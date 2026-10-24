import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scout

class ScoutTests(unittest.TestCase):
    def test_official_host_allowlist(self):
        self.assertTrue(scout.official("https://www.binance.com/en/press"))
        self.assertFalse(scout.official("http://www.binance.com/en/press"))
        self.assertFalse(scout.official("https://binance.com.evil.test/"))
        self.assertFalse(scout.official("https://127.0.0.1/private"))
    def test_categories_are_distinct(self):
        self.assertEqual(scout.classify("New Agent ID .ai campaign"),"direct")
        self.assertEqual(scout.classify("AI Agent roadmap"),"ecosystem")
        self.assertIsNone(scout.classify("A token listing"))
    def test_index_ignores_square_and_external(self):
        sources=[{"url":"https://www.binance.com/en/press","kind":"index","name":"Binance"}]
        raw="<html><a href='/en/news/agent-id'>Agent ID campaign</a><a href='/en/square/post/agent-id'>Agent ID rumor</a><a href='https://evil.tld/'>Agent ID</a></html>"
        results,diagnostics=scout.collect(sources,lambda url:raw)
        self.assertEqual(len(results),1)
        self.assertEqual(results[0]["kind"],"direct")
        self.assertTrue(diagnostics[0]["ok"])
    def test_failed_source_is_not_success(self):
        sources=[{"url":"https://www.binance.com/en/press"}]
        def failure(url): raise RuntimeError("blocked")
        items,diagnostics=scout.collect(sources,failure)
        self.assertEqual(items,[])
        self.assertFalse(diagnostics[0]["ok"])
    def test_first_baseline_new_and_changed(self):
        link="https://www.binance.com/en/news/agent-id"
        item=scout.make_item(link,"Agent ID registration","Binance")
        state,items=scout.compare([item],{})
        self.assertEqual(items[0]["change"],"baseline")
        item2=scout.make_item(link,"Agent ID registration","Binance")
        state2,items2=scout.compare([item2],state)
        self.assertEqual(items2[0]["change"],"same")
        item3=scout.make_item(link,"Agent ID rewards","Binance")
        _,items3=scout.compare([item3],state2)
        self.assertEqual(items3[0]["change"],"changed")
    def test_page_mode_does_not_assume_ai_holder_requirement(self):
        sources=[{"url":"https://four.meme/en/agentic","kind":"page"}]
        items,_=scout.collect(sources,lambda url:"<title>AI Agent Tools</title><p>ERC 8004 launch tools</p>")
        self.assertEqual(items[0]["kind"],"ecosystem")
        self.assertIn("线索",items[0]["warning"])

if __name__=="__main__":unittest.main()
