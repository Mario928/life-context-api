"""
Unified FastAPI Application - Life Context API
Mounts all three APIs (GPS, Audio, Whisper) under one application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import individual API apps
from collectors.gps.main import app as gps_app
from collectors.audio.main import app as audio_app

# Try to import Whisper API (may not be available if dependencies not installed)
whisper_available = False
try:
    from processors.whisper.main import app as whisper_app
    whisper_available = True
except ImportError as e:
    print(f"Warning: Whisper API not available - {e}")
    print("This is expected on standard App Service. Whisper requires GPU VM or Docker deployment.")

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

# Mount GPS and Audio APIs (always available)
app.mount("/gps", gps_app)
app.mount("/audio", audio_app)

# Mount Whisper API only if dependencies are available
if whisper_available:
    app.mount("/whisper", whisper_app)

@app.get("/")
async def root():
    """Root endpoint - shows all available APIs"""
    apis = {
        "gps": "/gps - GPS data collection and tracking",
        "audio": "/audio - Audio file upload and chunking"
    }
    
    if whisper_available:
        apis["whisper"] = "/whisper - Audio transcription processing"
    else:
        apis["whisper_note"] = "Whisper API requires GPU VM deployment (not available on standard App Service)"
    
    return {
        "service": "Life Context API",
        "status": "running",
        "apis": apis,
        "docs": "/docs",
        "health_checks": {
            "gps": "/gps/",
            "audio": "/audio/",
            "whisper": "/whisper/" if whisper_available else None
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "Life Context API",
        "available_apis": ["GPS", "Audio"] + (["Whisper"] if whisper_available else [])
    }
