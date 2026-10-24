import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import quickstart

class QuickstartTests(unittest.TestCase):
 def test_generates_safe_incomplete_plan(self):
  p=quickstart.plan_from_link("https://example.com/mint","0.0125")
  self.assertEqual(p["total_spend_cap_wei"],"12500000000000000")
  self.assertNotIn("tx_value_wei",p)
  self.assertNotIn("gas_cap_wei",p)
  self.assertEqual(p["mint_status"],"unknown")
  self.assertFalse(p["official_rules_verified"])
  self.assertFalse(p["auto_execute"])
 def test_without_budget_does_not_invent_price(self):
  p=quickstart.plan_from_link("https://example.com/mint")
  self.assertNotIn("total_spend_cap_wei",p)
 def test_blocks_internal_urls(self):
  for url in ("http://example.com/","https://localhost:443/","https://127.0.0.1/"):
   with self.subTest(url=url):
    with self.assertRaises(ValueError):quickstart.plan_from_link(url)
 def test_bad_budget_rejected(self):
  for budget in ("NaN","Infinity","-0.001","0.1234567890123456789","a lot"):
   with self.subTest(budget=budget):
    with self.assertRaises(ValueError):quickstart.bnb_to_wei(budget)
if __name__=="__main__":unittest.main()
