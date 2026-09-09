import pytest
from fastapi.testclient import TestClient
from src.server import app
from src.memory.session_manager import session_manager

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "endpoints" in data

def test_api_message_scheduling():
    session_manager.clear()
    payload = {
        "phone": "+1-415-999-0001",
        "name": "David",
        "message": "Can we set up a 15 min meeting to talk about consulting?"
    }
    response = client.post("/api/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "calendly" in data["reply"].lower()

def test_twilio_webhook_endpoint():
    session_manager.clear()
    form = {
        "From": "whatsapp:+14159990002",
        "Body": "Hello Adarsh, how are you?",
        "ProfileName": "Emma"
    }
    response = client.post("/webhook/twilio", data=form)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert "<Response><Message>" in response.text

def test_meta_webhook_verification():
    # Valid verify token
    response = client.get("/webhook/meta", params={
        "hub.mode": "subscribe",
        "hub.challenge": "challenge_12345",
        "hub.verify_token": "whatsapp_verify_token"
    })
    assert response.status_code == 200
    assert response.text == "challenge_12345"

    # Invalid verify token
    invalid_response = client.get("/webhook/meta", params={
        "hub.mode": "subscribe",
        "hub.challenge": "challenge_12345",
        "hub.verify_token": "bad_token"
    })
    assert invalid_response.status_code == 403

def test_takeover_api_endpoints():
    phone = "+1-415-999-0003"
    # Enable takeover
    res1 = client.post(f"/api/sessions/{phone}/takeover", json={"duration_minutes": 60})
    assert res1.status_code == 200
    assert res1.json()["status"] == "takeover_activated"

    # Verify session list shows active takeover
    res_list = client.get("/api/sessions")
    assert res_list.status_code == 200

    # Disable takeover
    res2 = client.delete(f"/api/sessions/{phone}/takeover")
    assert res2.status_code == 200
    assert res2.json()["status"] == "takeover_deactivated"
