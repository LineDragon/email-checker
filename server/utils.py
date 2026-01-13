"""Utility functions for data loading and email personalization."""
import json
import random
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status

try:
    from .models import EMAIL_TEMPLATES_FILE
    from .config import Settings
except ImportError:
    from models import EMAIL_TEMPLATES_FILE
    from config import Settings


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


def is_interview_request(email_content: str, api_key: Optional[str] = None) -> bool:
    """
    Identify if email content matches any of three important conditions using GPT API:
    1. Requesting an interview
    2. Planning next steps (contact/discuss after days, discuss next steps, etc.)
    3. Job offer or passing job testing
    
    Args:
        email_content: The content of the email (subject + body)
        api_key: GPT API key (optional, will use settings if not provided)
    
    Returns:
        True if email contains ANY of the three conditions above, False otherwise
    """
    # If no API key provided, try to get from settings
    if not api_key:
        try:
            settings = Settings()
            api_key = settings.GPT_API_KEY
        except Exception:
            pass
    
    # If still no API key, return False (can't check without API key)
    if not api_key:
        return False
    
    # Truncate email content if too long (GPT API has token limits)
    # Keep it reasonable - around 3000 characters should be enough
    content_to_analyze = email_content[:3000] if len(email_content) > 3000 else email_content
    
    try:
        from openai import OpenAI
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create prompt for GPT API - check three important conditions
        prompt = f"""Analyze the following email content and determine if it matches ANY of these three important conditions:

Email content:
{content_to_analyze}

CONDITION 1: Interview Request
- Contains ANY mention of interview (interview, interviewing, interview process, interview invitation, interview request, scheduling interview, phone interview, video interview, interview call, interview meeting)
- Examples: "We would like to schedule an interview", "Can you come in for an interview?", "Next step is an interview"

CONDITION 2: Planning Next Steps
- Mentions planning next steps, contacting after a few days, discussing next steps, follow-up discussion, next phase, moving forward, next stage
- Examples: "We will contact you in a few days", "Let's discuss the next steps", "We'll reach out next week to discuss", "Moving to the next phase", "Next steps in the process"

CONDITION 3: Job Offer or Passing Job Testing
- Contains job offer, offer letter, congratulations on passing, you passed the test, test results positive, selected for position
- Examples: "We would like to offer you the position", "Congratulations, you passed the interview/testing", "We are pleased to offer you", "You have been selected", "Job offer"

IMPORTANT INSTRUCTIONS:
- Return "true" if the email contains EVEN A LITTLE about ANY of the three conditions above
- Return "false" ONLY if the email contains NONE of these three conditions

Examples that should return TRUE:
- "We would like to schedule an interview"
- "We'll contact you next week to discuss next steps"
- "Congratulations, you passed the test. We'll discuss next steps soon."
- "Let's set up a call in a few days"
- "We're pleased to offer you the position"
- "You passed the interview. Next steps will follow."

Examples that should return FALSE:
- Simple application confirmation
- Rejection letter without any of the three conditions
- General inquiry about position
- Automated system notifications
- Email that contains none of the three conditions

Respond with ONLY "true" or "false" (lowercase, no quotes, no explanation).

Response:"""
        
        # Call GPT API using GPT-4 or higher version
        response = client.chat.completions.create(
            model="gpt-4o",  # Using GPT-4o (latest GPT-4 model) for better accuracy
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes emails to detect: 1) interview requests, 2) planning next steps (contacting/discussing after days), 3) job offers or passing job testing. Return 'true' if email contains ANY of these three conditions, even briefly. Respond only with 'true' or 'false'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for more deterministic results
            max_completion_tokens=10  # Only need true/false response (GPT-4o uses max_completion_tokens instead of max_tokens)
        )
        
        # Extract response
        result = response.choices[0].message.content.strip().lower()
        
        # Parse result - should be "true" or "false"
        if result == "true":
            return True
        elif result == "false":
            return False
        else:
            # If response is unexpected, default to False for safety
            return False
            
    except Exception as e:
        # If API call fails, return False (don't break the application)
        # In production, you might want to log this error
        print(f"Error checking interview request with GPT API: {str(e)}")
        return False

