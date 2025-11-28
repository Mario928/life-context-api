"""
Audio Upload API
Receives WAV files, chunks them, and stores to Azure Blob Storage

Flow:
1. Receive audio file upload
2. Chunk audio using friend's algorithm (5 min chunks, 30s overlap)
3. Upload chunks to Azure Blob Storage
4. Store metadata in PostgreSQL
5. Return upload_id for later processing
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import pool
import os
import uuid
import tempfile
from azure.storage.blob import BlobServiceClient

from chunking import make_chunks_with_overlap, get_audio_duration

# Global variables
db_pool = None
blob_service_client = None


def init_db_pool():
    """Initialize PostgreSQL connection pool"""
    global db_pool
    db_url = os.environ.get(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/lifecontext_db'  # Set DATABASE_URL in Azure environment variables
    )
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url)


def init_blob_client():
    """Initialize Azure Blob Storage client"""
    global blob_service_client
    connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
    if connection_string:
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)


def get_db_connection():
    """Get connection from pool"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    return db_pool.getconn()


def release_db_connection(conn):
    """Return connection to pool"""
    if db_pool:
        db_pool.putconn(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: Create tables and initialize connections"""
    init_db_pool()
    init_blob_client()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audio_uploads (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                member_id VARCHAR(100) NOT NULL,
                original_filename VARCHAR(500) NOT NULL,
                recording_datetime TIMESTAMP,
                duration_seconds FLOAT,
                total_chunks INT,
                status VARCHAR(50) DEFAULT 'chunked',
                uploaded_at TIMESTAMP DEFAULT NOW(),
                processed_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS audio_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                upload_id UUID REFERENCES audio_uploads(id) ON DELETE CASCADE,
                chunk_index INT NOT NULL,
                start_time_sec FLOAT NOT NULL,
                duration_sec FLOAT NOT NULL,
                blob_path VARCHAR(1000) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_uploads_member ON audio_uploads(member_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_upload ON audio_chunks(upload_id);
        """)
        
        conn.commit()
        cursor.close()
        print("✓ Audio database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise
    finally:
        release_db_connection(conn)
    
    yield
    
    # Shutdown
    if db_pool:
        db_pool.closeall()
        print("✓ Database connections closed")


app = FastAPI(
    title="Life Context - Audio Upload",
    description="Receives audio files, chunks them, and stores to Azure Blob",
    version="1.0.0",
    lifespan=lifespan
)


def parse_datetime_from_filename(filename: str) -> datetime | None:
    """Try to extract datetime from filename like 'recording_2024-11-26_14-00-00.wav'"""
    try:
        # Common patterns in recording filenames
        parts = filename.replace('.wav', '').replace('.WAV', '').split('_')
        for i in range(len(parts) - 1):
            try:
                # Try parsing date_time pattern
                dt_str = f"{parts[i]}_{parts[i+1]}"
                return datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S")
            except:
                continue
    except:
        pass
    return None


@app.post("/audio/upload/{member_id}")
async def upload_audio(member_id: str, file: UploadFile = File(...)):
    """
    Upload audio file, chunk it, and store to Azure Blob
    
    - Accepts WAV files (up to 500MB)
    - Chunks into 5-minute segments with 30s overlap
    - Stores chunks in Azure Blob Storage
    - Returns upload_id for later processing
    """
    if not file.filename.lower().endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only WAV files supported")
    
    # Generate upload ID
    upload_id = str(uuid.uuid4())
    recording_dt = parse_datetime_from_filename(file.filename)
    
    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    try:
        # Get audio duration
        duration = get_audio_duration(tmp_path)
        
        # FIRST: Upload original file to Blob Storage (if configured)
        container_name = "audio-files"
        dt_prefix = recording_dt.strftime("%Y-%m-%d_%H-%M-%S") if recording_dt else "unknown"
        original_blob_path = f"original/{dt_prefix}_{upload_id}.wav"
        
        if blob_service_client:
            try:
                blob_client = blob_service_client.get_blob_client(
                    container=container_name,
                    blob=original_blob_path
                )
                with open(tmp_path, 'rb') as data:
                    blob_client.upload_blob(data, overwrite=True)
                print(f"✓ Uploaded original file: {original_blob_path}")
            except Exception as e:
                print(f"Warning: Original file upload failed: {e}")
        
        # THEN: Chunk the audio (using friend's code)
        chunks = make_chunks_with_overlap(
            tmp_path,
            chunk_minutes=5,
            overlap_seconds=30
        )
        
        # Upload chunks to Azure Blob (if configured)
        chunk_records = []
        
        for idx, (chunk_audio, start_sec) in enumerate(chunks):
            # Create chunk filename
            dt_prefix = recording_dt.strftime("%Y-%m-%d_%H-%M-%S") if recording_dt else "unknown"
            chunk_filename = f"{dt_prefix}_{upload_id}_chunk_{idx}.wav"
            blob_path = f"chunks/{chunk_filename}"
            
            # Save chunk to temp file
            chunk_tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            chunk_audio.export(chunk_tmp.name, format="wav")
            
            # Upload to Blob Storage (if configured)
            if blob_service_client:
                try:
                    blob_client = blob_service_client.get_blob_client(
                        container=container_name,
                        blob=blob_path
                    )
                    with open(chunk_tmp.name, 'rb') as data:
                        blob_client.upload_blob(data, overwrite=True)
                except Exception as e:
                    print(f"Warning: Blob upload failed for chunk {idx}: {e}")
            
            # Store chunk metadata
            chunk_duration = len(chunk_audio) / 1000.0
            chunk_records.append({
                'chunk_index': idx,
                'start_time_sec': start_sec,
                'duration_sec': chunk_duration,
                'blob_path': blob_path
            })
            
            # Cleanup temp chunk file
            os.unlink(chunk_tmp.name)
        
        # Store in database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Insert upload record
            cursor.execute("""
                INSERT INTO audio_uploads 
                (id, member_id, original_filename, recording_datetime, duration_seconds, total_chunks, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (upload_id, member_id, file.filename, recording_dt, duration, len(chunks), 'chunked'))
            
            # Insert chunk records
            for chunk in chunk_records:
                cursor.execute("""
                    INSERT INTO audio_chunks
                    (upload_id, chunk_index, start_time_sec, duration_sec, blob_path)
                    VALUES (%s, %s, %s, %s, %s)
                """, (upload_id, chunk['chunk_index'], chunk['start_time_sec'], 
                      chunk['duration_sec'], chunk['blob_path']))
            
            conn.commit()
            cursor.close()
            
            return {
                "status": "success",
                "upload_id": upload_id,
                "member_id": member_id,
                "original_filename": file.filename,
                "recording_datetime": recording_dt.isoformat() if recording_dt else None,
                "duration_seconds": duration,
                "total_chunks": len(chunks),
                "message": "Audio chunked and ready for processing"
            }
            
        finally:
            release_db_connection(conn)
    
    finally:
        # Cleanup original temp file
        os.unlink(tmp_path)


@app.get("/")
async def health():
    """Health check"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        release_db_connection(conn)
        
        return {
            "status": "healthy",
            "service": "Audio Upload API",
            "database": "connected",
            "blob_storage": "configured" if blob_service_client else "not configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/audio/uploads/{member_id}")
async def list_uploads(member_id: str):
    """List all audio uploads for a member"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, original_filename, recording_datetime, duration_seconds, 
                   total_chunks, status, uploaded_at
            FROM audio_uploads
            WHERE member_id = %s
            ORDER BY uploaded_at DESC
        """, (member_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        uploads = [
            {
                "upload_id": str(row[0]),
                "filename": row[1],
                "recording_datetime": row[2].isoformat() if row[2] else None,
                "duration_seconds": row[3],
                "total_chunks": row[4],
                "status": row[5],
                "uploaded_at": row[6].isoformat()
            }
            for row in rows
        ]
        
        return {
            "member_id": member_id,
            "count": len(uploads),
            "uploads": uploads
        }
    finally:
        release_db_connection(conn)


@app.get("/audio/upload/{upload_id}")
async def get_upload_details(upload_id: str):
    """Get details for a specific upload including chunk information"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get upload info
        cursor.execute("""
            SELECT member_id, original_filename, recording_datetime, 
                   duration_seconds, total_chunks, status, uploaded_at
            FROM audio_uploads
            WHERE id = %s
        """, (upload_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Get chunks
        cursor.execute("""
            SELECT chunk_index, start_time_sec, duration_sec, blob_path
            FROM audio_chunks
            WHERE upload_id = %s
            ORDER BY chunk_index
        """, (upload_id,))
        
        chunk_rows = cursor.fetchall()
        cursor.close()
        
        return {
            "upload_id": upload_id,
            "member_id": row[0],
            "filename": row[1],
            "recording_datetime": row[2].isoformat() if row[2] else None,
            "duration_seconds": row[3],
            "total_chunks": row[4],
            "status": row[5],
            "uploaded_at": row[6].isoformat(),
            "chunks": [
                {
                    "chunk_index": c[0],
                    "start_time_sec": c[1],
                    "duration_sec": c[2],
                    "blob_path": c[3]
                }
                for c in chunk_rows
            ]
        }
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
