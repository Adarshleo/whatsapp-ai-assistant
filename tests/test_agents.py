import pytest
from pathlib import Path
from src.agents.triage_agent import TriageAgent, TriageResult
from src.agents.escalation_agent import EscalationAgent
from src.agents.response_agent import ResponseAgent
from src.memory.session_manager import SessionManager
from src.pipeline import AssistantPipeline
from src.connectors.twilio_connector import TwilioWhatsAppConnector
from src.connectors.meta_connector import MetaWhatsAppConnector

@pytest.fixture
def triage_agent():
    return TriageAgent(provider="mock")

@pytest.fixture
def session_mgr():
    sm = SessionManager(max_history=5)
    return sm

@pytest.fixture
def response_agent(tmp_path):
    profile_file = tmp_path / "user_profile.yaml"
    profile_file.write_text("""
owner_name: "Adarsh"
title: "AI Engineer"
calendly_link: "https://calendly.com/adarsh/test"
working_hours: "9 AM - 6 PM IST"
rules:
  - "Be polite and concise."
""", encoding="utf-8")

    kb_file = tmp_path / "knowledge_base.md"
    kb_file.write_text("Adarsh builds AI agents.", encoding="utf-8")

    return ResponseAgent(
        profile_path=profile_file,
        knowledge_base_path=kb_file,
        provider="mock"
    )

@pytest.mark.asyncio
async def test_triage_classification(triage_agent):
    # Test urgent
    res = await triage_agent.classify("URGENT: server is down!")
    assert res.category == "URGENT"
    assert res.urgency == 5
    assert res.action == "escalate_and_reply"

    # Test scheduling
    res = await triage_agent.classify("Can we schedule a meeting tomorrow?")
    assert res.category == "SCHEDULING"
    assert res.action == "auto_reply"

    # Test human handover
    res = await triage_agent.classify("#human I need to speak to someone")
    assert res.category == "HUMAN_TAKEOVER_REQUEST"
    assert res.action == "human_handover"

    # Test spam
    res = await triage_agent.classify("Claim your crypto giveaway now")
    assert res.category == "SPAM"
    assert res.action == "ignore"

def test_session_manager(session_mgr):
    phone = "+1-555-1234"
    # Add messages
    for i in range(7):
        session_mgr.add_message(phone, "user", f"msg {i}")

    history = session_mgr.get_recent_history(phone)
    assert len(history) == 5  # trimmed to max_history
    assert history[-1].content == "msg 6"

    # Test takeover
    assert not session_mgr.is_human_takeover_active(phone)
    session_mgr.activate_human_takeover(phone, duration_minutes=60)
    assert session_mgr.is_human_takeover_active(phone)
    session_mgr.deactivate_human_takeover(phone)
    assert not session_mgr.is_human_takeover_active(phone)

@pytest.mark.asyncio
async def test_response_agent(response_agent):
    triage = TriageResult(
        category="SCHEDULING",
        urgency=3,
        summary="meeting request",
        action="auto_reply"
    )
    reply = await response_agent.generate_response(
        incoming_message="Can we meet?",
        triage=triage,
        history=[],
        contact_name="Alice"
    )
    assert "https://calendly.com/adarsh/test" in reply
    assert "Adarsh" in reply

@pytest.mark.asyncio
async def test_end_to_end_pipeline():
    pipeline = AssistantPipeline()
    phone = "+1-999-888-7777"

    # 1. Normal scheduling inquiry
    res = await pipeline.process_message(phone, "Mark", "Hi Adarsh, can we schedule a call?")
    assert res["status"] == "success"
    assert "calendly" in res["reply"].lower()

    # 2. Trigger human handover
    handover = await pipeline.process_message(phone, "Mark", "#human please step in")
    assert handover["status"] == "human_handover_activated"

    # 3. Next message should be silenced due to active takeover
    silenced = await pipeline.process_message(phone, "Mark", "Are you there?")
    assert silenced["status"] == "silenced_human_takeover"
    assert silenced["reply"] is None

def test_twilio_connector():
    connector = TwilioWhatsAppConnector()
    phone, name, body = connector.parse_incoming({
        "From": "whatsapp:+1234567890",
        "ProfileName": "John Doe",
        "Body": "Hello world"
    })
    assert phone == "+1234567890"
    assert name == "John Doe"
    assert body == "Hello world"

    xml = connector.create_twiml_response("Hello from bot")
    assert "<Response><Message>Hello from bot</Message></Response>" in xml

def test_meta_connector():
    connector = MetaWhatsAppConnector(verify_token="test_token")
    # Test challenge verification
    challenge = connector.verify_webhook("subscribe", "test_token", "12345")
    assert challenge == "12345"

    mismatch = connector.verify_webhook("subscribe", "wrong_token", "12345")
    assert mismatch is None
