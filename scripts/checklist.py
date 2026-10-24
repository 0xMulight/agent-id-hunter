#!/usr/bin/env python3
"""Generate a conservative participation checklist from a HUMAN-VERIFIED activity card."""
import argparse
from pathlib import Path
import json
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

def build(card, profile=None):
    profile = profile or {}
    relation = card.get("ai_requirement", "unknown")
    if relation not in ("required", "optional", "none", "unknown"):
        raise ValueError("ai_requirement 必须为 required / optional / none / unknown")
    lines = [f"# {card.get('title', '活动')}｜参与清单", "",
             f"官方原文：{card.get('official_url') or '未提供'}",
             f"生成于：{datetime.now(timezone.utc).isoformat(timespec='minutes')}", ""]
    if not card.get("source_verified") or not card.get("official_url"):
        lines += ["**警告：活动来源未人工核验，以下不能当做真实的官方资格规则。**", ""]
    description = {
        "required": "官方活动卡标记 .ai 为必要条件；请打开原文确认并核验链上所有权",
        "optional": "活动卡标记 .ai 为可选项；须核对官方原文",
        "none": "活动卡标记不要求 .ai；跳过 .ai 身份检查",
        "unknown": "活动是否需要 .ai 尚不明确，不能预设资格",
    }
    lines += [f"**.ai 身份要求**：{description[relation]}", ""]
    agent = str(profile.get("agent_id", "")).strip()
    if relation in ("required", "optional"):
        if agent.lower().endswith(".ai"):
            lines += [f"- [ ] 用户填写的名称：{agent}，**仍需按官方方法核验所有权与活动钱包**"]
        else:
            lines += ["- [ ] 如活动需要，填写你自己的 .ai 名称，并核验 NFT 持有人/绑定地址"]
    elif relation == "unknown":
        lines += ["- [ ] 官方活动规则是否真的要求 .ai？"]
    for field, label in [
        ("identity_proof", "身份验证方式"), ("registration", "报名方式"),
        ("wallet_and_chain", "指定钱包与链"), ("snapshot", "快照要求"),
        ("eligibility_region", "地区/KYC 限制"),
        ("deadline_with_timezone", "截止时间与时区"),
        ("reward_claim", "奖励领取"),
    ]:
        value = card.get(field) or "unknown"
        lines.append(f"- [ ] {label}：{value if value != 'unknown' else '待核对官方原文'}")
    lines += ["", "## 有效任务及凭证"]
    tasks = card.get("tasks", [])
    if not isinstance(tasks, list): raise ValueError("tasks 必须为数组")
    for t in tasks:
        lines += [f"- [ ] {t.get('title', '待补充任务')}｜凭证：{t.get('evidence') or '待核验'}｜官方计数：未确认"]
    lines += ["", "**这是准备清单，不代表已报名或资格通过；绝不自动签名/交易。**", ""]
    return "\n".join(lines)

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--activity", type=Path, required=True)
    p.add_argument("--profile", type=Path)
    p.add_argument("--output", type=Path, default=ROOT/"data/my-checklist.md")
    a = p.parse_args(argv)
    try:
        card = json.loads(a.activity.read_text(encoding="utf-8"))
        profile = json.loads(a.profile.read_text(encoding="utf-8")) if a.profile else {}
        content = build(card, profile)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(content, encoding="utf-8")
        print(content)
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print("错误：" + str(e), file=sys.stderr)
        return 1
if __name__ == "__main__":
    sys.exit(main())
