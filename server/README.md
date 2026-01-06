# Bulk Email Sender - Server

FastAPI backend for sending bulk emails via Google Gmail API.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```env
GOOGLE_AUTH_CLIENT_ID=your_google_client_id_here
GOOGLE_AUTH_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_AUTH_REDIRECT_URI=http://localhost:8000/api/google/callback
EMAIL_DELAY_SECONDS=1.0
```

3. Get Google OAuth credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Add `http://localhost:8000/api/google/callback` to authorized redirect URIs
   - Copy Client ID and Client Secret to `.env`

4. Create `email_targets.json` file (example provided):
```json
[
  {
    "target_email": "example1@example.com",
    "name": "Example Company 1"
  },
  {
    "target_email": "example2@example.com",
    "name": "Example Company 2"
  }
]
```

5. Run the server:
```bash
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /api/google/auth` - Initiate Google OAuth flow
- `GET /api/google/callback` - OAuth callback handler
- `GET /api/google/status` - Check Google connection status
- `POST /api/google/send-bulk-emails` - Send bulk emails from JSON file

