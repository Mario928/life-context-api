"""
Whisper Transcription Core
Extracted from friend's notebook - uses faster-whisper large-v3
"""
import torch
from faster_whisper import WhisperModel
from typing import List, Dict, Tuple
import tempfile
import os

# Global model instance (loaded once)
_model = None


def init_whisper_model():
    """
    Initialize Whisper model (call once at startup)
    Uses large-v3 model with GPU if available
    """
    global _model
    
    if _model is not None:
        return _model
    
    # Pick device + compute_type (from friend's code)
    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "int8_float16"  # good mix of speed + quality
        print("✓ Using CUDA GPU for Whisper")
    else:
        device = "cpu"
        compute_type = "int8"  # CPU will be slow, but works
        print("⚠ Using CPU for Whisper (this will be slow)")
    
    _model = WhisperModel(
        "large-v3",
        device=device,
        compute_type=compute_type,
    )
    
    print("✓ Whisper model loaded")
    return _model


def transcribe_chunk_file(
    chunk_path: str,
    initial_prompt: str = None
) -> Tuple[str, List[Dict], str, float]:
    """
    Transcribe a single audio chunk file using Whisper.
    
    Returns:
        - chunk_text: Full text for this chunk
        - segments: List of segments with timestamps
        - language: Detected language
        - language_probability: Confidence score
        
    Based on friend's transcribe_with_5min_chunks function
    """
    model = init_whisper_model()
    
    # Run transcription (from friend's code)
    segments_iter, info = model.transcribe(
        chunk_path,
        task="translate",  # any language -> English
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
        initial_prompt=initial_prompt or None,
    )
    
    # Collect segments
    chunk_text_parts = []
    segments = []
    
    for seg in segments_iter:
        text = seg.text
        chunk_text_parts.append(text)
        
        segments.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": text
        })
    
    chunk_text = "".join(chunk_text_parts)
    
    return (
        chunk_text,
        segments,
        info.language,
        float(info.language_probability)
    )


def transcribe_audio_chunks(
    chunk_paths: List[str],
    overlap_seconds: int = 30,
    prompt_tail_chars: int = 300
) -> Tuple[str, List[Dict], List[Dict]]:
    """
    Transcribe multiple audio chunks with context carryover.
    
    Args:
        chunk_paths: List of paths to chunk files
        overlap_seconds: Overlap duration for deduplication
        prompt_tail_chars: Characters to carry forward as context
    
    Returns:
        - full_text: Combined transcript
        - all_segments: All segments with global timestamps
        - language_per_chunk: Language info per chunk
        
    This is adapted from friend's transcribe_with_5min_chunks function
    """
    model = init_whisper_model()
    
    full_text_parts = []
    all_segments = []
    language_per_chunk = []
    
    prev_tail = ""  # for initial_prompt to next chunk
    
    for idx, chunk_path in enumerate(chunk_paths):
        print(f"Processing chunk {idx+1}/{len(chunk_paths)}")
        
        # Transcribe this chunk
        chunk_text, segments, language, lang_prob = transcribe_chunk_file(
            chunk_path,
            initial_prompt=prev_tail or None
        )
        
        # Record language info
        language_per_chunk.append({
            "chunk_index": idx,
            "language": language,
            "language_probability": lang_prob
        })
        
        # For merging: skip overlap at start of chunk (except first chunk)
        chunk_text_for_merge = []
        
        for seg in segments:
            local_start = seg["start"]
            
            # Skip overlapped region at start (from friend's logic)
            if idx > 0 and local_start < overlap_seconds:
                continue
            
            chunk_text_for_merge.append(seg["text"])
            
            # Add to global segments
            all_segments.append({
                "chunk_index": idx,
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "language": language,
                "language_probability": lang_prob
            })
        
        chunk_text_merge = "".join(chunk_text_for_merge)
        full_text_parts.append(chunk_text_merge)
        
        # Update tail prompt for next chunk
        if chunk_text_merge:
            prev_tail = chunk_text_merge[-prompt_tail_chars:]
        elif chunk_text:
            prev_tail = chunk_text[-prompt_tail_chars:]
    
    full_text = "".join(full_text_parts)
    return full_text, all_segments, language_per_chunk
