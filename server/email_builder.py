"""Email message building utilities."""
import base64
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

try:
    from .models import RESUME_MIME_TYPE
except ImportError:
    from models import RESUME_MIME_TYPE


def build_resume_attachment_part(resume_bytes: bytes, resume_filename: str) -> MIMEBase:
    """Build a MIME attachment part for resume file."""
    part = MIMEBase("application", "octet-stream")
    part.set_payload(resume_bytes)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Type",
        f'{RESUME_MIME_TYPE}; name="{resume_filename}"',
    )
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=resume_filename,
    )
    return part


def build_gmail_message(
    to_email: str,
    subject: str,
    body: str,
    resume_bytes: Optional[bytes] = None,
    resume_filename: Optional[str] = None
) -> str:
    """Create a Gmail-compatible MIME message with optional resume attachment."""
    message = MIMEMultipart()
    message["to"] = to_email
    message["subject"] = subject

    body_part = MIMEText(body, "plain")
    message.attach(body_part)

    # Attach resume if provided
    if resume_bytes and resume_filename:
        attachment_part = build_resume_attachment_part(resume_bytes, resume_filename)
        message.attach(attachment_part)

    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

