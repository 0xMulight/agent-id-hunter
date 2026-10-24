#!/usr/bin/env python3
"""Read-only diagnostics of installed Binance Agentic Wallet CLI."""
import argparse
import json
import re
import shutil
import subprocess
import sys

SAFE_COMMANDS = {
    "status": ["baw", "wallet", "status", "--json"],
    "settings": ["baw", "wallet", "settings", "--json"],
    "address": ["baw", "wallet", "address", "--json"],
    "gas": ["baw", "wallet", "gas-price", "--json"],
}
SENSITIVE_KEYS = re.compile(r"^(?:(?:access|refresh|id|session|auth)?token|privatekey|seedphrase|mnemonic|password|secret|clientid|apikey|apisecret|jwt|authorization|cookie|bearer)$", re.I)

def redact(data):
    """Hide credential-like fields before the CLI output reaches an AI conversation."""
    if isinstance(data, dict):
        return {k: "[REDACTED]" if SENSITIVE_KEYS.fullmatch(re.sub(r"[^a-zA-Z0-9]", "", str(k))) else redact(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact(v) for v in data]
    return data

INSTALL = "npx skills add binance/binance-skills-hub/skills/binance-web3/binance-agentic-wallet"

def probe(which, runner=subprocess.run, found=shutil.which):
    if not found("baw"):
        return {"ok": False, "error": "未安装 baw CLI，先安装币安官方 Agentic Wallet Skill", "install": INSTALL}
    if which not in SAFE_COMMANDS:
        return {"ok": False, "error": "命令不在只读白名单"}
    cmd=SAFE_COMMANDS[which]
    try:
        proc=runner(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "baw 返回错误")[:600]}
    try:
        data=json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": "钱包 CLI 没有返回有效 JSON"}
    return {"ok": True, "command": which, "result": redact(data)}

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("command", choices=list(SAFE_COMMANDS))
    args=parser.parse_args(argv)
    result=probe(args.command)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["ok"] else 2

if __name__=="__main__":
    sys.exit(main())
