from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import threading
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContactSession(BaseModel):
    phone_number: str
    contact_name: Optional[str] = None
    messages: List[ChatMessage] = Field(default_factory=list)
    human_takeover_until: Optional[datetime] = None
    last_interaction: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    triage_history: List[str] = Field(default_factory=list)

class SessionManager:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self._sessions: Dict[str, ContactSession] = {}
        self._lock = threading.RLock()

    def get_or_create_session(self, phone_number: str, contact_name: Optional[str] = None) -> ContactSession:
        with self._lock:
            if phone_number not in self._sessions:
                self._sessions[phone_number] = ContactSession(
                    phone_number=phone_number,
                    contact_name=contact_name
                )
            session = self._sessions[phone_number]
            if contact_name and not session.contact_name:
                session.contact_name = contact_name
            return session

    def add_message(self, phone_number: str, role: str, content: str):
        with self._lock:
            session = self.get_or_create_session(phone_number)
            session.messages.append(ChatMessage(role=role, content=content))
            session.last_interaction = datetime.now(timezone.utc)
            # Trim to max_history
            if len(session.messages) > self.max_history:
                session.messages = session.messages[-self.max_history:]

    def get_recent_history(self, phone_number: str) -> List[ChatMessage]:
        with self._lock:
            if phone_number in self._sessions:
                return list(self._sessions[phone_number].messages)
            return []

    def is_human_takeover_active(self, phone_number: str) -> bool:
        with self._lock:
            session = self._sessions.get(phone_number)
            if not session or not session.human_takeover_until:
                return False
            if datetime.now(timezone.utc) < session.human_takeover_until:
                return True
            # Expired takeover
            session.human_takeover_until = None
            return False

    def activate_human_takeover(self, phone_number: str, duration_minutes: int = 120):
        with self._lock:
            session = self.get_or_create_session(phone_number)
            session.human_takeover_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

    def deactivate_human_takeover(self, phone_number: str):
        with self._lock:
            if phone_number in self._sessions:
                self._sessions[phone_number].human_takeover_until = None

    def record_triage(self, phone_number: str, category: str):
        with self._lock:
            session = self.get_or_create_session(phone_number)
            session.triage_history.append(category)

    def get_all_sessions(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "phone_number": s.phone_number,
                    "contact_name": s.contact_name,
                    "message_count": len(s.messages),
                    "human_takeover_active": self.is_human_takeover_active(s.phone_number),
                    "last_interaction": s.last_interaction.isoformat(),
                    "latest_triage": s.triage_history[-1] if s.triage_history else None
                }
                for s in self._sessions.values()
            ]

    def clear(self):
        with self._lock:
            self._sessions.clear()

session_manager = SessionManager()
