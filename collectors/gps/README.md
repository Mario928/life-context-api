# GPS Data Collector

FastAPI service that receives GPS location data from the GPSLogger mobile app and stores it in PostgreSQL.

Part of the Life Context API project for capturing and analyzing daily life patterns.

---

## 🎯 What It Does

- Receives GPS coordinates from GPSLogger Android app via HTTP POST
- Stores raw GPS data as JSONB (flexible, future-proof)
- Provides stats and recent data endpoints for analysis
- Auto-creates database tables on startup
- Connection pooling for better performance

---

## 🚀 Quick Start - Local Development

### 1. Prerequisites

- Python 3.9+
- PostgreSQL installed and running

### 2. Setup Database

```bash
# Create database
createdb life_context

# Set environment variable (replace with your username)
export DATABASE_URL="postgresql://your_username@localhost:5432/life_context"
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Service

```bash
# Option 1: Direct run
python main.py

# Option 2: With auto-reload (for development)
uvicorn main:app --reload

# Service runs on http://localhost:8000
```

### 5. Test It

```bash
# Health check
curl http://localhost:8000/

# Send test GPS data
curl -X POST http://localhost:8000/gps/prashant \
  -H "Content-Type: application/json" \
  -d '{"latitude": 40.7128, "longitude": -74.0060, "timestamp": "2024-11-26T20:00:00Z"}'

# Check stats
curl http://localhost:8000/stats/prashant

# Get recent points
curl http://localhost:8000/recent/prashant?limit=5
```

---

## 📱 GPSLogger App Setup

### Download App

- **Android**: [GPSLogger from F-Droid](https://f-droid.org/packages/com.mendhak.gpslogger/) (free, open source)

### Configure App

1. Open GPSLogger → Settings → Logging details
2. Enable **"Log to custom URL"**
3. Configure:
   - **URL**: `https://your-domain.com/gps/YOUR_NAME` (replace YOUR_NAME with your identifier)
   - **HTTP Method**: `POST`
   - **HTTP Headers**: `Content-Type: application/json`
   - **HTTP Body**:
     ```json
     {
       "latitude": %LAT,
       "longitude": %LON,
       "timestamp": %TIME,
       "accuracy": %ACC,
       "speed": %SPD,
       "battery": %BATT,
       "altitude": %ALT
     }
     ```

4. Start logging - GPS data will be sent to your API automatically!

---

## 🌐 Azure Deployment

### 1. Create Azure Resources

```bash
# Login to Azure
az login

# Create resource group
az group create --name life-context-rg --location eastus

# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group life-context-rg \
  --name life-context-db \
  --location eastus \
  --admin-user dbadmin \
  --admin-password YOUR_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15

# Create database
az postgres flexible-server db create \
  --resource-group life-context-rg \
  --server-name life-context-db \
  --database-name life_context

# Create Web App
az webapp up \
  --resource-group life-context-rg \
  --name life-context-gps \
  --runtime "PYTHON:3.11" \
  --sku B1
```

### 2. Configure Web App

In Azure Portal:
- Go to your Web App → Configuration → Application Settings
- Add environment variable:
  - **Name**: `DATABASE_URL`
  - **Value**: `postgresql://dbadmin:YOUR_PASSWORD@life-context-db.postgres.database.azure.com:5432/life_context?sslmode=require`

- Go to Configuration → General Settings
- **Startup Command**: `python -m uvicorn main:app --host 0.0.0.0 --port 8000`

### 3. Deploy via GitHub

- Fork/push code to GitHub
- In Azure Portal → Deployment Center
- Connect to your GitHub repo
- Select branch → Azure auto-deploys on push

**Your API will be live at**: `https://life-context-gps.azurewebsites.net/`

---

## 📡 API Endpoints

### `POST /gps/{member_id}`

Receive GPS data from GPSLogger.

**Parameters:**
- `member_id` (path): Unique identifier for the person (e.g., "prashant", "friend1")

**Request Body**: Any JSON (flexible - stores everything)

**Example**:
```bash
curl -X POST https://your-api.com/gps/prashant \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timestamp": "2024-11-26T20:00:00Z",
    "accuracy": 10.5,
    "speed": 0.0,
    "battery": 85.0
  }'
```

**Response**:
```json
{
  "status": "ok",
  "member": "prashant",
  "timestamp": "2024-11-26T20:00:05.123456"
}
```

---

### `GET /`

Health check endpoint (used by Azure monitoring).

**Response**:
```json
{
  "status": "healthy",
  "service": "GPS Collector",
  "database": "connected",
  "message": "Life Context API - GPS data collection active"
}
```

---

### `GET /stats/{member_id}`

Get GPS statistics for a member.

**Response**:
```json
{
  "member_id": "prashant",
  "total_points": 1547,
  "first_log": "2024-11-20T08:00:00",
  "last_log": "2024-11-26T21:00:00",
  "active": true
}
```

---

### `GET /recent/{member_id}?limit=10`

Get recent GPS points (for debugging/testing).

**Parameters**:
- `limit` (query, optional): Number of points to return (default: 10, max: 100)

**Response**:
```json
{
  "member_id": "prashant",
  "count": 5,
  "points": [
    {
      "data": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timestamp": "2024-11-26T20:00:00Z"
      },
      "received_at": "2024-11-26T20:00:05"
    }
  ]
}
```

---

## 🗄️ Database Schema

The service auto-creates this table on startup:

```sql
CREATE TABLE gps_logs (
    id SERIAL PRIMARY KEY,
    member_id VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,              -- Stores complete GPS JSON
    received_at TIMESTAMP NOT NULL,   -- When API received it
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_gps_member ON gps_logs(member_id);
CREATE INDEX idx_gps_received ON gps_logs(received_at);
```

**Why JSONB?**
- Flexible - accepts any fields from GPSLogger
- Future-proof - add new fields without schema changes
- Fast queries - PostgreSQL indexes JSONB efficiently
- Zero data loss - stores everything

---

## 🔧 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql://user:password@localhost:5432/life_context` | PostgreSQL connection string |

**Format**: `postgresql://username:password@host:port/database`

**For Azure**: `postgresql://user:pass@server.postgres.database.azure.com:5432/dbname?sslmode=require`

---

## 🧪 Testing Tips

### Check Database Directly

```sql
-- Count total GPS points
SELECT member_id, COUNT(*) as points
FROM gps_logs
GROUP BY member_id;

-- View recent data
SELECT member_id, data, received_at
FROM gps_logs
ORDER BY received_at DESC
LIMIT 10;

-- Query by location (if you have lat/lon in data)
SELECT member_id, data->>'latitude' as lat, data->>'longitude' as lon
FROM gps_logs
WHERE member_id = 'prashant';
```

### Simulate GPSLogger

```bash
# Send a day's worth of GPS points (every 5 minutes)
for i in {1..288}; do
  curl -X POST http://localhost:8000/gps/prashant \
    -H "Content-Type: application/json" \
    -d "{\"latitude\": 40.7128, \"longitude\": -74.006$i, \"timestamp\": \"2024-11-26T$(printf %02d $((i/12))):$(printf %02d $((i%12*5))):00Z\"}"
  sleep 0.5
done
```

---

## 🔮 Future Enhancements

- [ ] Batch geocoding (lat/long → place names using Google API)
- [ ] Location clustering (detect "home", "work", frequent places)
- [ ] Privacy features (data retention policies, anonymization)
- [ ] Webhook for real-time notifications
- [ ] Integration with audio processing for time-location correlation

---

## 📚 Related Components

This is part of the larger Life Context API:
- **GPS Collector** (this) - Location tracking
- **Audio Transcription** - Speech-to-text, speaker diarization (Whisper + Pyannote)
- **Noise Analysis** - Environmental sound classification (YAMNet)
- **Context Analysis** - Correlate location with audio for life patterns

---

## 🐛 Troubleshooting

### "Database pool not initialized"
- Check `DATABASE_URL` is set correctly
- Ensure PostgreSQL is running
- Verify database exists: `psql -l`

### "Connection refused"
- PostgreSQL not running: `brew services start postgresql@15`
- Wrong host/port in `DATABASE_URL`

### GPSLogger not sending data
- Check URL is correct (https if deployed)
- Verify Content-Type header is set
- Check phone has internet connection
- Look at app logs for HTTP errors

### Azure deployment fails
- Check startup command is set
- Verify Python version matches (3.11)
- Check Application Insights logs in Azure Portal

---

## 📞 Contact

Part of course project - adjust and extend as needed for your use case!
