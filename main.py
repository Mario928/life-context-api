"""
Unified FastAPI Application - Life Context API
Mounts all three APIs (GPS, Audio, Whisper) under one application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import individual API apps
from collectors.gps.main import app as gps_app
from collectors.audio.main import app as audio_app

# Try to import Whisper, but allow failure if dependencies (FFmpeg) are missing
try:
    from processors.whisper.main import app as whisper_app
    whisper_available = True
except ImportError:
    whisper_app = None
    whisper_available = False

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
# Mount all three APIs
app.mount("/gps", gps_app)
app.mount("/audio", audio_app)
if whisper_available:
    app.mount("/whisper", whisper_app)

@app.get("/")
async def root():
    """Root endpoint - shows all available APIs"""
    apis = {
        "gps": "/gps - GPS data collection and tracking",
        "audio": "/audio - Audio file upload and chunking"
    }
    
    health_checks = {
        "gps": "/gps/",
        "audio": "/audio/"
    }

    if whisper_available:
        apis["whisper"] = "/whisper - Audio transcription processing"
        health_checks["whisper"] = "/whisper/"
    else:
        apis["whisper"] = "Unavailable (FFmpeg/Dependencies missing)"

    return {
        "service": "Life Context API",
        "status": "running",
        "deployment": "Standard Python (GPS+Audio only)" if not whisper_available else "Docker container with FFmpeg",
        "apis": apis,
        "docs": "/docs",
        "health_checks": health_checks
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "Life Context API",
        "available_apis": ["GPS", "Audio", "Whisper"]
    }
