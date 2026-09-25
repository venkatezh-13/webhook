import logging
import urllib.request
import urllib.parse
import urllib.error
import json
import base64
from typing import Dict, Any, List
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class WhatsAppNotifier(BaseNotifier):
    """
    WhatsApp Notifier supporting Twilio, Meta WhatsApp Cloud API, and Whatomate / Whautomate platform integrations.
    """

    def __init__(
        self,
        provider: str = "whatomate",
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "whatsapp:+14155238886",
        to_number: str = "",
        meta_token: str = "",
        meta_phone_id: str = "",
        whatomate_url: str = "",
        whatomate_api_key: str = "",
        whatomate_contact_id: str = "",
        delay_seconds: float = 1.0
    ):
        super().__init__("WhatsApp")
        self.provider = provider.lower()
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number
        self.meta_token = meta_token
        self.meta_phone_id = meta_phone_id
        self.whatomate_url = whatomate_url
        self.whatomate_api_key = whatomate_api_key
        self.whatomate_contact_id = whatomate_contact_id
        self.delay_seconds = delay_seconds


    def send_notification(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> bool:
        title = alert.get("title", "Untitled Alert")
        url = alert.get("url", "")
        keywords_str = ", ".join(matched_keywords)

        message_body = (
            f"🚨 *CIRCULAR ALERT*\n"
            f"*Title:* {title}\n"
            f"*Keywords:* {keywords_str}\n"
            f"*Snippet:* {snippet}\n"
        )
        if url:
            message_body += f"\n🔗 *Link:* {url}"

        if self.provider in ("whatomate", "whautomate"):
            return self._send_via_whatomate(message_body, title)
        elif self.provider == "twilio":
            return self._send_via_twilio(message_body, title)
        elif self.provider == "meta":
            return self._send_via_meta(message_body, title)
        else:
            logger.warning(f"[WhatsApp] Unknown provider '{self.provider}'")
            return False

    def _send_via_whatomate(self, body: str, title: str) -> bool:
        """Sends WhatsApp message via Whatomate / Whautomate REST API."""
        if not self.whatomate_url or "YOUR_" in self.whatomate_url:
            logger.warning("[WhatsApp/Whatomate] WHATOMATE_URL missing or unconfigured.")
            print(f"👉 [WhatsApp Whatomate DRY RUN] Would notify: '{title}'")
            return False

        # Endpoint construction
        if "/api/contacts/" in self.whatomate_url:
            endpoint = self.whatomate_url
        elif self.whatomate_contact_id:
            base = self.whatomate_url.rstrip("/")
            endpoint = f"{base}/api/contacts/{self.whatomate_contact_id}/messages"
        else:
            endpoint = self.whatomate_url

        payload = {
            "text": body,
            "message": body,
            "to": self.to_number
        }

        headers = {
            "Content-Type": "application/json"
        }
        if self.whatomate_api_key:
            headers["X-API-Key"] = self.whatomate_api_key
            headers["Authorization"] = f"Bearer {self.whatomate_api_key}"

        try:
            import time
            if self.delay_seconds > 0:
                time.sleep(self.delay_seconds)  # Configurable rate limit pause
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201, 202, 204):
                    logger.info("[WhatsApp/Whatomate] Notification dispatched successfully.")
                    print(f"✅ [WhatsApp/Whatomate] Message sent for: '{title}'")
                    return True
                else:
                    logger.error(f"[WhatsApp/Whatomate] Status code: {response.status}")
                    return False

        except urllib.error.URLError as e:
            logger.error(f"[WhatsApp/Whatomate Error] HTTP Error: {e}")
            print(f"❌ [WhatsApp Whatomate Error] {e}")
            return False
        except Exception as e:
            logger.error(f"[WhatsApp/Whatomate Error] {e}")
            print(f"❌ [WhatsApp Whatomate Error] {e}")
            return False

    def _send_via_twilio(self, body: str, title: str) -> bool:
        if not self.account_sid or not self.auth_token or not self.to_number:
            logger.warning("[WhatsApp/Twilio] Credentials missing. Skipping dispatch.")
            print(f"👉 [WhatsApp DRY RUN] Would notify to {self.to_number or 'Target Number'}: '{title}'")
            return False

        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        form_data = urllib.parse.urlencode({
            "From": self.from_number,
            "To": self.to_number,
            "Body": body
        }).encode("utf-8")

        auth_str = f"{self.account_sid}:{self.auth_token}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            req = urllib.request.Request(twilio_url, data=form_data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    logger.info("[WhatsApp/Twilio] Notification dispatched successfully.")
                    print(f"✅ [WhatsApp] Message sent to {self.to_number} for: '{title}'")
                    return True
                else:
                    logger.error(f"[WhatsApp/Twilio] Status code: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"[WhatsApp/Twilio Error] {e}")
            print(f"❌ [WhatsApp Error] {e}")
            return False

    def _send_via_meta(self, body: str, title: str) -> bool:
        if not self.meta_token or not self.meta_phone_id or not self.to_number:
            logger.warning("[WhatsApp/Meta] Token or Phone ID missing. Skipping dispatch.")
            print(f"👉 [WhatsApp Meta DRY RUN] Would notify: '{title}'")
            return False

        meta_url = f"https://graph.facebook.com/v17.0/{self.meta_phone_id}/messages"
        recipient = self.to_number.replace("whatsapp:", "").replace("+", "")

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": body}
        }

        headers = {
            "Authorization": f"Bearer {self.meta_token}",
            "Content-Type": "application/json"
        }

        try:
            req = urllib.request.Request(meta_url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    print(f"✅ [WhatsApp Meta] Message sent to {recipient} for: '{title}'")
                    return True
                return False
        except Exception as e:
            print(f"❌ [WhatsApp Meta Error] {e}")
            return False
