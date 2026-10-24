#!/usr/bin/env python3
"""Prepare a safe read-only on-chain mint plan. Never signs or submits."""
import argparse
from decimal import Decimal, InvalidOperation
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
HEX = re.compile(r"^0x(?:[a-fA-F0-9]{2})*$")
MAX_INT = 2**256 - 1

def valid_site(value):
    if not isinstance(value, str): return False
    try:
        p = urlsplit(value)
        host = p.hostname or ""
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            return False
        if not host or host.endswith(".local") or host == "localhost": return False
        if host.count(".") < 1: return False
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_global
        except ValueError: return True
    except ValueError: return False

def parse_uint(value, name, errors):
    if isinstance(value, bool) or value is None or not re.fullmatch(r"[0-9]+", str(value)):
        errors.append(f"{name} 必须填写非负整数（以 wei 为单位）")
        return None
    v = int(value)
    if v > MAX_INT:
        errors.append(f"{name} 超出 uint256 上限")
        return None
    return v

def fmt_bnb(wei):
    return f"{(Decimal(wei) / Decimal(10**18)):.8f} BNB"

def check(plan):
    blocks, missing, notes = [], [], []
    if plan.get("auto_execute") or plan.get("auto_sign") or plan.get("private_key"):
        blocks.append("禁止自动执行、自动签名或传入私钥")
    site = plan.get("project_url", "")
    if not valid_site(site):
        blocks.append("项目网址必须为可公开访问的 HTTPS 域名，不能是本机或内网")
    if plan.get("mint_status") == "closed":
        blocks.append("项目已结束 Mint，停止准备交易")
    elif plan.get("mint_status") != "open":
        missing.append("需要重新检查官方 Mint 是否开放及时间窗口")
    if plan.get("chain_id") != 56:
        missing.append("当前模板只为 BSC（chain_id=56）设计，其他链须使用对应官方钱包文档")
    if plan.get("method") not in ("contract_call", "swap_quote", "wallet_mint"):
        missing.append("确认执行方法：合约调用、DEX 兑换或网页钱包 Mint，三者不能混用")
    if plan.get("method") in ("swap_quote", "wallet_mint"):
        missing.append("当前不是标准合约调用，不得直接使用 contract-call preview；须阅读官方对应交易操作说明")
    if plan.get("payment_asset") != "BNB":
        missing.append("目前本预算模板仅计算原生 BNB 支出；ERC-20 付款需单独核对币种、授权和价格")
    if not plan.get("payment_value_verified"):
        missing.append("tx_value_wei 需要依据官方支付规则核实；免费 Mint 也不能把未知价格直接写成 0")
    address = plan.get("contract_address", "")
    if plan.get("method") == "contract_call" and not ADDRESS.fullmatch(str(address)):
        missing.append("提供已从项目官方文档与区块浏览器交叉核对的目标合约地址")
    if not plan.get("official_contract_verified"):
        missing.append("人工核验合约地址、网络与入口是否来自真实项目方")
    if not plan.get("official_rules_verified"):
        missing.append("核查官方数量限制、付款方式、Mint 条件、计数、截止和退款条款")
    if plan.get("ai_requirement") == "required" and not plan.get("ai_ownership_verified"):
        missing.append("活动官方要求持有 .ai，需按其规则核验持有权及参与钱包")
    if plan.get("ai_requirement") not in ("required", "optional", "none", "unknown"):
        missing.append("确认是否真的需要 .ai，而不是其他 Agent 身份标准")
    if plan.get("ai_requirement") == "unknown":
        missing.append("官方是否要求 .ai 尚未确认；不能凭项目宣传推断")
    quantity = plan.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        missing.append("确认 Mint 数量（正整数）")
    for k in ("tx_value_wei", "gas_cap_wei", "total_spend_cap_wei"):
        if k not in plan:
            missing.append(f"填写 {k}，以 wei 为单位（合约调用时不能直接填 BNB 数值）")
    value = parse_uint(plan.get("tx_value_wei"), "tx_value_wei", blocks) if "tx_value_wei" in plan else None
    gas = parse_uint(plan.get("gas_cap_wei"), "gas_cap_wei", blocks) if "gas_cap_wei" in plan else None
    budget = parse_uint(plan.get("total_spend_cap_wei"), "total_spend_cap_wei", blocks) if "total_spend_cap_wei" in plan else None
    if value is not None and gas is not None and budget is not None:
        if value + gas > budget:
            blocks.append(f"所需 {fmt_bnb(value+gas)} 超过预算上限 {fmt_bnb(budget)}")
        else:
            notes.append(f"用户填写的 BNB 支出 + Gas 预留 {fmt_bnb(value+gas)}；总预算 {fmt_bnb(budget)}")
            notes.append("gas_cap_wei 是手动预算预留，并非钱包实际 Gas 报价；必须通过 preview 估算再确认")
    if plan.get("method") == "contract_call":
        input_data = plan.get("input_data")
        if not HEX.fullmatch(str(input_data)):
            missing.append("必须由官方合约文档或可信 ABI 生成并核对 input_data；不可凭空生成")
        if input_data == "0x" and not plan.get("empty_calldata_authorized"):
            missing.append("空 calldata 转账不能自动视为 Mint，需要官方明确确认")
    if plan.get("approval_needed") is True:
        missing.append("先核对代币授权额度、spender、到期与撤销方式；USDT approve 和 mint 是两笔操作")
    if plan.get("allowlist_only") and not plan.get("allowlist_verified"):
        missing.append("确认地址是否在白名单或满足快照条件")
    notes += [
        "这份计划只检查用户填写的资料；布尔值“已核实”是自报，并非工具已独立验证",
        "即便检查通过，也只表示参数可用于 preview；不代表项目安全、资格已通过；必须查看实际报价、模拟和风险并经本人确认",
        "不要直接从网页复制所谓一键脚本或将助记词、私钥交给第三方 AI",
    ]
    status = "BLOCKED" if blocks else "NEEDS_REVIEW" if missing else "READY_FOR_PREVIEW"
    return {"status":status, "blocking":blocks, "missing":missing, "notes":notes,
            "safe":status=="READY_FOR_PREVIEW", "ready_for_execution":False}

def render(plan, result):
    title=plan.get("project_name") or "未命名项目"
    lines=[f"# Mint 预检｜{title}","",f"生成时间：{datetime.now(timezone.utc).isoformat(timespec='minutes')}",
           f"状态：**{result['status']}**","",f"入口：{plan.get('project_url','待确认')}",""]
    for label,key in [("必须停止","blocking"),("必须核实","missing"),("说明","notes")]:
        lines.append("## "+label)
        lines += ["- "+m for m in result[key]] or ["- 暂无"]
        lines.append("")
    if result["safe"]:
        lines += ["**下一步仅是打开官方钱包的 contract-call preview，不可直接 execute。**","",
                  "阅读 references/mint-playbook.md，读取官方钱包 SKILL.md 的实时语法，预览解析后的交易；",
                  "把真实钱包地址、合约、calldata、金额、gas 与风险逐项展示给用户并获明确确认。"]
    return "\n".join(lines)+"\n"

def main(argv=None):
    ap=argparse.ArgumentParser(description="只读 Mint 预检；不触发钱包签名")
    ap.add_argument("--plan",type=Path,required=True)
    ap.add_argument("--output",type=Path,default=ROOT/"data/mint-preflight.md")
    args=ap.parse_args(argv)
    try:
        plan=json.loads(args.plan.read_text(encoding="utf-8"))
        result=check(plan)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(render(plan,result),encoding="utf-8")
        print(json.dumps({"status":result["status"],"blocking":result["blocking"],
                          "missing":result["missing"],"report":str(args.output)},ensure_ascii=False,indent=2))
        return 2 if result["blocking"] else 0
    except (OSError,ValueError,TypeError,InvalidOperation) as exc:
        print(f"预检失败：{exc}",file=sys.stderr);return 1
if __name__=="__main__":
    sys.exit(main())
