#!/usr/bin/env python3
"""Simple test script for is_interview_request function.
Usage:
    python3 test_interview_request.py                    # Uses default test email
    python3 test_interview_request.py "email content"    # Uses provided email
    echo "email content" | python3 test_interview_request.py  # Reads from stdin
"""
import sys
from pathlib import Path

# Add server directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from utils import is_interview_request
except ImportError as e:
    print(f"Error importing is_interview_request: {e}", file=sys.stderr)
    sys.exit(1)


def main():
    """Test is_interview_request function with email input."""
    # Get email content from command line argument, stdin, or use default
    if len(sys.argv) > 1:
        # Email provided as command line argument
        email = sys.argv[1]
    elif not sys.stdin.isatty():
        # Email provided via stdin (pipe or redirect)
        email = sys.stdin.read().strip()
    else:
        # Default test email
        email = """
            Hi tyler,
            We received your application and would love to learn more about you and answer any questions you may have about Mosai or the Machine Learning Operations Engineer position.
            Could you send me a few times when you’d be available for a 30 minute virtual interview in the next few business days? You'll be meeting with the hiring manager via Microsoft Teams.
            We look forward to the conversation and getting to know you.
            Best,
            Elizabeth Watson
            Recruiter
            Mosai
        """
    
    # Format email content (subject + body)
    email_content = f"Subject: Interview Request\n\n{email}"
    
    # Test the function
    try:
        result = is_interview_request(email_content)
        print("true" if result else "false")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

