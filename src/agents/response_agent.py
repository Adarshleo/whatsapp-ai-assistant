import yaml
from pathlib import Path
from typing import List, Optional
from src.memory.session_manager import ChatMessage
from src.agents.triage_agent import TriageResult

class ResponseAgent:
    def __init__(
        self,
        profile_path: Path,
        knowledge_base_path: Path,
        provider: str = "mock",
        api_key: str = "",
        gemini_model: str = "gemini-2.5-flash",
        openai_model: str = "gpt-4o-mini"
    ):
        self.profile_path = profile_path
        self.knowledge_base_path = knowledge_base_path
        self.provider = provider
        self.api_key = api_key
        self.gemini_model = gemini_model
        self.openai_model = openai_model
        
        self.profile_data = self._load_profile()
        self.knowledge_base_text = self._load_knowledge_base()

    def _load_profile(self) -> dict:
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return {"owner_name": "Adarsh", "title": "Software Engineer"}

    def _load_knowledge_base(self) -> str:
        if self.knowledge_base_path.exists():
            try:
                with open(self.knowledge_base_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def _build_system_prompt(self) -> str:
        owner = self.profile_data.get("owner_name", "Adarsh")
        title = self.profile_data.get("title", "Professional")
        org = self.profile_data.get("organization", "")
        hours = self.profile_data.get("working_hours", "Business hours")
        calendly = self.profile_data.get("calendly_link", "")
        rules = "\n".join(f"- {r}" for r in self.profile_data.get("rules", []))
        tone = self.profile_data.get("tone", "Professional, polite, and concise")
        status = self.profile_data.get("current_status", "")

        return f"""You are the AI Executive Assistant representing {owner} ({title} at {org}) on WhatsApp.
Your job is to respond politely, crisply, and professionally to incoming WhatsApp messages on {owner}'s behalf.

=== OWNER PROFILE & CONTEXT ===
- Owner Name: {owner}
- Title / Role: {title}
- Working Hours: {hours}
- Current Status: {status}
- Meeting Booking Link: {calendly}
- Tone & Voice: {tone}

=== STRICT OPERATIONAL RULES ===
{rules}
- Never pretend you are {owner} directly; you are {owner}'s AI Assistant.
- Keep responses short, clear, and easy to read on mobile (1 to 4 sentences).
- If someone requests a meeting, provide the Calendly link or invite them to share their available slots and agenda.
- Never confirm pricing, signing of contracts, or binding deadlines without {owner}'s direct approval.

=== GROUNDED KNOWLEDGE BASE ===
{self.knowledge_base_text}
"""

    async def generate_response(
        self,
        incoming_message: str,
        triage: TriageResult,
        history: List[ChatMessage],
        contact_name: Optional[str] = None
    ) -> str:
        # If triage marked as ignore (spam)
        if triage.action == "ignore":
            return ""

        # If provider is mock or missing API key, use grounded deterministic template responses
        if self.provider == "mock" or not self.api_key:
            return self._generate_mock_response(incoming_message, triage, contact_name)

        if self.provider == "gemini":
            return await self._generate_gemini(incoming_message, history, contact_name)
        elif self.provider == "openai":
            return await self._generate_openai(incoming_message, history, contact_name)

        return self._generate_mock_response(incoming_message, triage, contact_name)

    def _generate_mock_response(
        self,
        message: str,
        triage: TriageResult,
        contact_name: Optional[str] = None
    ) -> str:
        """Grounded responses when running without external API keys."""
        owner = self.profile_data.get("owner_name", "Adarsh")
        calendly = self.profile_data.get("calendly_link", "https://calendly.com/adarsh/30min")
        hours = self.profile_data.get("working_hours", "Mon-Fri 9:30 AM - 6:30 PM IST")
        
        greeting = f"Hi {contact_name}," if contact_name else "Hi,"
        cat = triage.category

        if cat == "SCHEDULING":
            return (
                f"{greeting} I'm {owner}'s AI assistant. {owner} would be glad to connect. "
                f"You can pick a convenient 30-minute slot on his calendar here: {calendly} "
                f"or let us know your preferred times and agenda."
            )
        elif cat == "URGENT":
            return (
                f"{greeting} I'm {owner}'s AI assistant. I have marked this as urgent and directly alerted {owner}. "
                f"He will get back to you as soon as possible."
            )
        elif cat == "CASUAL_CHAT":
            return (
                f"{greeting} thanks for reaching out! I'm {owner}'s AI assistant. "
                f"{owner} is currently focused on work during office hours ({hours}), "
                f"but I've logged your message and he'll review it shortly. How can we help you today?"
            )
        elif cat == "GENERAL_FAQ":
            cleaned = message.lower()
            if "service" in cleaned or "what do you do" in cleaned or "specializ" in cleaned:
                return (
                    f"{greeting} {owner} specializes in AI Agents, Full-Stack Python engineering, "
                    f"and workflow automation. Feel free to share details about what you're looking to build!"
                )
            elif "rate" in cleaned or "cost" in cleaned or "price" in cleaned:
                return (
                    f"{greeting} project rates depend on the scope and timeline. "
                    f"Please share a brief summary of your project or book a discovery call at {calendly}, "
                    f"and {owner} will provide an estimate."
                )
            else:
                return (
                    f"{greeting} thanks for your inquiry! I'm {owner}'s AI assistant. "
                    f"I have noted your question and {owner} will get back to you with details during office hours ({hours})."
                )

        return (
            f"{greeting} I'm {owner}'s AI assistant. I have noted your message for {owner} and he will follow up shortly!"
        )

    async def _generate_gemini(
        self,
        incoming_message: str,
        history: List[ChatMessage],
        contact_name: Optional[str] = None
    ) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            system_prompt = self._build_system_prompt()
            
            # Format history
            conversation_history_text = "\n".join(
                f"{m.role.capitalize()}: {m.content}" for m in history[-6:]
            )
            
            prompt = f"""{system_prompt}

=== CONVERSATION HISTORY ===
{conversation_history_text}

Contact Name: {contact_name or 'Unknown'}
New Message: {incoming_message}

Please provide your short, professional response:"""

            response = client.models.generate_content(
                model=self.gemini_model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            owner = self.profile_data.get("owner_name", "Adarsh")
            return f"Hello! I am {owner}'s assistant. I have noted your message and {owner} will follow up shortly."

    async def _generate_openai(
        self,
        incoming_message: str,
        history: List[ChatMessage],
        contact_name: Optional[str] = None
    ) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            messages = [{"role": "system", "content": self._build_system_prompt()}]
            
            for m in history[-6:]:
                role = "assistant" if m.role == "assistant" else "user"
                messages.append({"role": role, "content": m.content})
                
            messages.append({"role": "user", "content": f"From {contact_name or 'User'}: {incoming_message}"})

            response = await client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            owner = self.profile_data.get("owner_name", "Adarsh")
            return f"Hello! I am {owner}'s assistant. I have noted your message and {owner} will follow up shortly."
