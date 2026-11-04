#!/usr/bin/env python3
"""Profile-scoped authentication and read-only access to the official baw CLI."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

REVIEWED_VERSION = "1.12.0"
REVIEWED_SHA256 = "e63e2dff4a6d267d2375a0bbcdf518f10ddd04b0ffaff378c265a26f0961fe4f"
READS = {"status", "address", "balance", "agent-id", "settings", "chains", "tx-history"}
KEYTAR_PROBE = """
const {createRequire} = require('node:module');
const {pathToFileURL} = require('node:url');
(async () => {
  const req = createRequire(process.argv[1]);
  let mod;
  try { mod = await import(pathToFileURL(req.resolve('@github/keytar')).href); }
  catch { process.stdout.write('file'); return; }
  const kt = mod.default || mod;
  try {
    await kt.getPassword('mulight-baw-isolation-probe-no-credentials', 'nonexistent');
    process.stdout.write('keychain');
  } catch { process.stdout.write('unknown'); }
})().catch(() => { process.stdout.write('unknown'); });
"""


class ProfileError(Exception):
    pass


def config_path():
    return Path(os.environ.get("BAW_MULTI_CONFIG", Path.home() / ".config/baw-multi/profiles.json")).expanduser().resolve()


@contextmanager
def lock(name="profiles.lock"):
    directory = config_path().parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = directory / name
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ProfileError("Another operation holds the local lock; wait for it. Do not remove an active lock.") from exc
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def load():
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError("Run init first in the environment where wallet 1 was originally connected.") from exc
    if data.get("version") != 1 or not isinstance(data.get("profiles"), dict):
        raise ProfileError("Unsupported profile configuration; do not recreate it or rotate instance IDs.")
    return data


def save(data):
    path = config_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".profiles-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp, path)
        if os.name != "nt":
            path.chmod(0o600)
    finally:
        Path(tmp).unlink(missing_ok=True)


def select(data, number):
    try:
        return data["profiles"][str(number)]
    except KeyError as exc:
        raise ProfileError(f"Wallet {number} is not registered.") from exc


def environment(profile):
    env = os.environ.copy()
    env["BINANCE_BAW_DIR"] = profile["directory"]
    env.pop("BINANCE_INSTANCE_ID", None)
    if profile["instance_id"] is not None:
        env["BINANCE_INSTANCE_ID"] = profile["instance_id"]
    return env


def runtime():
    """Inspect local code without importing baw or opening any wallet session."""
    node = shutil.which("node")
    command = shutil.which("baw")
    explicit = os.environ.get("BAW_MULTI_CLI_ENTRY")
    if not node or not (command or explicit):
        raise ProfileError("Missing Node.js or baw. Install the official @binance/agentic-wallet CLI in this runtime.")
    entry = Path(explicit or command).expanduser().resolve()
    candidates = [entry]
    candidates += [entry.parent / "node_modules/@binance/agentic-wallet/dist/index.js"]
    actual = None
    for candidate in candidates:
        package_file = candidate.parent.parent / "package.json"
        if package_file.is_file():
            package = json.loads(package_file.read_text(encoding="utf-8"))
            if package.get("name") == "@binance/agentic-wallet":
                actual = candidate
                break
    if actual is None:
        raise ProfileError("Cannot resolve the official baw entry. Set BAW_MULTI_CLI_ENTRY to its installed dist/index.js; do not use a custom session wrapper.")
    if package.get("version") != REVIEWED_VERSION or hashlib.sha256(actual.read_bytes()).hexdigest() != REVIEWED_SHA256:
        raise ProfileError("This baw build has not been reviewed for session isolation. Inspect its current storage code before updating the guard; do not downgrade a working installation automatically.")
    try:
        probe = subprocess.run([node, "-e", KEYTAR_PROBE, str(actual)], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProfileError("Cannot determine the system keychain backend; do not start a second login.") from exc
    if probe.returncode != 0 or probe.stdout != "file":
        raise ProfileError("System keychain is available or isolation is uncertain. baw 1.12.0 uses one shared keychain entry. Stop before a second login; use separate OS users or independently isolated runtimes instead.")
    return [node, str(actual)]


def scrub(value, data):
    if isinstance(value, dict):
        return {k: scrub(v, data) for k, v in value.items() if not re.search(r"^(clientId|sessionId|sessionToken|accessToken|refreshToken|token|cookie|authorization|privateKey|seedPhrase|mnemonic|instanceId|instance_id)$", k, re.I)}
    if isinstance(value, list):
        return [scrub(v, data) for v in value]
    if isinstance(value, str):
        for profile in data.get("profiles", {}).values():
            if profile.get("instance_id"):
                value = value.replace(profile["instance_id"], "[redacted]")
    return value


def call(data, number, args, runner):
    profile = select(data, number)
    try:
        result = subprocess.run(runner + args + ["--json"], env=environment(profile), capture_output=True, text=True, encoding="utf-8", timeout=330 if args[:2] == ["auth", "verify"] else 45, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProfileError("baw did not complete. Check this wallet's status before retrying authentication.") from exc
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProfileError("baw returned non-JSON output; raw output was withheld to protect credentials.") from exc
    payload = scrub(payload, data)
    if result.returncode != 0 or payload.get("success") is not True:
        raise ProfileError(json.dumps(payload.get("error", {"message": "baw failed"}), ensure_ascii=False))
    return payload


def address_map(payload):
    rows = payload.get("data", {}).get("addresses", [])
    return {str(row["binanceChainId"]): row["address"] for row in rows if row.get("address")}


def normalized(address):
    return address.lower() if address.startswith("0x") else address


def check_all(data, runner):
    reports, seen, issues = [], {}, []
    for number, profile in data["profiles"].items():
        status = call(data, number, ["wallet", "status"], runner).get("data", {}).get("status")
        report = {"wallet": number, "status": status, "addresses": {}}
        if status == "CONNECTED":
            report["addresses"] = address_map(call(data, number, ["wallet", "address"], runner))
            if not report["addresses"]:
                issues.append(f"Wallet {number} returned no addresses")
            if not profile.get("expected_addresses"):
                issues.append(f"Wallet {number} address mapping needs user confirmation and pin")
            for chain, address in report["addresses"].items():
                key = (chain, normalized(address))
                if key in seen:
                    issues.append(f"Wallets {seen[key]} and {number} share the same address on chain {chain}")
                seen[key] = number
            for chain, expected in profile.get("expected_addresses", {}).items():
                if normalized(report["addresses"].get(chain, "")) != normalized(expected):
                    issues.append(f"Wallet {number} does not match its confirmed address on chain {chain}")
        else:
            issues.append(f"Wallet {number} is not connected")
        reports.append(report)
    return {"wallets": reports, "issues": issues, "verified": not issues}


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="action", required=True)
    sub.add_parser("init", help="Register wallet 1's existing directory/environment without touching its session")
    sub.add_parser("list")
    sub.add_parser("doctor")
    sub.add_parser("check")
    add = sub.add_parser("add")
    add.add_argument("--wallet", required=True, type=int)
    add.add_argument("--directory")
    run = sub.add_parser("run")
    run.add_argument("--wallet", required=True, type=int)
    run.add_argument("operation", choices=sorted(READS | {"signin", "verify"}))
    run.add_argument("--qr-code-id")
    pin = sub.add_parser("pin")
    pin.add_argument("--wallet", required=True, type=int)
    pin.add_argument("--chain", required=True)
    pin.add_argument("--address", required=True)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    if args.action == "doctor":
        runtime()
        return {"ready": True, "reviewed_cli": REVIEWED_VERSION, "backend": "file", "live_login_tested": False}
    if args.action in {"init", "add", "pin"}:
        with lock():
            if args.action == "init":
                if config_path().exists():
                    load()
                    return {"existing_configuration_preserved": True}
                primary = Path(os.environ.get("BINANCE_BAW_DIR") or Path.home() / ".baw").expanduser().resolve()
                save({"version": 1, "profiles": {"1": {"directory": str(primary), "instance_id": os.environ.get("BINANCE_INSTANCE_ID"), "expected_addresses": {}}}})
                return {"wallet": "1", "directory": str(primary), "session_untouched": True}
            data = load()
            if args.action == "add":
                if args.wallet < 2:
                    raise ProfileError("Use init to preserve wallet 1; additional wallets start at 2.")
                if str(args.wallet) in data["profiles"]:
                    return {"wallet": str(args.wallet), "existing_configuration_preserved": True}
                directory = Path(args.directory or Path.home() / f".baw-wallet{args.wallet}").expanduser().resolve()
                for profile in data["profiles"].values():
                    other = Path(profile["directory"]).resolve()
                    if directory == other or directory in other.parents or other in directory.parents:
                        raise ProfileError("Wallet directories must be distinct and must not contain one another.")
                if directory.exists() and (not directory.is_dir() or any(directory.iterdir())):
                    raise ProfileError("Target directory already has content; do not overwrite or copy an existing session.")
                directory.mkdir(mode=0o700, parents=True, exist_ok=True)
                if os.name != "nt":
                    directory.chmod(0o700)
                data["profiles"][str(args.wallet)] = {"directory": str(directory), "instance_id": f"wallet-{args.wallet}-" + secrets.token_urlsafe(32), "expected_addresses": {}}
                save(data)
                return {"wallet": str(args.wallet), "directory": str(directory), "login_required": True}
            with lock("runtime.lock"):
                actual = address_map(call(data, args.wallet, ["wallet", "address"], runtime()))
            if normalized(actual.get(args.chain, "")) != normalized(args.address):
                raise ProfileError("The supplied address does not match this wallet; no binding was saved.")
            select(data, args.wallet)["expected_addresses"][args.chain] = args.address
            save(data)
            return {"wallet": str(args.wallet), "chain": args.chain, "confirmed_address": args.address}
    data = load()
    if args.action == "list":
        return {"profiles": [{"wallet": n, "directory": p["directory"], "confirmed_addresses": p.get("expected_addresses", {})} for n, p in data["profiles"].items()]}
    with lock("runtime.lock"):
        runner = runtime()
        if args.action == "check":
            return check_all(data, runner)
        if args.operation == "signin":
            status = call(data, args.wallet, ["wallet", "status"], runner)
            if status.get("data", {}).get("status") == "CONNECTED":
                return {"success": True, "data": {"status": "ALREADY_CONNECTED"}}
            return call(data, args.wallet, ["auth", "signin"], runner)
        if args.operation == "verify":
            if not args.qr_code_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", args.qr_code_id):
                raise ProfileError("Pass the exact qrCodeId returned by this wallet's signin.")
            return call(data, args.wallet, ["auth", "verify", "--qrCodeId", args.qr_code_id], runner)
        return call(data, args.wallet, ["wallet", args.operation], runner)


if __name__ == "__main__":
    try:
        output = main()
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if output.get("verified") is False:
            sys.exit(2)
    except (ProfileError, OSError, ValueError) as exc:
        print(json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
