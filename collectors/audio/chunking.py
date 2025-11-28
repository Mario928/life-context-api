"""
Audio Chunking Utilities
Extracted from friend's Whisper notebook - minimal changes
"""
from pydub import AudioSegment
from typing import List, Tuple


def make_chunks_with_overlap(
    audio_path: str,
    chunk_minutes: int = 5,
    overlap_seconds: int = 30,
) -> List[Tuple[AudioSegment, float]]:
    """
    Split audio into chunks with overlap.
    
    Returns list of (chunk_audio_segment, chunk_start_time_sec).
    
    - Each chunk is ~chunk_minutes long.
    - Each chunk (except the first) starts `overlap_seconds` earlier than the
      previous chunk ended.
      
    This is the exact code from friend's notebook.
    """
    audio = AudioSegment.from_file(audio_path)
    total_ms = len(audio)

    chunk_ms = chunk_minutes * 60 * 1000
    overlap_ms = overlap_seconds * 1000

    chunks = []
    start_ms = 0

    while start_ms < total_ms:
        end_ms = min(start_ms + chunk_ms, total_ms)
        chunk = audio[start_ms:end_ms]
        start_sec = start_ms / 1000.0
        chunks.append((chunk, start_sec))

        if end_ms >= total_ms:
            break

        # Move start of next chunk: end - overlap
        start_ms = end_ms - overlap_ms

    return chunks


def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds"""
    audio = AudioSegment.from_file(audio_path)
    return len(audio) / 1000.0
