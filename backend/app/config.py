import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    APP_NAME: str = "AI Job Application Agent"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    
    # Database
    DATABASE_URL: str = "sqlite:///./job_agent.db"
    
    # Security
    SECRET_KEY: str = "dev_secret_key_antigravity_agent_change_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALGORITHM: str = "HS256"
    
    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    
    # Uploads
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # Submission Guardrail
    ENABLE_LIVE_SUBMISSIONS: bool = False

    model_config = SettingsConfigDict(
        env_file=[str(ROOT_DIR / ".env"), str(BASE_DIR / ".env"), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
