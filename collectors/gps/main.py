"""
GPS Data Collection API
Part of Life Context API - Captures location data from GPSLogger mobile app

Simple, production-ready FastAPI service with:
- Connection pooling for better performance
- Auto table creation on startup
- Error handling
- Health checks for Azure monitoring
"""
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
import psycopg2
from psycopg2 import pool
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
# Azure will use its own environment variables (set in portal)
load_dotenv()

# Global connection pool (initialized on startup)
db_pool = None


def init_db_pool():
    """Initialize PostgreSQL connection pool"""
    global db_pool
    db_url = os.environ.get(
        'DATABASE_URL', 
        'postgresql://user:password@localhost:5432/lifecontext_db'  # Set DATABASE_URL in Azure environment variables
    )
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, db_url)


def get_db_connection():
    """Get a connection from the pool"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database pool not initialized")
    return db_pool.getconn()


def release_db_connection(conn):
    """Return connection to the pool"""
    if db_pool:
        db_pool.putconn(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle
    Creates table and connection pool on startup
    """
    # Startup: Initialize pool and create table
    init_db_pool()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create table if doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gps_logs (
                id SERIAL PRIMARY KEY,
                member_id VARCHAR(100) NOT NULL,
                data JSONB NOT NULL,
                received_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_gps_member ON gps_logs(member_id);
            CREATE INDEX IF NOT EXISTS idx_gps_received ON gps_logs(received_at);
        """)
        
        conn.commit()
        cursor.close()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        raise
    finally:
        release_db_connection(conn)
    
    yield  # App runs here
    
    # Shutdown: Close pool
    if db_pool:
        db_pool.closeall()
        print("✓ Database connections closed")


app = FastAPI(
    title="Life Context - GPS Collector",
    description="Receives GPS data from GPSLogger mobile app",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/gps/{member_id}")
async def receive_gps(member_id: str, request: Request):
    """
    Receive GPS data from GPSLogger app
    
    Stores raw JSON as JSONB for maximum flexibility and zero data loss.
    member_id: Unique identifier for the person (e.g., 'prashant', 'friend1')
    """
    try:
        # Accept ANY JSON structure from GPSLogger
        data = await request.json()
        
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO gps_logs (member_id, data, received_at) 
                VALUES (%s, %s, %s)
            """, (member_id, json.dumps(data), datetime.utcnow()))
            
            conn.commit()
            cursor.close()
            
            return {
                "status": "ok", 
                "member": member_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            release_db_connection(conn)
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/")
async def health():
    """Health check endpoint - Azure uses this to monitor service status"""
    try:
        # Quick DB connection test
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        release_db_connection(conn)
        
        return {
            "status": "healthy",
            "service": "GPS Collector",
            "database": "connected",
            "message": "Life Context API - GPS data collection active"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "GPS Collector",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/stats/{member_id}")
async def get_stats(member_id: str):
    """
    Get GPS data statistics for a member
    
    Returns total points logged and time range
    """
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*), 
                       MIN(received_at), 
                       MAX(received_at)
                FROM gps_logs 
                WHERE member_id = %s
            """, (member_id,))
            
            count, first, last = cursor.fetchone()
            cursor.close()
            
            return {
                "member_id": member_id,
                "total_points": count or 0,
                "first_log": first.isoformat() if first else None,
                "last_log": last.isoformat() if last else None,
                "active": count > 0
            }
        finally:
            release_db_connection(conn)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.get("/recent/{member_id}")
async def get_recent(member_id: str, limit: int = 10):
    """
    Get recent GPS points for a member (for debugging/testing)
    
    limit: Number of recent points to return (default 10, max 100)
    """
    if limit > 100:
        limit = 100
        
    try:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data, received_at 
                FROM gps_logs 
                WHERE member_id = %s
                ORDER BY received_at DESC
                LIMIT %s
            """, (member_id, limit))
            
            rows = cursor.fetchall()
            cursor.close()
            
            points = [
                {
                    "data": row[0],
                    "received_at": row[1].isoformat()
                }
                for row in rows
            ]
            
            return {
                "member_id": member_id,
                "count": len(points),
                "points": points
            }
        finally:
            release_db_connection(conn)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
