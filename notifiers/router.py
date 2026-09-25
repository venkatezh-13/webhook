import logging
from typing import Dict, Any, List
from .webhook import WebhookNotifier

logger = logging.getLogger(__name__)

class NotificationRouter:
    """
    Routes matched circular alerts to the configured Webhook endpoint.
    """

    def __init__(self, config: Dict[str, Any], env_vars: Dict[str, str] = None, on_dispatch=None):
        self.config = config
        self.env = env_vars or {}
        
        webhook_url = self.env.get("WEBHOOK_URL") or self.config.get("webhook_url", "")
        delay = float(self.config.get("rate_limit_delay_seconds", 1.0))
        
        self.notifier = WebhookNotifier(webhook_url=webhook_url, delay_seconds=delay, on_dispatch=on_dispatch)


    def dispatch(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> List[str]:
        """
        Dispatches alert payload to the Webhook URL.
        """
        try:
            success = self.notifier.send_notification(alert, matched_keywords, snippet)
            return [self.notifier.name] if success else []
        except Exception as e:
            logger.error(f"[Router Error] Failed to send via Webhook: {e}")
            return []
