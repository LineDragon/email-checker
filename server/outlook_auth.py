"""Outlook OAuth and email sending functionality."""
import time
from typing import Any, Dict, Optional

import msal
import requests
from fastapi import HTTPException, status

try:
    from .config import Settings, OUTLOOK_SCOPES
except ImportError:
    from config import Settings, OUTLOOK_SCOPES


class OutlookAuthService:
    """Service for managing Outlook OAuth and email sending."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.app: Optional[msal.ConfidentialClientApplication] = None
        self.auth_state: Optional[Dict[str, Any]] = None
        self.email: Optional[str] = None
        
        if settings.OUTLOOK_CLIENT_ID and settings.OUTLOOK_CLIENT_SECRET:
            authority = f"https://login.microsoftonline.com/{settings.OUTLOOK_TENANT}"
            self.app = msal.ConfidentialClientApplication(
                client_id=settings.OUTLOOK_CLIENT_ID,
                authority=authority,
                client_credential=settings.OUTLOOK_CLIENT_SECRET,
            )
    
    def ensure_enabled(self):
        """Ensure Outlook integration is enabled."""
        if not self.app:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Outlook integration is not configured on the server.",
            )
    
    def get_authorization_url(self) -> str:
        """Get Outlook OAuth authorization URL."""
        self.ensure_enabled()
        return self.app.get_authorization_request_url(
            scopes=OUTLOOK_SCOPES,
            redirect_uri=self.settings.OUTLOOK_REDIRECT_URI,
            prompt="consent",
        )
    
    def handle_callback(self, code: str) -> str:
        """Handle OAuth callback and return user email."""
        self.ensure_enabled()
        
        result = self.app.acquire_token_by_authorization_code(
            code=code,
            scopes=OUTLOOK_SCOPES,
            redirect_uri=self.settings.OUTLOOK_REDIRECT_URI,
        )
        
        if "access_token" not in result:
            error_msg = result.get("error_description", "Failed to acquire Outlook token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        access_token = result["access_token"]
        email = self._fetch_email(access_token)
        self._update_auth_state(result, email)
        
        return email
    
    def _fetch_email(self, access_token: str) -> str:
        """Retrieve the primary email address for the connected Outlook user."""
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fetch Outlook profile: {response.text}",
            )
        
        profile = response.json()
        return profile.get("mail") or profile.get("userPrincipalName") or ""
    
    def _update_auth_state(self, token_result: Dict[str, Any], email: str):
        """Persist Outlook auth tokens in memory."""
        expires_in = int(token_result.get("expires_in", 0))
        self.auth_state = {
            "access_token": token_result["access_token"],
            "refresh_token": token_result.get("refresh_token"),
            "expires_at": time.time() + expires_in - 30,  # refresh 30s before expiry
        }
        self.email = email
    
    def get_access_token(self) -> str:
        """Return a valid Outlook access token, refreshing when possible."""
        self.ensure_enabled()
        
        if not self.auth_state:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Outlook account not connected. Please connect first.",
            )
        
        if self.auth_state["expires_at"] <= time.time():
            refresh_token = self.auth_state.get("refresh_token")
            if not refresh_token:
                self.auth_state = None
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Outlook session expired. Please reconnect.",
                )
            
            refresh_result = self.app.acquire_token_by_refresh_token(
                refresh_token, scopes=OUTLOOK_SCOPES
            )
            if "access_token" not in refresh_result:
                self.auth_state = None
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Outlook session expired. Please reconnect.",
                )
            
            expires_in = int(refresh_result.get("expires_in", 0))
            self.auth_state["access_token"] = refresh_result["access_token"]
            self.auth_state["refresh_token"] = refresh_result.get(
                "refresh_token", refresh_token
            )
            self.auth_state["expires_at"] = time.time() + expires_in - 30
        
        return self.auth_state["access_token"]
    
    def is_connected(self) -> bool:
        """Check if Outlook account is connected."""
        if not self.app or not self.auth_state:
            return False
        
        try:
            self.get_access_token()
            return True
        except HTTPException:
            return False
    
    def send_email(self, access_token: str, to_email: str, subject: str, body: str):
        """Send an email via Microsoft Graph."""
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            },
            "saveToSentItems": True,
        }
        response = requests.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        if response.status_code >= 400:
            raise RuntimeError(response.text)

