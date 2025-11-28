# Whisper Processing API

Transcribes audio chunks using OpenAI's Whisper large-v3 model via faster-whisper.

Uses transcription logic from friend's Whisper notebook.

---

## 🎯 What It Does

- Fetches audio chunks from Azure Blob Storage
- Transcribes using Whisper large-v3 (faster-whisper)
- Translates any language to English
- Detects language per chunk
- Carries context between chunks for better accuracy
- Stores results in PostgreSQL

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Azure Blob Storage (with audio chunks)
- **GPU highly recommended** (CPU works but very slow)
- CUDA toolkit if using GPU

### Environment Variables

```bash
export DATABASE_URL="postgresql://dbadmin:YourPassword123!@life-context-project.postgres.database.azure.com:5432/life_context"
export AZURE_STORAGE_CONNECTION_STRING="your_blob_connection_string"
```

### Install & Run

```bash
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8001 (port 8001 to avoid conflict with upload API)
```

**Note:** First startup will download Whisper large-v3 model (~3GB).

---

## 📡 API Endpoints

### `POST /whisper/process/{upload_id}`

Process all chunks for an upload.

**Example:**
```bash
curl -X POST http://localhost:8001/whisper/process/abc-123-def-456
```

**Response:**
```json
{
  "status": "completed",
  "upload_id": "abc-123-def-456",
  "member_id": "prashant",
  "filename": "recording_2024-11-26_14-00-00.wav",
  "chunks_processed": 12,
  "full_transcript": "Hello, this is a test recording...",
  "languages": ["en"],
  "message": "Transcription completed successfully"
}
```

### `GET /whisper/transcript/{upload_id}`

Get full transcript with segments.

**Response:**
```json
{
  "upload_id": "abc-123-def-456",
  "full_transcript": "Complete text here...",
  "segments": [
    {
      "chunk_index": 0,
      "start": 0.0,
      "end": 5.2,
      "text": " Hello, this is a test",
      "language": "en",
      "language_probability": 0.99
    }
  ],
  "languages": ["en"]
}
```

### `GET /whisper/status/{upload_id}`

Check processing status.

---

## 🗄️ Database Table Created

```sql
transcripts (
    id UUID PRIMARY KEY,
    chunk_id UUID,
    upload_id UUID,
    chunk_index INT,
    text TEXT,
    language VARCHAR(10),
    language_probability FLOAT,
    segments JSONB,
    processed_at TIMESTAMP
)
```

---

## 🖥️ GPU Requirements

### For Development (Azure VM)

**Recommended:** NC6 instance (1x NVIDIA Tesla K80)
- Cost: ~$0.90/hour
- Strategy: Start VM when processing, stop when done
- Only pay for hours used

**Setup:**
```bash
# Install CUDA
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda-repo-ubuntu2204-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-12-2-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get -y install cuda

# Verify
nvidia-smi
```

### For CPU (Slow)

Works but expect 10-15 minutes per 1-hour audio file.

---

## 🚀 Azure Deployment Options

### Option 1: Azure VM with GPU

1. Create NC-series VM
2. Install CUDA + dependencies
3. Run API as systemd service
4. Start/stop VM as needed

### Option 2: Azure Container Instances with GPU

```bash
az container create \
  --resource-group life-context-rg \
  --name whisper-processor \
  --image your-docker-image \
  --gpu-count 1 \
  --environment-variables DATABASE_URL=... AZURE_STORAGE_CONNECTION_STRING=...
```

---

## 🧪 Testing

```bash
# Health check
curl http://localhost:8001/

# Process audio (requires existing upload_id from upload API)
curl -X POST http://localhost:8001/whisper/process/abc-123-def-456

# Get transcript
curl http://localhost:8001/whisper/transcript/abc-123-def-456

# Check status
curl http://localhost:8001/whisper/status/abc-123-def-456
```

---

## ⚡ Performance

- **With GPU (NVIDIA K80)**: ~1-2 minutes per 5-min chunk (~12-24 min for 1-hour audio)
- **With CPU**: ~10-15 minutes per 5-min chunk (~2-3 hours for 1-hour audio)

---

## 🔮 Future Enhancements

- [ ] Batch processing multiple uploads
- [ ] Progress tracking (chunks processed / total)
- [ ] Speaker diarization (identify who spoke when)
- [ ] Background sound classification
- [ ] Real-time status updates via WebSocket

---

## 📝 Complete Workflow

```bash
# 1. Upload audio (Upload API)
curl -X POST http://upload-api/audio/upload/prashant \
  -F "file=@recording.wav"
# Returns upload_id: abc-123

# 2. Process with Whisper (this API)
curl -X POST http://whisper-api/whisper/process/abc-123

# 3. Get transcript
curl http://whisper-api/whisper/transcript/abc-123
```
