# Audio Upload API

Receives WAV audio files, chunks them using 5-minute segments with 30-second overlap, and stores to Azure Blob Storage.

Uses chunking algorithm from friend's Whisper notebook.

---

## 🎯 What It Does

- Accepts WAV file uploads (up to 500MB)
- Chunks audio into 5-min segments with 30s overlap
- Uploads chunks to Azure Blob Storage
- Stores metadata in PostgreSQL
- Returns upload_id for later transcription

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Azure Blob Storage account
- ffmpeg installed (`apt-get install ffmpeg` or `brew install ffmpeg`)

### Environment Variables

```bash
export DATABASE_URL="postgresql://dbadmin:YourPassword123!@life-context-project.postgres.database.azure.com:5432/life_context"
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=your_account;AccountKey=your_key;EndpointSuffix=core.windows.net"
```

### Install & Run

```bash
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

---

## 📡 API Endpoints

### `POST /audio/upload/{member_id}`

Upload WAV file and chunk it.

**Example:**
```bash
curl -X POST http://localhost:8000/audio/upload/prashant \
  -F "file=@recording_2024-11-26_14-00-00.wav"
```

**Response:**
```json
{
  "status": "success",
  "upload_id": "abc-123-def-456",
  "member_id": "prashant",
  "original_filename": "recording_2024-11-26_14-00-00.wav",
  "recording_datetime": "2024-11-26T14:00:00",
  "duration_seconds": 3600.5,
  "total_chunks": 12,
  "message": "Audio chunked and ready for processing"
}
```

### `GET /audio/uploads/{member_id}`

List all uploads for a member.

### `GET /audio/upload/{upload_id}`

Get details for specific upload including chunk information.

---

## 🗄️ Database Tables Created

```sql
audio_uploads (
    id UUID PRIMARY KEY,
    member_id VARCHAR(100),
    original_filename VARCHAR(500),
    recording_datetime TIMESTAMP,
    duration_seconds FLOAT,
    total_chunks INT,
    status VARCHAR(50),
    uploaded_at TIMESTAMP
)

audio_chunks (
    id UUID PRIMARY KEY,
    upload_id UUID,
    chunk_index INT,
    start_time_sec FLOAT,
    duration_sec FLOAT,
    blob_path VARCHAR(1000)
)
```

---

## 📁 Blob Storage Structure

```
Container: audio-files
└── chunks/
    ├── 2024-11-26_14-00-00_abc123_chunk_0.wav
    ├── 2024-11-26_14-00-00_abc123_chunk_1.wav
    └── ...
```

---

## 🔧 Azure Blob Storage Setup

```bash
# Create storage account
az storage account create \
  --name lifecontextstorage \
  --resource-group life-context-rg \
  --location eastus \
  --sku Standard_LRS

# Get connection string
az storage account show-connection-string \
  --name lifecontextstorage \
  --resource-group life-context-rg

# Create container
az storage container create \
  --name audio-files \
  --account-name lifecontextstorage
```

---

## 🚀 Azure Deployment

1. **Push to GitHub**
2. **In Azure Portal**:
   - Create Web App (Python 3.11)
   - Set environment variables (DATABASE_URL, AZURE_STORAGE_CONNECTION_STRING)
   - Set startup command: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`
3. **Connect GitHub** for auto-deploy

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8000/

# Upload audio
curl -X POST http://localhost:8000/audio/upload/testuser \
  -F "file=@test_audio.wav"

# List uploads
curl http://localhost:8000/audio/uploads/testuser
```

---

## 📝 Next Steps

After upload completes, use the Whisper Processing API to transcribe the chunks.
