# 🤖 Professional WhatsApp AI Assistant (Python)

An enterprise-grade, multi-agent Python WhatsApp chatbot designed to act as your **Executive AI Assistant**. It replies intelligently, politely, and crisply on your behalf, triages incoming inquiries, answers frequent questions from your custom profile, and halts auto-replies whenever human takeover is requested.

---

## 🌟 Why This Architecture is Professional

Most basic WhatsApp bots are single-prompt wrappers that either sound generic, hallucinate promises, or annoy contacts. This system follows a **Multi-Agent Architecture**:

1. **Gatekeeper / Triage Agent**:
   - Classifies every message before replying into:
     - `URGENT`: Critical alerts, emergencies, production bugs (Alerts you immediately and triggers escalation).
     - `SCHEDULING`: Meeting/call inquiries (Shares your Calendly or requests agenda and times).
     - `GENERAL_FAQ`: Questions about your background, skills, rates, availability (Answered strictly from grounded facts).
     - `CASUAL_CHAT`: Greetings or light conversation (Replies politely and sets office hours expectations).
     - `SPAM / MARKETING`: Unsolicited advertisements or bot links (Silently ignored).
     - `HUMAN_TAKEOVER_REQUEST`: Triggers when contact types `#human` or asks to speak directly.
2. **Executive Assistant / Persona Agent**:
   - Strictly guided by `data/user_profile.yaml` and `data/knowledge_base.md`.
   - Never commits to contracts, pricing, or deadlines without your approval.
   - Maintains a short, mobile-optimized tone (1 to 4 sentences).
3. **Escalation & Safety Agent**:
   - Manages **Human Takeover**: If you or your contact request direct human contact, the bot pauses auto-replies for that contact for a configurable window (e.g. 2 hours).
   - Logs urgent inquiries in real-time to `data/escalations.log`.
4. **Session Memory**:
   - Thread-safe conversation history tracking per phone number to remember multi-turn context.

---

## 📁 Project Structure

```
d:/AI/Agent/
├── .env                        # Active environment variables and API keys
├── .env.example                # Example configuration template
├── requirements.txt            # Python dependencies
├── config.py                   # Centralized Pydantic settings
├── data/
│   ├── user_profile.yaml       # YOUR bio, office hours, Calendly link, rules
│   ├── knowledge_base.md       # YOUR FAQs, services, and company details
│   └── escalations.log         # Audit log of urgent and handover requests
├── src/
│   ├── agents/
│   │   ├── triage_agent.py     # Intent & priority classification
│   │   ├── response_agent.py   # Context-aware professional response generator
│   │   └── escalation_agent.py # Escalations and human handoff manager
│   ├── memory/
│   │   └── session_manager.py  # Thread-safe contact session buffer & takeover state
│   ├── connectors/
│   │   ├── base.py             # Abstract WhatsApp Connector
│   │   ├── twilio_connector.py # Twilio WhatsApp Webhook & REST API
│   │   ├── meta_connector.py   # Meta WhatsApp Cloud API
│   │   └── mock_connector.py   # Testing simulator connector
│   ├── pipeline.py             # End-to-end orchestration pipeline
│   └── server.py               # FastAPI server exposing webhooks & REST API
├── run_simulator.py            # Interactive CLI terminal simulator
└── tests/
    ├── test_agents.py          # Unit & pipeline tests
    └── test_server.py          # FastAPI endpoint tests
```

---

## 🚀 Quick Start (Testing Immediately via Terminal)

You do **not** need to wait for WhatsApp approval or API keys to test the bot. The system includes an interactive terminal simulator that runs in grounded mode.

### 1. Run the Interactive Simulator
```bash
# In your terminal inside d:\AI\Agent
.\.venv\Scripts\python.exe run_simulator.py
```

### 2. Test Realistic Scenarios
Inside the simulator, type:
- `1` : Test a meeting scheduling inquiry
- `2` : Test an urgent production bug alert
- `3` : Test a general FAQ inquiry about your services
- `4` : Test `#human` takeover
- `all` : Run all 6 preset scenarios consecutively
- Or type any custom message!

---

## ⚙️ Customizing Your Profile & Knowledge

To make the assistant speak accurately for **you**:

1. **Edit `data/user_profile.yaml`**:
   - Update `owner_name`, `title`, and `bio`.
   - Set your `working_hours` and `time_zone`.
   - Update `calendly_link` with your real booking link.
   - Adjust `rules` and `tone`.

2. **Edit `data/knowledge_base.md`**:
   - Add your common questions and answers (pricing, portfolio, location, contact methods).

---

## 🔑 Activating an AI Provider (Gemini / OpenAI)

Open `.env` and set:
```ini
# Choose "gemini", "openai", or "mock"
AI_PROVIDER=gemini

# If using Gemini (recommended for speed & high free-tier limits):
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash

# If using OpenAI:
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

---

## 🌐 Connecting to WhatsApp

### Method A: Twilio WhatsApp (Fastest Sandbox Setup)

1. Sign up for a free account at [Twilio](https://www.twilio.com/).
2. Go to **Messaging > Try it out > Send a WhatsApp message** to activate the **Twilio WhatsApp Sandbox**.
3. Copy your **Account SID** and **Auth Token** into `.env`:
   ```ini
   TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```
4. Start the FastAPI server:
   ```bash
   .\.venv\Scripts\uvicorn.exe src.server:app --reload --port 8000
   ```
5. Expose your local port using **Ngrok**:
   ```bash
   ngrok http 8000
   ```
6. In your Twilio Sandbox Settings, paste your webhook URL:
   `https://<your-ngrok-subdomain>.ngrok-free.app/webhook/twilio` (HTTP POST).
7. Send a WhatsApp message to the Twilio number—your bot will reply instantly!

---

### Method B: Meta WhatsApp Cloud API (Official Enterprise)

1. Register at [developers.facebook.com](https://developers.facebook.com/).
2. Create an App > Select **Business** type > Add **WhatsApp**.
3. Under WhatsApp > **API Setup**, grab your **Temporary Access Token** and **Phone Number ID**.
4. In `.env`:
   ```ini
   META_VERIFY_TOKEN=any_secret_passphrase_you_choose
   META_ACCESS_TOKEN=EAAG...
   META_PHONE_NUMBER_ID=1000...
   ```
5. In the Meta App Dashboard under WhatsApp > **Configuration**:
   - Set Callback URL: `https://<your-ngrok-subdomain>.ngrok-free.app/webhook/meta`
   - Set Verify Token: (must match `META_VERIFY_TOKEN`)
   - Subscribe to the `messages` webhook field.

---

## 🧪 Running Automated Tests

Run the test suite anytime to verify all components:
```bash
.\.venv\Scripts\pytest.exe -v
```
All 11 tests check classification, session memory, takeover timeouts, and API routes.
