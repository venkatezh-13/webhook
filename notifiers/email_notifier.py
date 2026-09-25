import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class EmailNotifier(BaseNotifier):
    """
    Email Notifier sending HTML formatted alert emails via SMTP.
    """

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        use_tls: bool = True,
        smtp_user: str = "",
        smtp_password: str = "",
        email_from: str = "",
        email_to: str = ""
    ):
        super().__init__("Email")
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port) if smtp_port else 587
        self.use_tls = use_tls
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from or smtp_user
        self.email_to = email_to

    def send_notification(self, alert: Dict[str, Any], matched_keywords: List[str], snippet: str) -> bool:
        if not self.smtp_user or not self.smtp_password or not self.email_to:
            logger.warning("[Email] SMTP credentials missing. Skipping email dispatch.")
            print(f"👉 [Email DRY RUN] Would send email to '{self.email_to or 'Target Email'}': '{alert.get('title')}'")
            return False

        title = alert.get("title", "Untitled Circular Alert")
        url = alert.get("url", "#")
        keywords_html = " ".join([
            f'<span style="background-color: #fee2e2; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-weight: bold; margin-right: 4px;">{kw}</span>'
            for kw in matched_keywords
        ])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f5; margin: 0; padding: 20px; }}
                .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
                .header {{ border-bottom: 2px solid #e4e4e7; padding-bottom: 12px; margin-bottom: 20px; }}
                .title {{ font-size: 20px; font-weight: 700; color: #18181b; margin: 0 0 10px 0; }}
                .snippet {{ background-color: #f8fafc; border-left: 4px solid #0284c7; padding: 12px 16px; font-size: 14px; color: #334155; margin: 16px 0; line-height: 1.5; }}
                .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; font-size: 14px; margin-top: 12px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="header">
                    <h2 style="color: #dc2626; margin: 0;">🚨 Circular Alert Triggered</h2>
                </div>
                <div class="title">{title}</div>
                <div style="margin-bottom: 12px;">
                    <strong>Matched Keywords:</strong> {keywords_html}
                </div>
                <div class="snippet">
                    <strong>Snippet:</strong><br>{snippet}
                </div>
                {f'<a href="{url}" class="btn" target="_blank">View Full Circular Document</a>' if url else ''}
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🚨 Alert: {title}"
        msg["From"] = self.email_from
        msg["To"] = self.email_to
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, [self.email_to], msg.as_string())
            
            logger.info(f"[Email] Successfully sent alert email to {self.email_to}")
            print(f"✅ [Email] Sent alert email to {self.email_to} for: '{title}'")
            return True
        except Exception as e:
            logger.error(f"[Email Error] Failed to send email: {e}")
            print(f"❌ [Email Error] {e}")
            return False
