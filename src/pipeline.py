import logging
from typing import Optional, Dict, Any
from config import settings
from src.memory.session_manager import session_manager
from src.agents.triage_agent import TriageAgent, TriageResult
from src.agents.escalation_agent import EscalationAgent
from src.agents.response_agent import ResponseAgent

logger = logging.getLogger("AssistantPipeline")

class AssistantPipeline:
    def __init__(self):
        # Initialize Triage Agent
        self.triage_agent = TriageAgent(
            provider=settings.AI_PROVIDER,
            api_key=settings.GEMINI_API_KEY if settings.AI_PROVIDER == "gemini" else settings.OPENAI_API_KEY,
            gemini_model=settings.GEMINI_MODEL,
            openai_model=settings.OPENAI_MODEL
        )
        
        # Initialize Escalation Agent
        self.escalation_agent = EscalationAgent(
            takeover_duration_minutes=settings.HUMAN_TAKEOVER_MINUTES
        )
        
        # Initialize Response Agent
        self.response_agent = ResponseAgent(
            profile_path=settings.PROFILE_PATH,
            knowledge_base_path=settings.KNOWLEDGE_BASE_PATH,
            provider=settings.AI_PROVIDER,
            api_key=settings.GEMINI_API_KEY if settings.AI_PROVIDER == "gemini" else settings.OPENAI_API_KEY,
            gemini_model=settings.GEMINI_MODEL,
            openai_model=settings.OPENAI_MODEL
        )

    async def process_message(
        self,
        phone_number: str,
        contact_name: Optional[str],
        message_text: str
    ) -> Dict[str, Any]:
        """
        End-to-end processing pipeline:
        1. Check Human Takeover
        2. Triage & Classify
        3. Escalate / Handover if needed
        4. Generate Grounded Professional Reply
        5. Update Session Memory
        """
        # 1. Check if human takeover is currently active
        if session_manager.is_human_takeover_active(phone_number):
            logger.info(f"Human takeover active for {phone_number}. Bot auto-reply is silenced.")
            # Record user message in history so the user has full transcript
            session_manager.add_message(phone_number, "user", message_text)
            return {
                "status": "silenced_human_takeover",
                "phone_number": phone_number,
                "reply": None,
                "reason": "Human takeover active for this contact."
            }

        # Record incoming message
        session_manager.add_message(phone_number, "user", message_text)

        # 2. Triage & Classify
        triage: TriageResult = await self.triage_agent.classify(message_text, contact_name)
        session_manager.record_triage(phone_number, triage.category)

        logger.info(f"Triage: [{triage.category}] Urgency: {triage.urgency}/5 Action: {triage.action}")

        # 3. Handle Human Handover / Urgent Escalation
        if triage.action == "human_handover":
            esc = self.escalation_agent.handle_escalation(phone_number, message_text, triage, contact_name)
            reply = esc.get("reply")
            if reply:
                session_manager.add_message(phone_number, "assistant", reply)
            return {
                "status": "human_handover_activated",
                "phone_number": phone_number,
                "reply": reply,
                "triage": triage.model_dump()
            }

        if triage.action == "ignore":
            logger.info(f"Spam message ignored from {phone_number}.")
            return {
                "status": "ignored_spam",
                "phone_number": phone_number,
                "reply": None,
                "triage": triage.model_dump()
            }

        if triage.action == "escalate_only":
            self.escalation_agent.handle_escalation(phone_number, message_text, triage, contact_name)
            return {
                "status": "escalated_no_reply",
                "phone_number": phone_number,
                "reply": None,
                "triage": triage.model_dump()
            }

        # If urgent, trigger escalation alert in background
        if triage.category == "URGENT" or triage.action == "escalate_and_reply":
            self.escalation_agent.handle_escalation(phone_number, message_text, triage, contact_name)

        # 4. Generate Response
        history = session_manager.get_recent_history(phone_number)
        reply_text = await self.response_agent.generate_response(
            incoming_message=message_text,
            triage=triage,
            history=history,
            contact_name=contact_name
        )

        if reply_text:
            session_manager.add_message(phone_number, "assistant", reply_text)

        return {
            "status": "success",
            "phone_number": phone_number,
            "reply": reply_text,
            "triage": triage.model_dump()
        }

pipeline = AssistantPipeline()
