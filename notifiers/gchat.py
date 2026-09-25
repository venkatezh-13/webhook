import logging
import urllib.request
import urllib.error
import json
from typing import Dict, Any, List
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class GChatNotifier(BaseNotifier):
    """
    Google Chat Webhook Notifier supporting formatted Cards V2 messages.
    """

    def __init__(self, webhook_url: str):
        super().__init__("Google Chat")
        self.webhook_url = webhook_url

    def send_notification(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> bool:
        if not self.webhook_url or "YOUR_KEY" in self.webhook_url or not self.webhook_url.startswith("http"):
            logger.warning("[Google Chat] Skipping dispatch: GCHAT_WEBHOOK_URL is missing or unconfigured.")
            print(f"👉 [Google Chat DRY RUN] Would notify for alert: '{alert.get('title')}' with keywords: {matched_keywords}")
            return False

        title = alert.get("title", "Untitled Alert")
        url = alert.get("url", "")
        keywords_str = ", ".join(matched_keywords)

        # Build Google Chat Card V2 Payload
        payload = {
            "cardsV2": [
                {
                    "cardId": "circularAlertCard",
                    "card": {
                        "header": {
                            "title": "🚨 Circular Alert Triggered",
                            "subtitle": f"Keywords: {keywords_str}",
                            "imageUrl": "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/notifications_active/default/48px.svg",
                            "imageType": "CIRCLE"
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": f"<b>Title:</b> {title}"
                                        }
                                    },
                                    {
                                        "textParagraph": {
                                            "text": f"<b>Snippet:</b> {snippet}"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        # Add Action Button if URL exists
        if url:
            payload["cardsV2"][0]["card"]["sections"][0]["widgets"].append({
                "buttonList": {
                    "buttons": [
                        {
                            "text": "Open Circular",
                            "onClick": {
                                "openLink": {
                                    "url": url
                                }
                            }
                        }
                    ]
                }
            })

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=UTF-8"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 204):
                    logger.info("[Google Chat] Successfully dispatched notification.")
                    print(f"✅ [Google Chat] Notification sent for: '{title}'")
                    return True
                else:
                    logger.error(f"[Google Chat] Failed with status code: {response.status}")
                    return False
        except urllib.error.URLError as e:
            logger.error(f"[Google Chat] HTTP Error during dispatch: {e}")
            print(f"❌ [Google Chat Error] {e}")
            return False
        except Exception as e:
            logger.error(f"[Google Chat] Unexpected error: {e}")
            return False
