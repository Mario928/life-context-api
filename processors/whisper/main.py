"""
Whisper Processing API
Fetches audio chunks from Azure Blob and transcribes them using Whisper

Flow:
1. Receive process request with upload_id
2. Fetch chunk metadata from PostgreSQL
3. Download chunks from Azure Blob
4. Run Whisper transcription (using friend's code)
5. Store results in PostgreSQL
6. Return transcript
"""
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import psycopg2
from psycopg2 import pool
import os
import tempfile
import json
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
load_dotenv()

from transcribe import init_whisper_model, transcribe_chunk_file

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
    """Startup: Initialize DB, Blob, and Whisper model"""
    init_db_pool()
    init_blob_client()
    
    # Create transcripts table
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                chunk_id UUID,
                upload_id UUID NOT NULL,
                chunk_index INT NOT NULL,
                text TEXT,
                language VARCHAR(10),
                language_probability FLOAT,
                segments JSONB,
                processed_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE INDEX IF NOT EXISTS idx_transcripts_upload ON transcripts(upload_id);
        """)
        conn.commit()
        cursor.close()
        print("✓ Transcripts database initialized")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise
    finally:
        release_db_connection(conn)
    
    # Initialize Whisper model
    print("Loading Whisper model...")
    init_whisper_model()
    
    yield
    
    # Shutdown
    if db_pool:
        db_pool.closeall()


app = FastAPI(
    title="Life Context - Whisper Processor",
    description="Transcribes audio chunks using Whisper large-v3",
    version="1.0.0",
    lifespan=lifespan
)


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
            "service": "Whisper Processor",
            "database": "connected",
            "blob_storage": "configured" if blob_service_client else "not configured",
            "model": "loaded"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/whisper/process/{upload_id}")
async def process_upload(upload_id: str):
    """
    Process all chunks for an upload using Whisper
    
    - Fetches chunks from Azure Blob
    - Transcribes each chunk
    - Stores results in PostgreSQL
    - Returns full transcript
    """
    if not blob_service_client:
        raise HTTPException(
            status_code=500,
            detail="Azure Blob Storage not configured. Set AZURE_STORAGE_CONNECTION_STRING"
        )
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get upload info
        cursor.execute("""
            SELECT member_id, original_filename, total_chunks, status
            FROM audio_uploads
            WHERE id = %s
        """, (upload_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        member_id, filename, total_chunks, status = row
        
        # Get chunks
        cursor.execute("""
            SELECT id, chunk_index, blob_path, start_time_sec
            FROM audio_chunks
            WHERE upload_id = %s
            ORDER BY chunk_index
        """, (upload_id,))
        
        chunks = cursor.fetchall()
        cursor.close()
        
        if not chunks:
            raise HTTPException(status_code=404, detail="No chunks found")
        
        # Process each chunk
        results = []
        prev_tail = ""
        
        for chunk_id, chunk_idx, blob_path, start_time in chunks:
            print(f"Processing chunk {chunk_idx + 1}/{total_chunks}")
            
            # Download chunk from Blob
            container_name = "audio-files"
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_path
            )
            
            # Download to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                blob_data = blob_client.download_blob()
                blob_data.readinto(tmp_file)
                tmp_path = tmp_file.name
            
            try:
                # Transcribe chunk (using friend's code)
                chunk_text, segments, language, lang_prob = transcribe_chunk_file(
                    tmp_path,
                    initial_prompt=prev_tail or None
                )
                
                # Update context for next chunk
                if chunk_text:
                    prev_tail = chunk_text[-300:]  # last 300 chars
                
                results.append({
                    'chunk_id': str(chunk_id),
                    'chunk_index': chunk_idx,
                    'text': chunk_text,
                    'language': language,
                    'language_probability': lang_prob,
                    'segments': segments
                })
                
            finally:
                os.unlink(tmp_path)
        
        # Store results in database
        cursor = conn.cursor()
        
        for result in results:
            cursor.execute("""
                INSERT INTO transcripts
                (chunk_id, upload_id, chunk_index, text, language, language_probability, segments)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                result['chunk_id'],
                upload_id,
                result['chunk_index'],
                result['text'],
                result['language'],
                result['language_probability'],
                json.dumps(result['segments'])
            ))
        
        # Update upload status
        cursor.execute("""
            UPDATE audio_uploads
            SET status = 'completed', processed_at = NOW()
            WHERE id = %s
        """, (upload_id,))
        
        conn.commit()
        cursor.close()
        
        # Combine full transcript
        full_text = "".join(r['text'] for r in results)
        
        return {
            "status": "completed",
            "upload_id": upload_id,
            "member_id": member_id,
            "filename": filename,
            "chunks_processed": len(results),
            "full_transcript": full_text,
            "languages": list(set(r['language'] for r in results)),
            "message": "Transcription completed successfully"
        }
        
    except Exception as e:
        # Update status to failed
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE audio_uploads
                SET status = 'failed'
                WHERE id = %s
            """, (upload_id,))
            conn.commit()
            cursor.close()
        except:
            pass
        
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
        
    finally:
        release_db_connection(conn)


@app.get("/whisper/transcript/{upload_id}")
async def get_transcript(upload_id: str):
    """Get full transcript for an upload"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get upload info
        cursor.execute("""
            SELECT member_id, original_filename, status, processed_at
            FROM audio_uploads
            WHERE id = %s
        """, (upload_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        member_id, filename, status, processed_at = row
        
        if status != 'completed':
            return {
                "upload_id": upload_id,
                "status": status,
                "message": f"Transcription not completed yet (status: {status})"
            }
        
        # Get transcripts
        cursor.execute("""
            SELECT chunk_index, text, language, language_probability, segments
            FROM transcripts
            WHERE upload_id = %s
            ORDER BY chunk_index
        """, (upload_id,))
        
        rows = cursor.fetchall()
        cursor.close()
        
        # Combine text
        full_text = "".join(row[1] for row in rows)
        
        # Get all segments
        all_segments = []
        for row in rows:
            segments = row[4]  # JSONB
            all_segments.extend(segments)
        
        return {
            "upload_id": upload_id,
            "member_id": member_id,
            "filename": filename,
            "status": status,
            "processed_at": processed_at.isoformat() if processed_at else None,
            "full_transcript": full_text,
            "total_chunks": len(rows),
            "segments": all_segments,
            "languages": list(set(row[2] for row in rows))
        }
        
    finally:
        release_db_connection(conn)


@app.get("/whisper/status/{upload_id}")
async def get_status(upload_id: str):
    """Check processing status for an upload"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT member_id, original_filename, total_chunks, status, 
                   uploaded_at, processed_at
            FROM audio_uploads
            WHERE id = %s
        """, (upload_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        return {
            "upload_id": upload_id,
            "member_id": row[0],
            "filename": row[1],
            "total_chunks": row[2],
            "status": row[3],
            "uploaded_at": row[4].isoformat(),
            "processed_at": row[5].isoformat() if row[5] else None
        }
        
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
