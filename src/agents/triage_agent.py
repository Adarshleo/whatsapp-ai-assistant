import re
import json
from typing import Optional
from pydantic import BaseModel, Field

class TriageResult(BaseModel):
    category: str = Field(description="URGENT, SCHEDULING, GENERAL_FAQ, CASUAL_CHAT, SPAM, or HUMAN_TAKEOVER_REQUEST")
    urgency: int = Field(ge=1, le=5, description="Urgency level from 1 (low) to 5 (critical)")
    summary: str = Field(description="Brief explanation of the classification")
    action: str = Field(description="'auto_reply', 'escalate_and_reply', 'escalate_only', 'ignore', or 'human_handover'")

class TriageAgent:
    def __init__(self, provider: str = "mock", api_key: str = "", gemini_model: str = "gemini-2.5-flash", openai_model: str = "gpt-4o-mini"):
        self.provider = provider
        self.api_key = api_key
        self.gemini_model = gemini_model
        self.openai_model = openai_model

    def evaluate_rule_based(self, text: str) -> Optional[TriageResult]:
        """Fast, 100% deterministic rules for commands and obvious patterns."""
        cleaned = text.strip().lower()
        
        # Human takeover triggers
        if any(trigger in cleaned for trigger in ["#human", "speak to human", "talk to human", "real person", "stop bot", "disable bot", "talk to adarsh directly"]):
            return TriageResult(
                category="HUMAN_TAKEOVER_REQUEST",
                urgency=3,
                summary="User requested direct communication with a human.",
                action="human_handover"
            )
            
        # Emergency & Urgent triggers
        urgent_keywords = ["urgent", "emergency", "server down", "production down", "critical bug", "hacked", "hospital", "asap call"]
        if any(re.search(rf"\b{kw}\b", cleaned) for kw in urgent_keywords):
            return TriageResult(
                category="URGENT",
                urgency=5,
                summary="Message contains high-priority or critical emergency keywords.",
                action="escalate_and_reply"
            )
            
        # Scheduling triggers
        meeting_keywords = ["schedule", "meeting", "call tomorrow", "calendar", "zoom call", "google meet", "free for a call", "discuss project", "appointment", "chat this week"]
        if any(kw in cleaned for kw in meeting_keywords):
            return TriageResult(
                category="SCHEDULING",
                urgency=3,
                summary="Inquiry regarding setting up a meeting or call.",
                action="auto_reply"
            )
            
        # Obvious spam/promotions
        spam_keywords = ["crypto giveaway", "telegram channel", "earn $1000", "viagra", "lottery", "click link to claim"]
        if any(kw in cleaned for kw in spam_keywords):
            return TriageResult(
                category="SPAM",
                urgency=1,
                summary="Unsolicited promotional / spam message.",
                action="ignore"
            )
            
        # Simple casual greetings
        casual_greetings = ["hi", "hello", "hey", "good morning", "good evening", "how are you", "what's up", "wassup", "sup"]
        if cleaned in casual_greetings or re.fullmatch(r"^(hi|hello|hey|good morning|good evening)[\s!.]*", cleaned):
            return TriageResult(
                category="CASUAL_CHAT",
                urgency=2,
                summary="Casual or polite introductory greeting.",
                action="auto_reply"
            )

        return None

    async def classify(self, message: str, contact_name: Optional[str] = None) -> TriageResult:
        # First check deterministic rules
        rule_result = self.evaluate_rule_based(message)
        if rule_result:
            return rule_result

        # If provider is mock or no API key, use smart heuristic fallback
        if self.provider == "mock" or not self.api_key:
            return self._heuristic_classify(message)

        # Call LLM provider if configured
        if self.provider == "gemini":
            return await self._classify_gemini(message)
        elif self.provider == "openai":
            return await self._classify_openai(message)
        
        return self._heuristic_classify(message)

    def _heuristic_classify(self, message: str) -> TriageResult:
        cleaned = message.lower()
        if "?" in message or any(w in cleaned for w in ["what", "how", "who", "cost", "portfolio", "rate", "services", "experience"]):
            return TriageResult(
                category="GENERAL_FAQ",
                urgency=2,
                summary="Informational question or inquiry.",
                action="auto_reply"
            )
        return TriageResult(
            category="CASUAL_CHAT",
            urgency=2,
            summary="General incoming communication.",
            action="auto_reply"
        )

    async def _classify_gemini(self, message: str) -> TriageResult:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            prompt = f"""You are an incoming message triage classifier for an executive assistant.
Classify this WhatsApp message into JSON with keys: category, urgency, summary, action.
Allowed categories: URGENT, SCHEDULING, GENERAL_FAQ, CASUAL_CHAT, SPAM, HUMAN_TAKEOVER_REQUEST.
Urgency: 1 (lowest) to 5 (critical).
Allowed actions: auto_reply, escalate_and_reply, escalate_only, ignore, human_handover.

Message: "{message}"

Respond strictly with valid JSON."""

            response = client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            return TriageResult(**data)
        except Exception as e:
            # Fallback on failure
            res = self._heuristic_classify(message)
            res.summary += f" (Heuristic fallback due to: {e})"
            return res

    async def _classify_openai(self, message: str) -> TriageResult:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            system_prompt = (
                "You are an incoming message triage classifier. "
                "Classify the message into JSON: category (URGENT, SCHEDULING, GENERAL_FAQ, CASUAL_CHAT, SPAM, HUMAN_TAKEOVER_REQUEST), "
                "urgency (1 to 5), summary (short string), action (auto_reply, escalate_and_reply, escalate_only, ignore, human_handover)."
            )
            response = await client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            return TriageResult(**data)
        except Exception as e:
            res = self._heuristic_classify(message)
            res.summary += f" (Heuristic fallback due to: {e})"
            return res
