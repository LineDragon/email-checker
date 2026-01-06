"""Data models and file paths."""
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# JSON file paths
EMAIL_TARGETS_FILE = BASE_DIR / "email_targets.json"
EMAIL_TEMPLATES_FILE = BASE_DIR / "email_templates.json"

# Resume MIME type
RESUME_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

