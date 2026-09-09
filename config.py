from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # AI Engine settings
    AI_PROVIDER: str = Field(default="mock", description="'gemini', 'openai', or 'mock'")
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    
    # Model selections
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")

    # Personal profile & Assistant identity
    OWNER_NAME: str = Field(default="Adarsh")
    BOT_NAME: str = Field(default="Adarsh's AI Assistant")
    
    # Paths
    PROFILE_PATH: Path = BASE_DIR / "data" / "user_profile.yaml"
    KNOWLEDGE_BASE_PATH: Path = BASE_DIR / "data" / "knowledge_base.md"
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID: str = Field(default="")
    TWILIO_AUTH_TOKEN: str = Field(default="")
    TWILIO_WHATSAPP_NUMBER: str = Field(default="whatsapp:+14155238886")
    
    # Meta WhatsApp Cloud API Settings
    META_VERIFY_TOKEN: str = Field(default="whatsapp_verify_token")
    META_ACCESS_TOKEN: str = Field(default="")
    META_PHONE_NUMBER_ID: str = Field(default="")
    
    # Behavior Settings
    HUMAN_TAKEOVER_MINUTES: int = Field(default=120)
    MAX_HISTORY_PER_CONTACT: int = Field(default=10)
    
    # Server Settings
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")

settings = Settings()
