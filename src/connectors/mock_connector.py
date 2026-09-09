from typing import Tuple, Optional, Dict, List
from src.connectors.base import BaseWhatsAppConnector

class MockWhatsAppConnector(BaseWhatsAppConnector):
    def __init__(self):
        self.sent_messages: List[Dict[str, str]] = []

    def parse_incoming(self, payload: Dict[str, str]) -> Tuple[str, Optional[str], str]:
        return (
            payload.get("phone", "+1234567890"),
            payload.get("name", "Test User"),
            payload.get("text", "")
        )

    async def send_message(self, to_number: str, message_text: str) -> bool:
        self.sent_messages.append({
            "to": to_number,
            "text": message_text
        })
        return True
