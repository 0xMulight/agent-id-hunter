import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import notify

class NotifyTests(unittest.TestCase):
    def test_baseline_and_ecosystem_are_ignored(self):
        requests=[]
        def api(*args):requests.append(args);return []
        result=notify.notify([
          {"kind":"direct","change":"baseline","url":"https://binance.com/a"},
          {"kind":"ecosystem","change":"new","url":"https://binance.com/b"}],
          "owner/repo","token",request=api)
        self.assertEqual(result["created"],0)
        self.assertEqual(requests,[])
    def test_first_create_and_url_dedupe(self):
        calls=[]
        issue={"number":12,"body":"<!-- agent-id-hunter-url:abc -->"}
        def api(method,path,token,payload=None):
            calls.append((method,path,payload))
            if method=="GET" and "issues?state" in path: return []
            if method=="POST" and path.endswith("/issues"): return issue
            return []
        entry={"id":"abc","kind":"direct","change":"new","hash":"","title":"Agent ID","url":"https://binance.com/en/press","source":"Binance"}
        result=notify.notify([entry,entry],"owner/repo","token",request=api)
        self.assertEqual(result["created"],1)
        self.assertEqual(result["ignored"],1)
    def test_reject_nonofficial(self):
        item={"id":"bad","kind":"direct","change":"new","url":"https://evil.test/","title":"Fake"}
        self.assertEqual(notify.notify([item],"owner/repo","token")["created"],0)

if __name__=="__main__":unittest.main()
