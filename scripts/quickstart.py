#!/usr/bin/env python3
"""Create an intentionally incomplete Mint research plan from a single project URL.

This is NOT an on-chain scanner and NEVER submits a transaction.
"""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys
from mint_preflight import ROOT, valid_site, MAX_INT

def bnb_to_wei(raw):
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError):
        raise ValueError("预算必须是非负的 BNB 数值")
    if not amount.is_finite() or amount < 0:
        raise ValueError("预算必须是非负的有限 BNB 数值")
    wei = amount * Decimal(10**18)
    if wei != wei.to_integral_value() or wei > MAX_INT:
        raise ValueError("精度不得超过 18 位小数且预算必须在 uint256 范围内")
    return str(int(wei))

def plan_from_link(url, budget_bnb=None, title=None):
    if not valid_site(url):
        raise ValueError("只接受合法、公开的 HTTPS 项目网址")
    p = {
        "project_name": title or "待核验项目",
        "project_url": url,
        "chain_id": 56,
        "mint_status": "unknown",
        "method": "unknown",
        "official_rules_verified": False,
        "official_contract_verified": False,
        "contract_address": "",
        "input_data": "",
        "payment_asset": "unknown",
        "payment_value_verified": False,
        "ai_requirement": "unknown",
        "ai_ownership_verified": False,
        "allowlist_only": False,
        "approval_needed": False,
        "auto_execute": False
    }
    if budget_bnb is not None:
        p["total_spend_cap_wei"] = bnb_to_wei(budget_bnb)
    return p

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--budget-bnb", help="最大允许 BNB 预算（可选；只作为用户上限，不等于报价）")
    parser.add_argument("--name", help="项目简称（可选）")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "mint-my-plan.json")
    args = parser.parse_args(argv)
    try:
        p = plan_from_link(args.url, args.budget_bnb, args.name)
        if args.output.resolve().is_relative_to(ROOT) and not args.output.resolve().is_relative_to(ROOT / "data"):
            raise ValueError("本项目目录内仅允许把个人计划保存到 data/，以免意外公开提交")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("已生成待核验计划：" + str(args.output))
        print("尚未抓取或核验官网、合约、报价、Mint 时间及钱包资格；不得直接交易")
        print("下一步：交由 Agent 核查官方材料，再执行 scripts/mint_preflight.py")
        return 0
    except (ValueError, OSError) as err:
        print("无法创建计划：" + str(err), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
