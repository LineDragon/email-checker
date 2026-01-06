# Quick Start Guide

## Prerequisites

- Python 3.8+
- Node.js 16+
- Google Cloud account with Gmail API enabled

## Step 1: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Gmail API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: `http://localhost:8000/api/google/callback`
   - Copy the **Client ID** and **Client Secret**

## Step 2: Backend Setup

```bash
cd server
pip install -r requirements.txt
```

Create `.env` file:
```env
GOOGLE_AUTH_CLIENT_ID=your_client_id_here
GOOGLE_AUTH_CLIENT_SECRET=your_client_secret_here
GOOGLE_AUTH_REDIRECT_URI=http://localhost:8000/api/google/callback
EMAIL_DELAY_SECONDS=1.0
```

Update `email_targets.json` with your recipients:
```json
[
  {
    "target_email": "recipient1@example.com",
    "name": "Recipient 1"
  },
  {
    "target_email": "recipient2@example.com",
    "name": "Recipient 2"
  }
]
```

Start the server:
```bash
python main.py
```

Server runs on `http://localhost:8000`

## Step 3: Frontend Setup

```bash
cd client
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

## Step 4: Use the Application

1. Open `http://localhost:3000` in your browser
2. Click **"Connect with Google"**
3. Authorize the application in Google
4. Once connected, button changes to **"Apply with Google"**
5. (Optional) Customize email subject and body
6. Click **"Send Bulk Emails"**
7. Wait for the success message showing how many emails were sent

## Troubleshooting

### "Google account not connected"
- Make sure you completed the OAuth flow
- Check that `.env` file has correct credentials
- Verify redirect URI matches in Google Console

### "Email targets file not found"
- Make sure `email_targets.json` exists in the `server/` folder
- Check file format is valid JSON array

### Rate limiting errors
- Increase `EMAIL_DELAY_SECONDS` in `.env` (e.g., 2.0 or 3.0)
- Google has daily sending limits for new accounts

### CORS errors
- Make sure backend CORS allows `http://localhost:3000`
- Check that both servers are running

