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
if __name__=="__main__":unittest.main()
