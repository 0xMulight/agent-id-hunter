import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import checklist

CARD={"title":"样例活动","official_url":"","source_verified":False,
      "ai_requirement":"unknown","tasks":[{"title":"报名","evidence":"截图"}]}

class ChecklistTests(unittest.TestCase):
    def test_unknown_does_not_require_agent_id(self):
        text=checklist.build(CARD)
        self.assertIn("尚不明确",text)
        self.assertNotIn("Flux",text)
    def test_no_ai_requirement_does_not_ask_for_ai(self):
        text=checklist.build({**CARD,"ai_requirement":"none"})
        self.assertIn("跳过 .ai 身份检查",text)
        self.assertNotIn("填写你自己的 .ai 名称",text)
    def test_required_with_self_report_does_not_claim_verified(self):
        text=checklist.build({**CARD,"ai_requirement":"required"},{"agent_id":"example.ai"})
        self.assertIn("example.ai",text)
        self.assertIn("仍需按官方方法核验所有权",text)
        self.assertNotIn("资格通过",text.split("## 有效任务及凭证")[0])
    def test_invalid_ai_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            checklist.build({**CARD,"ai_requirement":"YES"})

if __name__=="__main__":unittest.main()
