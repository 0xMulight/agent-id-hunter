import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import mint_preflight as m

BASE = {
 "project_name":"Demo","project_url":"https://example.com/mint",
 "chain_id":56,"mint_status":"open","method":"contract_call",
 "official_rules_verified":True,"official_contract_verified":True,
 "contract_address":"0x"+"a"*40,"input_data":"0x1234","quantity":1,
 "ai_requirement":"none","approval_needed":False,
 "payment_asset":"BNB","payment_value_verified":True,
 "tx_value_wei":"1000000000000000","gas_cap_wei":"100000000000000",
 "total_spend_cap_wei":"2000000000000000"
}

class MintTests(unittest.TestCase):
 def test_ready_never_auto_executes(self):
  res=m.check(BASE)
  self.assertEqual(res["status"],"READY_FOR_PREVIEW")
  self.assertFalse(res["ready_for_execution"])
 def test_budget_blocks(self):
  res=m.check({**BASE,"total_spend_cap_wei":"500000000000000"})
  self.assertEqual(res["status"],"BLOCKED")
  self.assertIn("预算上限",res["blocking"][0])
 def test_closed_mint_blocks(self):
  self.assertEqual(m.check({**BASE,"mint_status":"closed"})["status"],"BLOCKED")
 def test_auto_execute_blocks(self):
  self.assertEqual(m.check({**BASE,"auto_execute":True})["status"],"BLOCKED")
 def test_bad_contract_needs_review(self):
  self.assertEqual(m.check({**BASE,"contract_address":"0x123"})["status"],"NEEDS_REVIEW")
 def test_requirement_aliased_identity_needs_proof(self):
  res=m.check({**BASE,"ai_requirement":"required","ai_ownership_verified":False})
  self.assertEqual(res["status"],"NEEDS_REVIEW")
  self.assertIn("核验",res["missing"][0])
 def test_local_url_blocked(self):
  for url in ("http://example.com/","https://127.0.0.1/","https://localhost/mint","https://binance.com.evil.local/"):
   with self.subTest(url=url):
    self.assertEqual(m.check({**BASE,"project_url":url})["status"],"BLOCKED")
 def test_empty_calldata_needs_explicit_approval(self):
  res=m.check({**BASE,"input_data":"0x"})
  self.assertEqual(res["status"],"NEEDS_REVIEW")
 def test_malformed_input_data_requires_review(self):
  self.assertEqual(m.check({**BASE,"input_data":"0x123"})["status"],"NEEDS_REVIEW")
 def test_hard_block_exceeds_wei_range(self):
  self.assertEqual(m.check({**BASE,"tx_value_wei":str(2**256)})["status"],"BLOCKED")
 def test_missing_spend_cap_cannot_be_ready(self):
  p=dict(BASE);p.pop("total_spend_cap_wei")
  self.assertEqual(m.check(p)["status"],"NEEDS_REVIEW")

 def test_unknown_payment_cannot_be_ready(self):
  res=m.check({**BASE,"payment_value_verified":False})
  self.assertEqual(res["status"],"NEEDS_REVIEW")
 def test_erc20_payment_is_not_generic_bnb_contract_call(self):
  res=m.check({**BASE,"payment_asset":"USDT"})
  self.assertEqual(res["status"],"NEEDS_REVIEW")
 def test_swap_does_not_count_as_mint_preview(self):
  res=m.check({**BASE,"method":"swap_quote"})
  self.assertEqual(res["status"],"NEEDS_REVIEW")

if __name__=="__main__":unittest.main()
