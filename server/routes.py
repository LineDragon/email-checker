"""API routes and endpoints."""
import asyncio
import json
import random
import urllib.parse
from typing import Dict, Optional
from uuid import uuid4

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
        authorization_url = outlook_auth.get_authorization_url()
        return {"authorization_url": authorization_url}
    
    @app.get("/api/outlook/callback")
    async def outlook_callback(code: Optional[str] = None, error: Optional[str] = None):
        """Handle Outlook OAuth callback"""
        if error:
            error_msg = urllib.parse.quote(str(error))
            return RedirectResponse(
                url=f"http://localhost:3000?error={error_msg}"
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
        if outlook_auth.is_connected():
            return {"connected": True, "email": outlook_auth.email}
        return {"connected": False, "email": None}
    
    # Email templates route
    @app.get("/api/email/templates")
    async def get_email_templates():
        """Get list of available email templates"""
        templates = load_json_list(EMAIL_TEMPLATES_FILE, "Email templates")
        return {"templates": templates}
    
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

