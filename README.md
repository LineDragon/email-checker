# Bulk Email Sender

A simple application to send bulk emails via Google Gmail API with OAuth authentication.

## Features

- 🔐 Google OAuth authentication
- 📧 Bulk email sending from JSON file
- ⏱️ Configurable delay between emails (prevents rate limiting)
- 🎨 Modern, responsive UI
- 📊 Email sending status and count

## Project Structure

```
bulk-email-sender/
├── client/          # React frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── server/          # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   ├── email_targets.json
│   └── .env (create this)
└── README.md
```

## Quick Start

### Backend Setup

1. Navigate to server directory:
```bash
cd server
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file with your Google OAuth credentials:
```env
GOOGLE_AUTH_CLIENT_ID=your_client_id
GOOGLE_AUTH_CLIENT_SECRET=your_client_secret
GOOGLE_AUTH_REDIRECT_URI=http://localhost:8000/api/google/callback
EMAIL_DELAY_SECONDS=1.0
```

4. Update `email_targets.json` with your target emails:
```json
[
  {
    "target_email": "recipient1@example.com",
    "name": "Recipient 1"
  }
]
```

5. Run the server:
```bash
python main.py
```

### Frontend Setup

1. Navigate to client directory:
```bash
cd client
```

2. Install dependencies:
```bash
npm install
```

3. Run development server:
```bash
npm run dev
```

4. Open `http://localhost:3000` in your browser

## How to Use

1. Click "Connect with Google" button
2. Authorize the application in Google OAuth flow
3. Once connected, the button changes to "Apply with Google"
4. (Optional) Customize email subject and body
5. Click "Send Bulk Emails" to send emails to all recipients in `email_targets.json`
6. View the count of sent emails in the success message

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Gmail API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure OAuth consent screen
6. Add authorized redirect URI: `http://localhost:8000/api/google/callback`
7. Copy Client ID and Client Secret to your `.env` file

## Notes

- Emails are sent with a 1-second delay between each to prevent rate limiting
- The delay can be configured in `.env` file (`EMAIL_DELAY_SECONDS`)
- Outlook integration is planned for future release
- Make sure your Google account has permission to send emails

## License

MIT

