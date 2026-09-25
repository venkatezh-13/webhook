import logging
import urllib.request
import urllib.error
import json
import time
from typing import Dict, Any, List, Callable, Optional
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class WebhookNotifier(BaseNotifier):
    """
    Generic Webhook Notifier sending JSON payloads to any HTTP POST endpoint.
    """

    def __init__(self, webhook_url: str = "", delay_seconds: float = 1.0, on_dispatch: Optional[Callable[[Dict[str, Any]], None]] = None):
        super().__init__("Webhook")
        self.webhook_url = webhook_url
        self.delay_seconds = delay_seconds
        self.on_dispatch = on_dispatch

    def send_notification(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> bool:
        if not self.webhook_url or "YOUR_" in self.webhook_url or not self.webhook_url.startswith("http"):
            logger.warning("[Webhook] Skipping dispatch: WEBHOOK_URL is missing or unconfigured.")
            print(f"👉 [Webhook DRY RUN] Would send alert '{alert.get('title')}' with keywords: {matched_keywords}")
            return False

        title = alert.get("title", "Untitled Alert")
        url = alert.get("url", "")
        
        payload = {
            "event": "circular_alert",
            "title": title,
            "matched_keywords": matched_keywords,
            "snippet": snippet,
            "url": url,
            "category": alert.get("category", ""),
            "pub_date": alert.get("pubDate", "")
        }

        # Notify callback if registered
        if self.on_dispatch:
            try:
                self.on_dispatch({
                    **payload,
                    "destination": self.webhook_url
                })
            except Exception as e:
                logger.error(f"[Webhook Callback Error] {e}")

        # Apply rate limiting pause if configured
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "CircularAlertBot/1.0"
        }

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201, 202, 204):
                    logger.info("[Webhook] Notification dispatched successfully.")
                    print(f"✅ [Webhook] Payload sent for: '{title}'")
                    return True
                else:
                    logger.error(f"[Webhook] Status code: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"[Webhook Error] Failed to send payload: {e}")
            print(f"❌ [Webhook Error] {e}")
            return False
