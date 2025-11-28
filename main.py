"""
Unified FastAPI Application - Life Context API
Mounts all three APIs (GPS, Audio, Whisper) under one application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import individual API apps
from collectors.gps.main import app as gps_app
from collectors.audio.main import app as audio_app
from processors.whisper.main import app as whisper_app

# Create main application
app = FastAPI(
    title="Life Context API",
    description="Unified API for GPS tracking, audio upload, and transcription processing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all three APIs
app.mount("/gps", gps_app)
app.mount("/audio", audio_app)
app.mount("/whisper", whisper_app)

@app.get("/")
async def root():
    """Root endpoint - shows all available APIs"""
    return {
        "service": "Life Context API",
        "status": "running",
        "apis": {
            "gps": "/gps - GPS data collection and tracking",
            "audio": "/audio - Audio file upload and chunking", 
            "whisper": "/whisper - Audio transcription processing"
        },
        "docs": "/docs",
        "health_checks": {
            "gps": "/gps/",
            "audio": "/audio/",
            "whisper": "/whisper/"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Life Context API - All APIs"}
