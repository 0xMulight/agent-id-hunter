"""Offline checks: no Binance requests, keychain access, or real wallet sessions."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location("wallet_profiles", Path(__file__).resolve().parents[1] / "scripts/wallet_profiles.py")
wallets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wallets)


class ProfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.primary = self.root / "primary"
        self.primary.mkdir()
        self.session = self.primary / "session.json"
        self.original = b'{"offline_fixture":"primary-must-stay-byte-identical"}'
        self.session.write_bytes(self.original)
        self.env = mock.patch.dict(os.environ, {
            "BAW_MULTI_CONFIG": str(self.root / "private/profiles.json"),
            "BINANCE_BAW_DIR": str(self.primary),
            "BINANCE_INSTANCE_ID": "original-private-instance",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        wallets.main(["init"])

    def add_second(self):
        wallets.main(["add", "--wallet", "2", "--directory", str(self.root / "second")])
        return wallets.load()

    def test_primary_preserved_and_initialization_repeatable(self):
        data = self.add_second()
        wallets.main(["init"])
        wallets.main(["add", "--wallet", "2", "--directory", str(self.root / "other")])
        self.assertEqual(self.original, self.session.read_bytes())
        self.assertEqual(data, wallets.load())
        self.assertEqual("original-private-instance", data["profiles"]["1"]["instance_id"])
        if os.name != "nt":
            self.assertEqual(0o600, wallets.config_path().stat().st_mode & 0o777)
            self.assertEqual(0o700, (self.root / "second").stat().st_mode & 0o777)

    def test_profile_envs_do_not_leak_between_calls(self):
        data = self.add_second()
        second = wallets.environment(data["profiles"]["2"])
        primary = wallets.environment(data["profiles"]["1"])
        self.assertNotEqual(primary["BINANCE_INSTANCE_ID"], second["BINANCE_INSTANCE_ID"])
        self.assertNotEqual(primary["BINANCE_BAW_DIR"], second["BINANCE_BAW_DIR"])
        self.assertEqual("original-private-instance", os.environ["BINANCE_INSTANCE_ID"])
        data["profiles"]["1"]["instance_id"] = None
        self.assertNotIn("BINANCE_INSTANCE_ID", wallets.environment(data["profiles"]["1"]))

    def test_existing_directory_and_nested_directory_are_rejected(self):
        for target in (self.primary, self.primary / "child", self.root):
            with self.assertRaises(wallets.ProfileError):
                wallets.main(["add", "--wallet", "2", "--directory", str(target)])
        target = self.root / "occupied"
        target.mkdir()
        (target / "session.json").write_text("offline fixture")
        with self.assertRaises(wallets.ProfileError):
            wallets.main(["add", "--wallet", "2", "--directory", str(target)])
        self.assertEqual(self.original, self.session.read_bytes())

    def test_cli_cannot_forward_write_commands(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            wallets.main(["run", "--wallet", "1", "send"])
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            wallets.main(["run", "--wallet", "1", "status", "--", "wallet", "send"])

    def test_subprocess_scope_and_sensitive_output_filter(self):
        data = self.add_second()
        fake = subprocess.CompletedProcess([], 0, json.dumps({"success": True, "data": {"sessionId": "never-display", "clientId": "never-display", "status": "CONNECTED"}}), "")
        with mock.patch.object(wallets.subprocess, "run", return_value=fake) as run:
            result = wallets.call(data, "2", ["wallet", "status"], ["node", "fake-entry"])
        self.assertEqual({"status": "CONNECTED"}, result["data"])
        self.assertEqual(data["profiles"]["2"]["directory"], run.call_args.kwargs["env"]["BINANCE_BAW_DIR"])
        self.assertNotIn("instance_id", json.dumps(wallets.main(["list"])))
        self.assertEqual(self.original, self.session.read_bytes())

    def reports(self, first, second):
        def response(data, number, args, runner):
            payload = {"status": "CONNECTED"} if args[1] == "status" else {"addresses": [{"binanceChainId": "56", "address": first if str(number) == "1" else second}]}
            return {"success": True, "data": payload}
        return response

    def test_cross_profile_duplicates_and_missing_confirmation_are_detected(self):
        data = self.add_second()
        with mock.patch.object(wallets, "call", side_effect=self.reports("0xAbC", "0xabc")):
            result = wallets.check_all(data, ["fake"])
        self.assertFalse(result["verified"])
        self.assertTrue(any("share the same address" in issue for issue in result["issues"]))
        self.assertTrue(any("user confirmation" in issue for issue in result["issues"]))

    def test_confirmed_mapping_is_rechecked(self):
        data = self.add_second()
        for number, address in (("1", "0xabc"), ("2", "0xdef")):
            data["profiles"][number]["expected_addresses"] = {"56": address}
        with mock.patch.object(wallets, "call", side_effect=self.reports("0xABC", "0xdef")):
            self.assertTrue(wallets.check_all(data, ["fake"])["verified"])
        with mock.patch.object(wallets, "call", side_effect=self.reports("0xABC", "0xBAD")):
            result = wallets.check_all(data, ["fake"])
        self.assertFalse(result["verified"])
        self.assertTrue(any("does not match" in issue for issue in result["issues"]))

    def test_connected_wallet_is_not_signed_in_again(self):
        with mock.patch.object(wallets, "runtime", return_value=["fake"]), mock.patch.object(wallets, "call", return_value={"success": True, "data": {"status": "CONNECTED"}}) as call:
            output = wallets.main(["run", "--wallet", "1", "signin"])
        self.assertEqual("ALREADY_CONNECTED", output["data"]["status"])
        self.assertEqual(1, call.call_count)

    def test_active_lock_is_respected(self):
        with wallets.lock("runtime.lock"):
            with self.assertRaises(wallets.ProfileError):
                with wallets.lock("runtime.lock"):
                    self.fail("must not enter")

    def test_runtime_rejects_shared_or_uncertain_keychain(self):
        entry = self.root / "package/dist/index.js"
        entry.parent.mkdir(parents=True)
        entry.write_text("offline CLI storage fixture")
        (entry.parent.parent / "package.json").write_text(json.dumps({"name": "@binance/agentic-wallet", "version": wallets.REVIEWED_VERSION}))
        fingerprint = wallets.hashlib.sha256(entry.read_bytes()).hexdigest()
        with mock.patch.dict(os.environ, {"BAW_MULTI_CLI_ENTRY": str(entry)}), mock.patch.object(wallets.shutil, "which", return_value="node"), mock.patch.object(wallets, "REVIEWED_SHA256", fingerprint):
            for storage in ("keychain", "unknown", ""):
                with mock.patch.object(wallets.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, storage, "")):
                    with self.assertRaises(wallets.ProfileError):
                        wallets.runtime()
            with mock.patch.object(wallets.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "file", "")):
                self.assertEqual(["node", str(entry)], wallets.runtime())
        self.assertEqual(self.original, self.session.read_bytes())


if __name__ == "__main__":
    unittest.main()
