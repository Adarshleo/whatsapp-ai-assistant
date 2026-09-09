import logging
from typing import Optional
from fastapi import FastAPI, Request, Form, Response, Query, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from config import settings
from src.pipeline import pipeline
from src.memory.session_manager import session_manager
from src.connectors.twilio_connector import TwilioWhatsAppConnector
from src.connectors.meta_connector import MetaWhatsAppConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("WhatsAppServer")

app = FastAPI(
    title="Professional WhatsApp AI Assistant",
    description="Intelligent multi-agent assistant that responds to WhatsApp messages on your behalf.",
    version="1.0.0"
)

# Connectors
twilio_connector = TwilioWhatsAppConnector(
    account_sid=settings.TWILIO_ACCOUNT_SID,
    auth_token=settings.TWILIO_AUTH_TOKEN,
    from_number=settings.TWILIO_WHATSAPP_NUMBER
)

meta_connector = MetaWhatsAppConnector(
    verify_token=settings.META_VERIFY_TOKEN,
    access_token=settings.META_ACCESS_TOKEN,
    phone_number_id=settings.META_PHONE_NUMBER_ID
)

# Request Models
class DirectMessageRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    message: str

class TakeoverRequest(BaseModel):
    duration_minutes: int = 120

@app.get("/")
def read_root():
    return {
        "status": "online",
        "assistant_name": settings.BOT_NAME,
        "owner": settings.OWNER_NAME,
        "provider": settings.AI_PROVIDER,
        "endpoints": {
            "twilio_webhook": "/webhook/twilio",
            "meta_webhook": "/webhook/meta",
            "test_message_api": "/api/message",
            "sessions_api": "/api/sessions"
        }
    }

# =========================================================================
# Twilio WhatsApp Webhook
# =========================================================================
@app.post("/webhook/twilio")
async def twilio_webhook(
    From: str = Form(...),
    Body: str = Form(""),
    ProfileName: Optional[str] = Form(None)
):
    """Webhook endpoint for Twilio incoming WhatsApp messages."""
    form_data = {"From": From, "Body": Body, "ProfileName": ProfileName or ""}
    phone_number, contact_name, message_body = twilio_connector.parse_incoming(form_data)
    
    logger.info(f"Twilio Incoming from {contact_name or 'Unknown'} ({phone_number}): {message_body}")

    result = await pipeline.process_message(phone_number, contact_name, message_body)
    reply_text = result.get("reply") or ""

    # Return Twilio TwiML XML
    twiml = twilio_connector.create_twiml_response(reply_text)
    return Response(content=twiml, media_type="application/xml")

# =========================================================================
# Meta WhatsApp Cloud API Webhook
# =========================================================================
@app.get("/webhook/meta")
def meta_verify(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """Meta Webhook Challenge Verification."""
    challenge = meta_connector.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")

@app.post("/webhook/meta")
async def meta_webhook(request: Request):
    """Webhook endpoint for Meta WhatsApp Cloud API incoming events."""
    payload = await request.json()
    phone_number, contact_name, message_body = meta_connector.parse_incoming(payload)

    if not phone_number or not message_body:
        return {"status": "no_text_message"}

    logger.info(f"Meta Incoming from {contact_name or 'Unknown'} ({phone_number}): {message_body}")
    result = await pipeline.process_message(phone_number, contact_name, message_body)
    
    reply_text = result.get("reply")
    if reply_text:
        await meta_connector.send_message(phone_number, reply_text)

    return {"status": "received", "action": result.get("status")}

# =========================================================================
# Direct API & Management Endpoints
# =========================================================================
@app.post("/api/message")
async def send_test_message(req: DirectMessageRequest):
    """Direct API to simulate or route a message from any external bridge."""
    result = await pipeline.process_message(req.phone, req.name, req.message)
    return result

@app.get("/api/sessions")
def get_sessions():
    """Returns all active contact sessions and statuses."""
    return {"sessions": session_manager.get_all_sessions()}

@app.post("/api/sessions/{phone}/takeover")
def enable_takeover(phone: str, req: TakeoverRequest):
    """Manually pause bot auto-replies for a specific contact."""
    session_manager.activate_human_takeover(phone, req.duration_minutes)
    return {"status": "takeover_activated", "phone": phone, "minutes": req.duration_minutes}

@app.delete("/api/sessions/{phone}/takeover")
def disable_takeover(phone: str):
    """Resume bot auto-replies for a specific contact."""
    session_manager.deactivate_human_takeover(phone)
    return {"status": "takeover_deactivated", "phone": phone}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
