"""Utility functions for data loading and email personalization."""
import json
import random
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

try:
    from .models import EMAIL_TEMPLATES_FILE
except ImportError:
    from models import EMAIL_TEMPLATES_FILE


def load_json_list(file_path: Path, resource_name: str) -> list:
    """Load and validate list-based JSON resources (targets, templates, etc.)."""
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} file not found: {file_path}",
        )

    try:
        with open(file_path, "r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading {resource_name} file: {exc}",
        ) from exc

    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{resource_name} must be an array",
        )

    return data


def get_random_email_template() -> dict:
    """Get a random email template from available templates."""
    templates = load_json_list(EMAIL_TEMPLATES_FILE, "Email templates")
    
    if not templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No email templates available",
        )
    
    # Filter out templates with missing subject or body
    valid_templates = []
    for template in templates:
        subject = template.get("subject", "")
        body = template.get("body", "")
        if subject and body:
            valid_templates.append(template)
    
    if not valid_templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid email templates found (all templates missing subject or body)",
        )
    
    # Return a random template
    return random.choice(valid_templates)


def personalize_email_body(body: str, recipient_name: Optional[str], sender_name: str) -> str:
    """Personalize email body with recipient and sender names."""
    # Add greeting with recipient name
    if recipient_name and recipient_name.strip():
        greeting = f"Hi {recipient_name.strip()},"
    else:
        greeting = "Hi,"
    
    # Prepend greeting to the body
    personalized_body = f"{greeting} {body.lstrip()}"
    
    # Add sender name at the end (before "Best regards,")
    if sender_name and sender_name.strip():
        # Check if "Best regards," exists, if so, add name after it
        if "Best regards," in personalized_body:
            personalized_body = personalized_body.replace(
                "Best regards,",
                f"Best regards,\n\n{sender_name.strip()}"
            )
        else:
            # If no "Best regards," found, just append the name
            personalized_body += f"\n\n{sender_name.strip()}"
    
    return personalized_body

