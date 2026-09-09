import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from src.memory.session_manager import session_manager
from src.agents.triage_agent import TriageResult

logger = logging.getLogger("EscalationAgent")

class EscalationAgent:
    def __init__(self, log_dir: Optional[Path] = None, takeover_duration_minutes: int = 120):
        self.log_dir = log_dir or (Path(__file__).resolve().parents[2] / "data")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.escalation_log_file = self.log_dir / "escalations.log"
        self.takeover_duration_minutes = takeover_duration_minutes

    def handle_escalation(
        self,
        phone_number: str,
        message: str,
        triage: TriageResult,
        contact_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Processes urgent or human-takeover requests."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_human_request = triage.category == "HUMAN_TAKEOVER_REQUEST"
        is_urgent = triage.category == "URGENT" or triage.urgency >= 4

        # If user explicitly asked for human or takeover
        if is_human_request:
            session_manager.activate_human_takeover(phone_number, self.takeover_duration_minutes)
            reply_text = (
                "🤖 [Assistant]: Understood! I have paused automated replies for this conversation. "
                "Adarsh has been notified and will reply to you personally."
            )
        elif is_urgent:
            reply_text = (
                "🚨 [Assistant]: Thank you for flagging this. I have marked your message as URGENT "
                "and directly alerted Adarsh. He will reach out to you as quickly as possible."
            )
        else:
            reply_text = None

        # Log alert to escalations.log
        log_entry = (
            f"[{timestamp}] [PRIORITY {triage.urgency}/5] [{triage.category}] "
            f"Contact: {contact_name or 'Unknown'} ({phone_number})\n"
            f"Message: {message}\n"
            f"Summary: {triage.summary}\n"
            f"Action Taken: {triage.action} | Human takeover activated: {is_human_request}\n"
            f"{'-'*60}\n"
        )
        
        try:
            with open(self.escalation_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write escalation log: {e}")

        logger.warning(f"ESCALATION TRIGGERED: [{triage.category}] from {phone_number}: {message}")

        return {
            "escalated": True,
            "human_takeover": is_human_request,
            "reply": reply_text
        }
