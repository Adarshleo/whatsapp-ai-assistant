import logging
from typing import Tuple, Optional, Dict
import httpx
from src.connectors.base import BaseWhatsAppConnector

logger = logging.getLogger("TwilioConnector")

class TwilioWhatsAppConnector(BaseWhatsAppConnector):
    def __init__(self, account_sid: str = "", auth_token: str = "", from_number: str = "whatsapp:+14155238886"):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def parse_incoming(self, form_data: Dict[str, str]) -> Tuple[str, Optional[str], str]:
        """
        Parses Twilio webhook POST form data:
        - From: 'whatsapp:+123456789'
        - ProfileName: 'John Doe'
        - Body: 'Hello'
        """
        raw_from = form_data.get("From", "")
        # Normalize: strip 'whatsapp:' prefix if present
        phone_number = raw_from.replace("whatsapp:", "").strip()
        contact_name = form_data.get("ProfileName")
        body = form_data.get("Body", "").strip()
        return phone_number, contact_name, body

    def create_twiml_response(self, reply_text: str) -> str:
        """Returns standard Twilio TwiML XML string."""
        safe_text = (
            reply_text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{safe_text}</Message></Response>'

    async def send_message(self, to_number: str, message_text: str) -> bool:
        """Sends a proactive message via Twilio REST API."""
        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured; simulated send only.")
            return True

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "From": self.from_number if self.from_number.startswith("whatsapp:") else f"whatsapp:{self.from_number}",
            "To": to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}",
            "Body": message_text
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, data=data, auth=(self.account_sid, self.auth_token), timeout=10.0)
                if res.status_code in [200, 201]:
                    return True
                logger.error(f"Twilio API error ({res.status_code}): {res.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Twilio message: {e}")
            return False
