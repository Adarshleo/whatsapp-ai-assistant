from abc import ABC, abstractmethod
from typing import Tuple, Optional, Any

class BaseWhatsAppConnector(ABC):
    @abstractmethod
    def parse_incoming(self, payload: Any) -> Tuple[str, Optional[str], str]:
        """
        Parses provider-specific payload into:
        (phone_number, contact_name, message_text)
        """
        pass

    @abstractmethod
    async def send_message(self, to_number: str, message_text: str) -> bool:
        """Sends an outgoing WhatsApp message."""
        pass
