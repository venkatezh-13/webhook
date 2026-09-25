import os
import sys
import argparse
import yaml
import logging
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from matcher import KeywordMatcher
from storage import AlertStorage
from notifiers import NotificationRouter
from rss_poller import RSSCircularPoller

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return {
            "keywords": ["tax", "rbi", "urgent", "compliance", "circular", "MOCK"],
            "match_mode": "any",
            "webhook_url": "",
            "rate_limit_delay_seconds": 1.0,
            "deduplication": {"enabled": True, "storage_db": "alerts_history.db"}
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_env() -> Dict[str, str]:
    env_vars = dict(os.environ)
    env_file = ".env"
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars

def run_test_alert(router: NotificationRouter):
    """Triggers a simulated test alert payload to the configured Webhook URL."""
    print("\n🧪 --- RUNNING TEST WEBHOOK ALERT ---")
    test_alert = {
        "alert_id": "test_001",
        "title": "URGENT: Test Circular on Tax Policy & Compliance Update",
        "content": "This is a test notification payload verifying integration with your Webhook URL.",
        "url": "https://venkatezh-13.github.io/circulars"
    }
    test_keywords = ["urgent", "tax", "policy", "compliance"]
    snippet = "This is a test notification payload verifying integration with **[URGENT]** **[TAX]** **[POLICY]** updates."

    results = router.dispatch(test_alert, test_keywords, snippet)
    print(f"🎉 Test Alert Dispatch complete! Reached endpoint via: {results}\n")

def main():
    parser = argparse.ArgumentParser(description="Keyword Alert Webhook System for Exchange Circulars")
    parser.add_argument("--poll", action="store_true", help="Fetch RSS feed and process circular alerts")
    parser.add_argument("--interval", type=int, default=0, help="Continuous polling interval in seconds (e.g. 300 for 5 mins)")
    parser.add_argument("--test", action="store_true", help="Send a test alert payload to the Webhook URL")
    parser.add_argument("--history", action="store_true", help="Show database history of matched alerts")
    parser.add_argument("--keywords", nargs="+", help="Override keywords to search for")
    parser.add_argument("--webhook-url", type=str, help="Webhook Destination URL")
    parser.add_argument("--rss-url", type=str, help="Custom RSS feed URL")

    args = parser.parse_args()
    config = load_config()
    env_vars = load_env()

    if args.keywords:
        config["keywords"] = args.keywords

    if args.webhook_url:
        env_vars["WEBHOOK_URL"] = args.webhook_url

    matcher = KeywordMatcher(
        keywords=config.get("keywords", []),
        match_mode=config.get("match_mode", "any")
    )
    
    db_path = config.get("deduplication", {}).get("storage_db", "alerts_history.db")
    storage = AlertStorage(db_path=db_path)
    router = NotificationRouter(config=config, env_vars=env_vars)

    rss_url = args.rss_url or config.get("rss_url", "")
    if not rss_url and (args.poll or len(sys.argv) == 1):
        print("❌ Error: Please specify an RSS Feed URL via --rss-url <URL> or in config.yaml")
        sys.exit(1)

    poller = RSSCircularPoller(matcher=matcher, storage=storage, router=router, rss_url=rss_url)


    if args.test:
        run_test_alert(router)
    elif args.history:
        print("\n📜 --- RECENT MATCHED ALERTS HISTORY ---")
        alerts = storage.get_recent_alerts(limit=10)
        if not alerts:
            print("No alerts recorded in database yet.")
        for a in alerts:
            print(f"• [{a['processed_at']}] {a['title'][:60]}... | Keywords: {a['matched_keywords']} | Webhook Sent: {a['channels_sent']}")
        print()
    elif args.poll or len(sys.argv) == 1:
        print(f"⚙️ Configured Keywords: {config.get('keywords')}")
        print(f"⚙️ Match Mode: {config.get('match_mode')}")
        print(f"🌐 Webhook Destination: {env_vars.get('WEBHOOK_URL') or config.get('webhook_url')}")
        
        import time
        if args.interval > 0:
            print(f"🔄 Continuous Polling Active! Checking every {args.interval} seconds...\n")
            try:
                while True:
                    poller.fetch_and_process()
                    time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nStopping continuous polling.")
        else:
            poller.fetch_and_process()


if __name__ == "__main__":
    main()
