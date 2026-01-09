"""API routes and endpoints."""
import asyncio
import base64
import html
import json
import random
import re
import urllib.parse
from typing import Dict, Optional
from uuid import uuid4

import requests

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse, StreamingResponse

try:
    from .config import Settings
    from .email_builder import build_gmail_message
    from .google_auth import GoogleAuthService
    from .models import EMAIL_TARGETS_FILE, EMAIL_TEMPLATES_FILE
    from .outlook_auth import OutlookAuthService
    from .utils import (
        get_random_email_template,
        load_json_list,
        personalize_email_body,
    )
except ImportError:
    from config import Settings
    from email_builder import build_gmail_message
    from google_auth import GoogleAuthService
    from models import EMAIL_TARGETS_FILE, EMAIL_TEMPLATES_FILE
    from outlook_auth import OutlookAuthService
    from utils import (
        get_random_email_template,
        load_json_list,
        personalize_email_body,
    )

router = APIRouter()

# In-memory storage for email sending status
# Format: {job_id: {"status": "pending|sending|completed|failed", "targets": [{email, status, error}]}}
email_status: Dict[str, Dict] = {}


def setup_routes(
    app,
    google_auth: GoogleAuthService,
    outlook_auth: OutlookAuthService,
    settings: Settings,
):
    """Setup all API routes."""
    
    @app.get("/")
    async def root():
        return {"message": "Bulk Email Sender API"}
    
    # Google OAuth routes
    @app.get("/api/google/auth")
    async def google_auth_endpoint():
        """Initiate Google OAuth flow"""
        return google_auth.get_authorization_url()
    
    @app.get("/api/google/callback")
    async def google_callback(code: Optional[str] = None, error: Optional[str] = None):
        """Handle Google OAuth callback"""
        if error:
            return RedirectResponse(
                url=f"http://localhost:3000?error={error}"
            )
        
        if not code:
            return RedirectResponse(
                url="http://localhost:3000?error=No authorization code provided"
            )
        
        try:
            user_email = google_auth.handle_callback(code)
            return RedirectResponse(
                url=f"http://localhost:3000?google_connected=true&email={user_email}"
            )
        except Exception as e:
            error_msg = urllib.parse.quote(str(e))
            return RedirectResponse(
                url=f"http://localhost:3000?error={error_msg}"
            )
    
    @app.get("/api/google/status")
    async def google_status():
        """Check if Google account is connected"""
        if google_auth.is_connected():
            return {"connected": True, "email": google_auth.user_email}
        return {"connected": False, "email": None}
    
    # Outlook OAuth routes
    @app.get("/api/outlook/auth")
    async def outlook_auth_endpoint():
        """Initiate Outlook OAuth flow"""
        try:
            authorization_url = outlook_auth.get_authorization_url()
            return {"authorization_url": authorization_url}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate authorization URL: {str(e)}. Check your Outlook configuration in .env file."
            )
    
    @app.get("/api/outlook/callback")
    async def outlook_callback(
        code: Optional[str] = None, 
        error: Optional[str] = None, 
        error_description: Optional[str] = None,
        error_uri: Optional[str] = None
    ):
        """Handle Outlook OAuth callback"""
        if error:
            # Include error description if available for better debugging
            if error_description:
                error_msg = f"{error}: {error_description}"
            else:
                error_msg = str(error)
            
            # Provide helpful messages for common errors
            if error == "invalid_request":
                detailed_msg = f"Invalid request error from Microsoft. "
                if error_description:
                    detailed_msg += f"Details: {error_description}. "
                detailed_msg += "Common causes: 1) Redirect URI in Azure must match 'http://localhost:8000/api/outlook/callback' EXACTLY (check for trailing slashes, case sensitivity), 2) Redirect URI must be added under 'Web' platform in Azure Authentication settings, 3) Client ID and Secret must be correct, 4) App registration must be active"
                error_msg = detailed_msg
            elif error == "unauthorized_client":
                error_msg = f"Unauthorized client. Check that your Client ID ({settings.OUTLOOK_CLIENT_ID[:8]}...) is correct and the app is properly configured in Azure. Error details: {error_description or 'None provided'}"
            elif error == "access_denied":
                error_msg = "Access denied. You cancelled the authorization or didn't grant permissions"
            else:
                # For any other error, include the description
                if error_description:
                    error_msg = f"{error}: {error_description}"
            
            error_msg_encoded = urllib.parse.quote(error_msg)
            return RedirectResponse(
                url=f"http://localhost:3000?error={error_msg_encoded}"
            )
        
        if not code:
            return RedirectResponse(
                url="http://localhost:3000?error=No authorization code provided"
            )
        
        try:
            email = outlook_auth.handle_callback(code)
            return RedirectResponse(
                url=f"http://localhost:3000?outlook_connected=true&email={email}"
            )
        except HTTPException as exc:
            error_msg = urllib.parse.quote(str(exc.detail))
            return RedirectResponse(url=f"http://localhost:3000?error={error_msg}")
    
    @app.get("/api/outlook/status")
    async def outlook_status():
        """Check if Outlook account is connected"""
        try:
            if outlook_auth.is_connected():
                return {"connected": True, "email": outlook_auth.email}
        except Exception:
            pass
        return {"connected": False, "email": None}
    
    @app.get("/api/outlook/debug")
    async def outlook_debug():
        """Debug endpoint to check Outlook configuration"""
        config_status = {
            "client_id_set": bool(settings.OUTLOOK_CLIENT_ID),
            "client_secret_set": bool(settings.OUTLOOK_CLIENT_SECRET),
            "redirect_uri": settings.OUTLOOK_REDIRECT_URI,
            "tenant": settings.OUTLOOK_TENANT,
            "app_initialized": outlook_auth.app is not None,
        }
        if settings.OUTLOOK_CLIENT_ID:
            config_status["client_id_preview"] = f"{settings.OUTLOOK_CLIENT_ID[:8]}...{settings.OUTLOOK_CLIENT_ID[-4:]}"
        
        # Try to generate authorization URL to see if there are any issues
        try:
            auth_url = outlook_auth.get_authorization_url()
            config_status["authorization_url_generated"] = True
            config_status["authorization_url_preview"] = auth_url[:100] + "..." if len(auth_url) > 100 else auth_url
            # Extract redirect_uri from the URL to verify it matches
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(auth_url)
            params = parse_qs(parsed.query)
            if 'redirect_uri' in params:
                config_status["redirect_uri_in_url"] = params['redirect_uri'][0]
        except Exception as e:
            config_status["authorization_url_generated"] = False
            config_status["error"] = str(e)
        
        return config_status
    
    @app.get("/api/outlook/test-auth-url")
    async def test_outlook_auth_url():
        """Test endpoint to see the generated authorization URL"""
        try:
            auth_url = outlook_auth.get_authorization_url()
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(auth_url)
            params = parse_qs(parsed.query)
            
            return {
                "authorization_url": auth_url,
                "redirect_uri_in_url": params.get('redirect_uri', ['Not found'])[0],
                "expected_redirect_uri": settings.OUTLOOK_REDIRECT_URI,
                "match": params.get('redirect_uri', [''])[0] == settings.OUTLOOK_REDIRECT_URI,
                "client_id_in_url": params.get('client_id', ['Not found'])[0],
                "scopes": params.get('scope', ['Not found'])[0].split() if params.get('scope') else []
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Email templates route
    @app.get("/api/email/templates")
    async def get_email_templates():
        """Get list of available email templates"""
        templates = load_json_list(EMAIL_TEMPLATES_FILE, "Email templates")
        return {"templates": templates}
    
    # Email targets route with pagination and search
    @app.get("/api/email/targets")
    async def get_email_targets(
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ):
        """Get email targets with pagination and search"""
        all_targets = load_json_list(EMAIL_TARGETS_FILE, "Email targets")
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            filtered_targets = [
                target for target in all_targets
                if search_lower in target.get("target_email", "").lower()
                or search_lower in target.get("name", "").lower()
            ]
        else:
            filtered_targets = all_targets
        
        # Calculate pagination
        total = len(filtered_targets)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_targets = filtered_targets[start_idx:end_idx]
        
        return {
            "targets": paginated_targets,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    
    @app.get("/api/email/targets/stats")
    async def get_email_targets_stats():
        """Get statistics about email targets"""
        all_targets = load_json_list(EMAIL_TARGETS_FILE, "Email targets")
        return {
            "total": len(all_targets),
            "has_index": sum(1 for t in all_targets if "index" in t),
            "has_name": sum(1 for t in all_targets if t.get("name")),
            "has_email": sum(1 for t in all_targets if t.get("target_email"))
        }
    
    # Inbox email reading routes
    @app.get("/api/google/inbox")
    async def get_google_inbox(
        max_results: int = 50,
        page_token: Optional[str] = None
    ):
        """Get emails from Gmail inbox"""
        google_auth.ensure_connected()
        service = google_auth.get_gmail_service()
        
        try:
            # List messages
            query_params = {
                "userId": "me",
                "labelIds": ["INBOX"],
                "maxResults": min(max_results, 100),
            }
            if page_token:
                query_params["pageToken"] = page_token
            
            messages_response = service.users().messages().list(**query_params).execute()
            messages = messages_response.get("messages", [])
            next_page_token = messages_response.get("nextPageToken")
            
            # Get full message details
            email_list = []
            for msg in messages:
                try:
                    message = service.users().messages().get(
                        userId="me",
                        id=msg["id"],
                        format="full"
                    ).execute()
                    
                    # Extract headers
                    headers = message["payload"].get("headers", [])
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    date = next((h["value"] for h in headers if h["name"] == "Date"), "")
                    
                    # Extract body - prefer text/plain, fallback to text/html
                    body = ""
                    html_body = ""
                    payload = message["payload"]
                    
                    def extract_text_from_part(part):
                        """Extract text from a message part."""
                        if part.get("mimeType") == "text/plain":
                            data = part.get("body", {}).get("data", "")
                            if data:
                                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        elif part.get("mimeType") == "text/html":
                            data = part.get("body", {}).get("data", "")
                            if data:
                                return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        return None
                    
                    if "parts" in payload:
                        # Look for text/plain first
                        for part in payload["parts"]:
                            text = extract_text_from_part(part)
                            if text:
                                if part.get("mimeType") == "text/plain":
                                    body = text
                                    break
                                elif part.get("mimeType") == "text/html" and not html_body:
                                    html_body = text
                        # If no plain text found, use HTML and strip tags
                        if not body and html_body:
                            # Remove HTML tags
                            body = re.sub(r'<[^>]+>', '', html_body)
                            # Decode HTML entities
                            body = html.unescape(body)
                            # Clean up extra whitespace
                            body = re.sub(r'\n\s*\n', '\n\n', body).strip()
                    else:
                        if payload.get("mimeType") == "text/plain":
                            data = payload["body"].get("data", "")
                            if data:
                                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        elif payload.get("mimeType") == "text/html":
                            data = payload["body"].get("data", "")
                            if data:
                                html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                                # Strip HTML tags
                                body = re.sub(r'<[^>]+>', '', html_body)
                                body = html.unescape(body)
                                body = re.sub(r'\n\s*\n', '\n\n', body).strip()
                    
                    email_list.append({
                        "id": msg["id"],
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "snippet": message.get("snippet", ""),
                        "body": body[:500] if body else message.get("snippet", ""),  # Limit body preview
                        "full_body": body
                    })
                except Exception as e:
                    continue
            
            return {
                "emails": email_list,
                "next_page_token": next_page_token,
                "total": len(email_list)
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Gmail inbox: {str(e)}"
            )
    
    @app.get("/api/outlook/inbox")
    async def get_outlook_inbox(
        max_results: int = 50,
        skip: int = 0
    ):
        """Get emails from Outlook inbox"""
        outlook_auth.ensure_enabled()
        if not outlook_auth.is_connected():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Outlook account not connected. Please connect first."
            )
        
        access_token = outlook_auth.get_access_token()
        
        try:
            # Get messages from Outlook inbox
            url = f"https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            params = {
                "$top": min(max_results, 100),
                "$skip": skip,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,receivedDateTime,bodyPreview,body"
            }
            
            response = requests.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=10
            )
            
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to fetch Outlook inbox: {response.text}"
                )
            
            data = response.json()
            emails = data.get("value", [])
            
            email_list = []
            for msg in emails:
                from_info = msg.get("from", {})
                body = msg.get("body", {})
                body_content = body.get("content", "") if isinstance(body, dict) else ""
                
                # Strip HTML tags if content is HTML
                if body_content:
                    # Check if it's HTML
                    if "<" in body_content and ">" in body_content:
                        # Remove HTML tags
                        body_content = re.sub(r'<[^>]+>', '', body_content)
                        # Decode HTML entities
                        body_content = html.unescape(body_content)
                        # Clean up extra whitespace
                        body_content = re.sub(r'\n\s*\n', '\n\n', body_content).strip()
                
                email_list.append({
                    "id": msg.get("id"),
                    "subject": msg.get("subject", "No Subject"),
                    "from": from_info.get("emailAddress", {}).get("address", "Unknown") if isinstance(from_info, dict) else "Unknown",
                    "date": msg.get("receivedDateTime", ""),
                    "snippet": msg.get("bodyPreview", ""),
                    "body": body_content[:500] if body_content else msg.get("bodyPreview", ""),
                    "full_body": body_content
                })
            
            return {
                "emails": email_list,
                "total": len(email_list),
                "has_more": "@odata.nextLink" in data
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch Outlook inbox: {str(e)}"
            )
    
    # SSE endpoint for real-time status updates
    @app.get("/api/email/status/{job_id}")
    async def stream_email_status(job_id: str):
        """Stream email sending status via Server-Sent Events"""
        async def event_generator():
            last_sent = 0
            while True:
                if job_id not in email_status:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                    break
                
                job_data = email_status[job_id]
                targets = job_data.get("targets", [])
                
                # Only send updates for new items
                if len(targets) > last_sent:
                    update = {
                        "status": job_data.get("status", "pending"),
                        "targets": targets[last_sent:],
                        "total": job_data.get("total", 0),
                        "sent": job_data.get("sent", 0),
                        "failed": job_data.get("failed", 0)
                    }
                    yield f"data: {json.dumps(update)}\n\n"
                    last_sent = len(targets)
                
                # If job is completed, send final update and close
                if job_data.get("status") in ["completed", "failed"]:
                    final_update = {
                        "status": job_data.get("status"),
                        "targets": targets,
                        "total": job_data.get("total", 0),
                        "sent": job_data.get("sent", 0),
                        "failed": job_data.get("failed", 0),
                        "errors": job_data.get("errors")
                    }
                    yield f"data: {json.dumps(final_update)}\n\n"
                    break
                
                await asyncio.sleep(0.5)  # Poll every 500ms
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    # Background task for sending Gmail emails
    async def send_gmail_emails_task(
        job_id: str,
        email_targets: list,
        sender_name: str,
        resume_bytes: Optional[bytes],
        resume_filename: Optional[str]
    ):
        """Background task to send Gmail emails and update status"""
        try:
            email_status[job_id]["status"] = "sending"
            service = google_auth.get_gmail_service()
            sent_count = 0
            failed_count = 0
            errors = []
            
            for i, target in enumerate(email_targets):
                target_email = target.get("target_email") or target.get("email")
                recipient_name = target.get("name", "").strip()
                
                if not target_email:
                    failed_count += 1
                    error_msg = "Missing target_email"
                    errors.append(f"Item {i+1}: {error_msg}")
                    email_status[job_id]["targets"].append({
                        "email": target_email or f"Item {i+1}",
                        "status": "failed",
                        "error": error_msg
                    })
                    email_status[job_id]["failed"] = failed_count
                    continue
                
                try:
                    # Select a random template for this email
                    template = get_random_email_template()
                    subject = template["subject"]
                    base_body = template["body"]
                    
                    # Personalize email body for this recipient
                    personalized_body = personalize_email_body(base_body, recipient_name, sender_name)
                    
                    # Create email message with optional attachment
                    raw_message = build_gmail_message(
                        target_email, subject, personalized_body, resume_bytes, resume_filename
                    )
                    
                    # Send email
                    service.users().messages().send(
                        userId="me",
                        body={"raw": raw_message}
                    ).execute()
                    
                    sent_count += 1
                    email_status[job_id]["targets"].append({
                        "email": target_email,
                        "status": "sent",
                        "error": None
                    })
                    email_status[job_id]["sent"] = sent_count
                    
                    # Random delay between emails (except for the last one)
                    if i < len(email_targets) - 1:
                        min_delay = 0.8 * settings.EMAIL_DELAY_SECONDS
                        max_delay = 1.2 * settings.EMAIL_DELAY_SECONDS
                        random_delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(random_delay)
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    errors.append(f"Item {i+1} ({target_email}): {error_msg}")
                    email_status[job_id]["targets"].append({
                        "email": target_email,
                        "status": "failed",
                        "error": error_msg
                    })
                    email_status[job_id]["failed"] = failed_count
            
            email_status[job_id]["status"] = "completed"
            email_status[job_id]["errors"] = errors if errors else None
        except Exception as e:
            email_status[job_id]["status"] = "failed"
            email_status[job_id]["errors"] = [str(e)]
    
    # Background task for sending Outlook emails
    async def send_outlook_emails_task(
        job_id: str,
        email_targets: list,
        sender_name: str
    ):
        """Background task to send Outlook emails and update status"""
        try:
            email_status[job_id]["status"] = "sending"
            outlook_auth.ensure_enabled()
            access_token = outlook_auth.get_access_token()
            sent_count = 0
            failed_count = 0
            errors = []
            
            for i, target in enumerate(email_targets):
                target_email = target.get("target_email") or target.get("email")
                recipient_name = target.get("name", "").strip()
                
                if not target_email:
                    failed_count += 1
                    error_msg = "Missing target_email"
                    errors.append(f"Item {i+1}: {error_msg}")
                    email_status[job_id]["targets"].append({
                        "email": target_email or f"Item {i+1}",
                        "status": "failed",
                        "error": error_msg
                    })
                    email_status[job_id]["failed"] = failed_count
                    continue
                
                try:
                    # Select a random template for this email
                    template = get_random_email_template()
                    subject = template["subject"]
                    base_body = template["body"]
                    
                    # Personalize email body for this recipient
                    personalized_body = personalize_email_body(base_body, recipient_name, sender_name)
                    outlook_auth.send_email(access_token, target_email, subject, personalized_body)
                    sent_count += 1
                    email_status[job_id]["targets"].append({
                        "email": target_email,
                        "status": "sent",
                        "error": None
                    })
                    email_status[job_id]["sent"] = sent_count
                    
                    # Random delay between emails (except for the last one)
                    if i < len(email_targets) - 1:
                        min_delay = 0.8 * settings.EMAIL_DELAY_SECONDS
                        max_delay = 1.2 * settings.EMAIL_DELAY_SECONDS
                        random_delay = random.uniform(min_delay, max_delay)
                        await asyncio.sleep(random_delay)
                except Exception as exc:
                    failed_count += 1
                    error_msg = str(exc)
                    errors.append(f"Item {i+1} ({target_email}): {error_msg}")
                    email_status[job_id]["targets"].append({
                        "email": target_email,
                        "status": "failed",
                        "error": error_msg
                    })
                    email_status[job_id]["failed"] = failed_count
            
            email_status[job_id]["status"] = "completed"
            email_status[job_id]["errors"] = errors if errors else None
        except Exception as e:
            email_status[job_id]["status"] = "failed"
            email_status[job_id]["errors"] = [str(e)]
    
    # Send bulk emails routes
    @app.post("/api/google/send-bulk-emails")
    async def send_bulk_emails(
        background_tasks: BackgroundTasks,
        sender_name: str = Form(...),
        first_index: Optional[int] = Form(None),
        last_index: Optional[int] = Form(None),
        resume: Optional[UploadFile] = File(None)
    ):
        """Send bulk emails from JSON file with random template selection"""
        google_auth.ensure_connected()
        
        # Read email targets from JSON file
        all_targets = load_json_list(EMAIL_TARGETS_FILE, "Email targets")
        
        # Filter by index range if provided
        if first_index is not None or last_index is not None:
            email_targets = []
            for target in all_targets:
                target_index = target.get("index")
                if target_index is None:
                    continue
                
                # Check if index is within range
                if first_index is not None and target_index < first_index:
                    continue
                if last_index is not None and target_index > last_index:
                    continue
                
                email_targets.append(target)
            
            if not email_targets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No email targets found in index range {first_index or 'start'} to {last_index or 'end'}"
                )
        else:
            email_targets = all_targets
        
        # Read resume file if provided
        resume_bytes = None
        resume_filename = None
        if resume:
            resume_bytes = await resume.read()
            resume_filename = resume.filename
        
        # Create job ID and initialize status
        job_id = str(uuid4())
        email_status[job_id] = {
            "status": "pending",
            "targets": [],
            "total": len(email_targets),
            "sent": 0,
            "failed": 0,
            "errors": None
        }
        
        # Start background task
        background_tasks.add_task(
            send_gmail_emails_task,
            job_id,
            email_targets,
            sender_name,
            resume_bytes,
            resume_filename
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "total": len(email_targets)
        }
    
    @app.post("/api/outlook/send-bulk-emails")
    async def send_outlook_bulk_emails(
        background_tasks: BackgroundTasks,
        sender_name: str = Form(...),
        first_index: Optional[int] = Form(None),
        last_index: Optional[int] = Form(None),
        resume: Optional[UploadFile] = File(None)
    ):
        """Send bulk emails through Outlook using Microsoft Graph with random template selection"""
        outlook_auth.ensure_enabled()
        if not outlook_auth.is_connected():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Outlook account not connected. Please connect first."
            )
        
        # Read email targets from JSON file
        all_targets = load_json_list(EMAIL_TARGETS_FILE, "Email targets")
        
        # Filter by index range if provided
        if first_index is not None or last_index is not None:
            email_targets = []
            for target in all_targets:
                target_index = target.get("index")
                if target_index is None:
                    continue
                
                # Check if index is within range
                if first_index is not None and target_index < first_index:
                    continue
                if last_index is not None and target_index > last_index:
                    continue
                
                email_targets.append(target)
            
            if not email_targets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No email targets found in index range {first_index or 'start'} to {last_index or 'end'}"
                )
        else:
            email_targets = all_targets
        
        # Note: Outlook endpoint ignores resume file (not implemented for Outlook)
        
        # Create job ID and initialize status
        job_id = str(uuid4())
        email_status[job_id] = {
            "status": "pending",
            "targets": [],
            "total": len(email_targets),
            "sent": 0,
            "failed": 0,
            "errors": None
        }
        
        # Start background task
        background_tasks.add_task(
            send_outlook_emails_task,
            job_id,
            email_targets,
            sender_name
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "total": len(email_targets)
        }

