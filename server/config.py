"""Configuration and settings for the application."""
from typing import Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    GOOGLE_AUTH_CLIENT_ID: str
    GOOGLE_AUTH_CLIENT_SECRET: str
    GOOGLE_AUTH_REDIRECT_URI: str = "http://localhost:8000/api/google/callback"
    EMAIL_DELAY_SECONDS: float = 1.0
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    OUTLOOK_REDIRECT_URI: str = "http://localhost:8000/api/outlook/callback"
    OUTLOOK_TENANT: str = "common"
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )


# OAuth scopes
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email"
]

OUTLOOK_SCOPES = ["User.Read", "Mail.Send"]

# CORS origins
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]

