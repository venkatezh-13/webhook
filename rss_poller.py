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
        Fetches the RSS feed XML, parses items, evaluates keywords, and dispatches alerts.
        """
        # Clean double slashes in path (e.g., https://nsearchives.nseindia.com//content -> /content)
        clean_url = self.rss_url.replace("://", "___TEMP___").replace("//", "/").replace("___TEMP___", "://")
        print(f"📡 Fetching RSS Feed from: {clean_url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/"
            }
            req = urllib.request.Request(clean_url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_bytes = resp.read()
                xml_text = raw_bytes.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            logger.error(f"[RSS Poller Error] Failed to fetch feed: {e}")
            print(f"❌ [RSS Error] Failed to fetch feed: {e}")
            return {"status": "error", "message": f"Fetch failed: {e}", "processed": 0, "matched": 0}


        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"[RSS Poller Error] XML parse error: {e}")
            print(f"❌ [RSS Error] XML Parse Error: {e}")
            return {"status": "error", "message": str(e), "processed": 0, "matched": 0}


        channel = root.find("channel")
        if channel is None:
            return {"status": "error", "message": "Invalid RSS feed: missing <channel>", "processed": 0, "matched": 0}

        items = channel.findall("item")
        processed_count = 0
        matched_count = 0
        sent_results = []

        print(f"🔍 Found {len(items)} items in RSS feed. Evaluating keyword rules...")

        for item in items:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            guid = item.findtext("guid", "").strip() or link or AlertStorage.generate_hash(title)
            description = item.findtext("description", "").strip()
            category = item.findtext("category", "").strip()
            pub_date = item.findtext("pubDate", "").strip()

            processed_count += 1

            # 1. Check for duplicates
            if self.storage.is_duplicate(guid):
                continue

            # 2. Evaluate keyword match
            combined_text = f"{title}\nCategory: {category}\n{description}"
            match_result = self.matcher.match(title=title, content=combined_text)

            if match_result["is_match"]:
                matched_count += 1
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

                # 3. Dispatch notifications
                successful_channels = self.router.dispatch(
                    alert=alert_payload,
                    matched_keywords=matched_kws,
                    snippet=snippet
                )

                # 4. Save to storage
                self.storage.save_alert(
                    alert_id=guid,
                    title=title,
                    content=description,
                    matched_keywords=matched_kws,
                    channels_sent=successful_channels
                )

                sent_results.append({
                    "title": title,
                    "matched_keywords": matched_kws,
                    "channels": successful_channels
                })
            else:
                # Store processed non-matching alert so we don't evaluate it again
                self.storage.save_alert(
                    alert_id=guid,
                    title=title,
                    content=description,
                    matched_keywords=[],
                    channels_sent=[]
                )

        print(f"✨ Ingestion complete. Evaluated {processed_count} circulars. Triggered {matched_count} alerts.")
        return {
            "status": "success",
            "total_items": len(items),
            "processed": processed_count,
            "matched": matched_count,
            "alerts_triggered": sent_results
        }
