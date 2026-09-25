import unittest
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from matcher import KeywordMatcher
from storage import AlertStorage

class TestAlertSystem(unittest.TestCase):

    def test_keyword_matcher_any(self):
        matcher = KeywordMatcher(keywords=["tax", "rbi", "mutual fund"], match_mode="any")
        
        # Positive match
        res1 = matcher.match(title="Launch of DSP BSE Insurance ETF NFO on NSE MF Invest Platform", content="Mutual Fund listing")
        self.assertTrue(res1["is_match"])
        self.assertIn("mutual fund", [k.lower() for k in res1["matched_keywords"]])

        # Negative match
        res2 = matcher.match(title="Listing of Equity Shares of Sonaselection India Limited", content="Category: Listing")
        self.assertFalse(res2["is_match"])
        self.assertEqual(len(res2["matched_keywords"]), 0)

    def test_keyword_matcher_all(self):
        matcher = KeywordMatcher(keywords=["listing", "equity"], match_mode="all")
        
        res = matcher.match(title="Listing of Equity Shares of Sonaselection India Limited", content="")
        self.assertTrue(res["is_match"])
        self.assertEqual(len(res["matched_keywords"]), 2)

    def test_storage_deduplication(self):
        storage = AlertStorage(db_path=":memory:")
        guid = "test_guid_123"
        self.assertFalse(storage.is_duplicate(guid))

        storage.save_alert(alert_id=guid, title="Test Alert", content="Sample content", matched_keywords=["tax"])
        self.assertTrue(storage.is_duplicate(guid))

if __name__ == "__main__":
    unittest.main()
