import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import wallet_probe as p

class WalletProbeTests(unittest.TestCase):
 def test_missing_baw_explains_install(self):
  res=p.probe("status", found=lambda which: None)
  self.assertFalse(res["ok"])
  self.assertIn("npx skills add",res["install"])
 def test_only_allowlisted_read_commands(self):
  called=[]
  def runner(argv,**kw):
   called.append(argv)
   return type("Proc",(),{"returncode":0,"stdout":"{}","stderr":""})()
  res=p.probe("execute",runner=runner,found=lambda which:"/usr/bin/baw")
  self.assertFalse(res["ok"])
  self.assertEqual(called,[])
 def test_status_calls_baw_read_only(self):
  called=[]
  def runner(argv,**kw):
   called.append(argv)
   return type("Proc",(),{"returncode":0,"stdout":'{"success":true}',"stderr":""})()
  res=p.probe("status",runner=runner,found=lambda which:"/usr/bin/baw")
  self.assertEqual(called,[["baw","wallet","status","--json"]])
  self.assertTrue(res["ok"])
 def test_cli_error_is_not_silenced(self):
  def runner(argv,**kw):
   return type("Proc",(),{"returncode":1,"stdout":"","stderr":"not connected"})()
  res=p.probe("status",runner=runner,found=lambda which:"/usr/bin/baw")
  self.assertFalse(res["ok"])
  self.assertIn("not connected",res["error"])
 def test_wallet_output_redacts_secrets_recursively(self):
  result=p.redact({"success":True,"data":{"accessToken":"abc","refresh_token":"xyz","clientId":"private","walletAddress":"0x123","nested":[{"apiKey":"secret","dailyLimit":100}]}})
  self.assertEqual(result["data"]["accessToken"],"[REDACTED]")
  self.assertEqual(result["data"]["refresh_token"],"[REDACTED]")
  self.assertEqual(result["data"]["clientId"],"[REDACTED]")
  self.assertEqual(result["data"]["nested"][0]["apiKey"],"[REDACTED]")
  self.assertEqual(result["data"]["walletAddress"],"0x123")
  self.assertEqual(result["data"]["nested"][0]["dailyLimit"],100)

if __name__=="__main__":unittest.main()
