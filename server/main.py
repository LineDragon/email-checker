"""Main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from .config import CORS_ORIGINS, Settings
    from .google_auth import GoogleAuthService
    from .outlook_auth import OutlookAuthService
    from .routes import setup_routes
except ImportError:
    # Allow running as script
    from config import CORS_ORIGINS, Settings
    from google_auth import GoogleAuthService
    from outlook_auth import OutlookAuthService
    from routes import setup_routes

# Initialize settings
settings = Settings()

# Initialize auth services
google_auth = GoogleAuthService(settings)
outlook_auth = OutlookAuthService(settings)

# Create FastAPI app
app = FastAPI(title="Bulk Email Sender")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup routes
setup_routes(app, google_auth, outlook_auth, settings)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
