import sys
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
import logging
from typing import List, Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from matcher import KeywordMatcher
from storage import AlertStorage
from notifiers import NotificationRouter


logger = logging.getLogger(__name__)

DEFAULT_RSS_URL = "https://venkatezh-13.github.io/circulars/docs/rss/all.xml"

class RSSCircularPoller:
    """
    Poller for India Exchange Circulars RSS Feed (NSE, BSE, MCX).
    """

    def __init__(
        self,
        matcher: KeywordMatcher,
        storage: AlertStorage,
        router: NotificationRouter,
        rss_url: str = DEFAULT_RSS_URL
    ):
        self.matcher = matcher
        self.storage = storage
        self.router = router
        self.rss_url = rss_url

    def fetch_and_process(self) -> Dict[str, Any]:
        """
        Fetches the RSS feed XML (supports single URL, list, or comma/newline-separated URLs),
        parses items, evaluates keywords, and dispatches alerts.
        """
        urls = []
        if isinstance(self.rss_url, list):
            urls = self.rss_url
        elif isinstance(self.rss_url, str):
            import re
            urls = [u.strip() for u in re.split(r'[\n,]+', self.rss_url) if u.strip()]

        if not urls:
            return {"status": "error", "message": "No RSS URLs provided", "processed": 0, "matched": 0}

        total_processed = 0
        total_matched = 0
        all_sent_results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/"
        }

        for current_url in urls:
            clean_url = current_url.replace("://", "___TEMP___").replace("//", "/").replace("___TEMP___", "://")
            print(f"📡 Fetching RSS Feed from: {clean_url}")
            
            try:
                req = urllib.request.Request(clean_url, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw_bytes = resp.read()
                    xml_text = raw_bytes.decode('utf-8', errors='ignore').strip()
            except Exception as e:
                logger.error(f"[RSS Poller Error] Failed to fetch feed {clean_url}: {e}")
                print(f"❌ [RSS Error] Failed to fetch feed {clean_url}: {e}")
                continue

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                logger.error(f"[RSS Poller Error] XML parse error for {clean_url}: {e}")
                print(f"❌ [RSS Error] XML Parse Error for {clean_url}: {e}")
                continue

            channel = root.find("channel")
            if channel is None:
                continue

            items = channel.findall("item")
            print(f"🔍 Found {len(items)} items in RSS feed ({clean_url}). Evaluating keyword rules...")

            for item in items:
                title = item.findtext("title", "").strip()
                link = item.findtext("link", "").strip()
                guid = item.findtext("guid", "").strip() or link or AlertStorage.generate_hash(title)
                description = item.findtext("description", "").strip()
                category = item.findtext("category", "").strip()
                pub_date = item.findtext("pubDate", "").strip()

                total_processed += 1

                if self.storage.is_duplicate(guid):
                    continue

                combined_text = f"{title}\nCategory: {category}\n{description}"
                match_result = self.matcher.match(title=title, content=combined_text)

                if match_result["is_match"]:
                    total_matched += 1
                    matched_kws = match_result["matched_keywords"]
                    snippet = match_result["snippet"]

                    print(f"🎯 MATCH FOUND! Alert: '{title[:60]}...' | Keywords: {matched_kws}")

                    alert_payload = {
                        "alert_id": guid,
                        "title": title,
                        "content": description,
                        "category": category,
                        "url": link,
                        "pubDate": pub_date
                    }

                    successful_channels = self.router.dispatch(
                        alert=alert_payload,
                        matched_keywords=matched_kws,
                        snippet=snippet
                    )

                    self.storage.save_alert(
                        alert_id=guid,
                        title=title,
                        content=description,
                        matched_keywords=matched_kws,
                        channels_sent=successful_channels
                    )

                    all_sent_results.append({
                        "title": title,
                        "matched_keywords": matched_kws,
                        "channels": successful_channels
                    })
                else:
                    self.storage.save_alert(
                        alert_id=guid,
                        title=title,
                        content=description,
                        matched_keywords=[],
                        channels_sent=[]
                    )

        print(f"✨ Ingestion complete across {len(urls)} feeds. Evaluated {total_processed} circulars. Triggered {total_matched} alerts.")
        return {
            "status": "success",
            "processed": total_processed,
            "matched": total_matched,
            "alerts_triggered": all_sent_results
        }
