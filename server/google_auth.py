"""Google OAuth and email sending functionality."""
from typing import Optional

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

try:
    from .config import Settings, GOOGLE_SCOPES
except ImportError:
    from config import Settings, GOOGLE_SCOPES


class GoogleAuthService:
    """Service for managing Google OAuth and email sending."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": settings.GOOGLE_AUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_AUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://accounts.google.com/o/oauth2/token",
                    "redirect_uris": [settings.GOOGLE_AUTH_REDIRECT_URI],
                }
            },
            scopes=GOOGLE_SCOPES,
        )
        self.flow.redirect_uri = settings.GOOGLE_AUTH_REDIRECT_URI
        self.credentials: Optional[Credentials] = None
        self.user_email: Optional[str] = None
    
    def get_authorization_url(self):
        """Get Google OAuth authorization URL."""
        authorization_url, state = self.flow.authorization_url(
            access_type="offline",
            prompt="consent"
        )
        return {"authorization_url": authorization_url, "state": state}
    
    def handle_callback(self, code: str) -> str:
        """Handle OAuth callback and return user email."""
        self.flow.fetch_token(code=code)
        credentials = self.flow.credentials
        
        # Get user email from ID token
        from google.oauth2 import id_token
        request_adapter = GoogleRequest()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token, request_adapter
        )
        user_email = id_info.get("email", "")
        
        self.credentials = credentials
        self.user_email = user_email
        
        return user_email
    
    def is_connected(self) -> bool:
        """Check if Google account is connected and valid."""
        if not self.credentials:
            return False
        
        # Check if credentials are still valid
        if self.credentials.expired and self.credentials.refresh_token:
            try:
                self.credentials.refresh(GoogleRequest())
            except Exception:
                self.credentials = None
                self.user_email = None
                return False
        
        return self.credentials.valid
    
    def ensure_connected(self):
        """Ensure Google account is connected, refresh if needed."""
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                try:
                    self.credentials.refresh(GoogleRequest())
                except Exception:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Google credentials expired. Please reconnect."
                    )
            else:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Google account not connected. Please connect first."
                )
    
    def get_gmail_service(self):
        """Get Gmail API service instance."""
        self.ensure_connected()
        return build("gmail", "v1", credentials=self.credentials)

