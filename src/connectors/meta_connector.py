import logging
from typing import Tuple, Optional, Dict, Any
import httpx
from src.connectors.base import BaseWhatsAppConnector

logger = logging.getLogger("MetaConnector")

class MetaWhatsAppConnector(BaseWhatsAppConnector):
    def __init__(self, verify_token: str = "", access_token: str = "", phone_number_id: str = ""):
        self.verify_token = verify_token
        self.access_token = access_token
        self.phone_number_id = phone_number_id

    def verify_webhook(self, mode: Optional[str], token: Optional[str], challenge: Optional[str]) -> Optional[str]:
        """Validates Meta webhook verification challenge."""
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def parse_incoming(self, payload: Dict[str, Any]) -> Tuple[str, Optional[str], str]:
        """
        Extracts phone, name, and body from Meta Cloud API webhook JSON.
        """
        phone_number = ""
        contact_name = None
        message_body = ""

        try:
            entry = payload.get("entry", [])[0]
            change = entry.get("changes", [])[0]
            value = change.get("value", {})

            # Get contact name if available
            contacts = value.get("contacts", [])
            if contacts:
                contact_name = contacts[0].get("profile", {}).get("name")

            # Get message content
            messages = value.get("messages", [])
            if messages:
                msg = messages[0]
                phone_number = msg.get("from", "")
                if msg.get("type") == "text":
                    message_body = msg.get("text", {}).get("body", "")
        except Exception as e:
            logger.error(f"Error parsing Meta webhook payload: {e}")

        return phone_number, contact_name, message_body

    async def send_message(self, to_number: str, message_text: str) -> bool:
        """Sends an outgoing message via Meta WhatsApp Cloud API."""
        if not self.access_token or not self.phone_number_id:
            logger.warning("Meta Cloud API credentials not configured; simulated send.")
            return True

        url = f"https://graph.facebook.com/v19.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"preview_url": False, "body": message_text}
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=data, headers=headers, timeout=10.0)
                if res.status_code in [200, 201]:
                    return True
                logger.error(f"Meta API error ({res.status_code}): {res.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Meta Cloud API message: {e}")
            return False
