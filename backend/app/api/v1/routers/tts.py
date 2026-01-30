"""
TTS HTTP API Router

Provides simple HTTP TTS interface for streaming translation
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import asyncio
import numpy as np

router = APIRouter()


class TtsRequest(BaseModel):
    text: str
    accent: str = "American English"
    model: str = "free"  # "free" = MelonTTS (local), "paid" = ElevenLabs (API)


async def _generate_melotts_audio(text: str, accent: str) -> tuple[bytes, str]:
    """
    Generate audio using MelonTTS (local model)
    
    Args:
        text: Text to synthesize
        accent: Accent type
    
    Returns:
        tuple[bytes, str]: (audio data, MIME type)
    """
    from app.services.tts_elevenlabs import (
        _get_melotts_model,
        _accent_to_speaker_id,
        _get_melotts_executor
    )
    
    # Determine language model based on accent
    accent_lower = (accent or "").lower()
    if "chinese" in accent_lower or "china" in accent_lower:
        language = 'ZH'
    else:
        language = 'EN'
    
    # Get model (use cache)
    model, speaker_ids = _get_melotts_model(language)
    speaker_id = _accent_to_speaker_id(accent, speaker_ids, language)
    
    print(f"[TTS API][MelonTTS] Synthesizing speech: text='{text[:50]}...', accent={accent}, speaker_id={speaker_id}, language={language}")
    
    # Generate audio in thread pool
    executor = _get_melotts_executor()
    loop = asyncio.get_event_loop()
    
    def synthesize():
        """Synchronous synthesis function executed in thread pool"""
        audio = model.tts_to_file(
            text=text,
            speaker_id=speaker_id,
            output_path=None,
            speed=1.0,
            quiet=True
        )
        sample_rate = model.hps.data.sampling_rate
        return audio, sample_rate
    
    audio, sample_rate = await loop.run_in_executor(executor, synthesize)
    
    # Convert to audio bytes
    audio = np.clip(audio, -1.0, 1.0)
    
    # ✅ Prefer WAV format (more reliable, better browser support)
    try:
        import soundfile as sf
        
        # Directly output WAV (16-bit PCM, native browser support)
        audio = audio.astype(np.float32)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio, sample_rate, format='WAV', subtype='PCM_16')
        wav_buffer.seek(0)
        audio_bytes = wav_buffer.read()
        print(f"[TTS API][MelonTTS] WAV conversion completed, size: {len(audio_bytes)} bytes, sample_rate={sample_rate}")
        return audio_bytes, "audio/wav"
    except Exception as e:
        print(f"[TTS API][MelonTTS] ⚠️ WAV conversion failed: {e}, trying MP3...")
        
        # If WAV fails, try MP3 (fallback)
        try:
            from pydub import AudioSegment
            
            # Convert to 16-bit PCM
            audio_int16 = (audio * 32767.0).astype(np.int16)
            
            # Create AudioSegment
            audio_segment = AudioSegment(
                audio_int16.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,
                channels=1
            )
            
            # Export as MP3 (more compatible parameters)
            mp3_buffer = io.BytesIO()
            audio_segment.export(
                mp3_buffer, 
                format="mp3", 
                bitrate="128k",
                parameters=["-ar", "22050"]  # Lower sample rate for better compatibility
            )
            mp3_buffer.seek(0)
            audio_bytes = mp3_buffer.read()
            print(f"[TTS API][MelonTTS] MP3 conversion completed, size: {len(audio_bytes)} bytes, sample_rate={sample_rate}")
            return audio_bytes, "audio/mpeg"
        except Exception as e2:
            print(f"[TTS API][MelonTTS] ❌ MP3 conversion also failed: {e2}")
            raise RuntimeError(f"Audio conversion failed: WAV({e}), MP3({e2})")


async def _generate_elevenlabs_audio(text: str, accent: str) -> tuple[bytes, str]:
    """
    Generate audio using ElevenLabs (API)
    
    Args:
        text: Text to synthesize
        accent: Accent type
    
    Returns:
        tuple[bytes, str]: (audio data, MIME type)
    """
    from app.services.tts_elevenlabs import _stream_elevenlabs, _pick_voice_id_by_accent
    
    voice_id = _pick_voice_id_by_accent(accent)
    
    print(f"[TTS API][ElevenLabs] Synthesizing speech: text='{text[:50]}...', accent={accent}, voice_id={voice_id}")
    
    # ✅ Use optimized voice parameters (based on web settings)
    # Speed controlled by model, here mainly adjust voice quality
    audio_chunks = []
    async for chunk in _stream_elevenlabs(
        text=text,
        voice_id=voice_id,
        stability=0.88,           # Stability (more stable, reduce variation)
        similarity_boost=0.9,    # Similarity boost
        style=0.40,               # Style exaggeration (moderate expressiveness)
        use_speaker_boost=True    # Enable speaker boost
    ):
        audio_chunks.append(chunk)
    
    # Merge audio data
    audio_data = b''.join(audio_chunks)
    print(f"[TTS API][ElevenLabs] Generation completed, size: {len(audio_data)} bytes")
    return audio_data, "audio/mpeg"


@router.post("/synthesize")
async def synthesize_tts(req: TtsRequest):
    """
    Synthesize TTS audio (for streaming translation)
    
    Parameters:
    - text: Text to synthesize
    - accent: Accent (American English, British English, etc.)
    - model: Model selection
      - "free": MelonTTS local model (free, slower)
      - "paid": ElevenLabs API (paid, faster and more natural)
    
    Returns:
    - audio/mpeg audio stream
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    print(f"[TTS API] Received request: model={req.model}, accent={req.accent}, text_len={len(req.text)}")
    
    try:
        # Select TTS service based on model parameter
        if req.model == "paid":
            audio_data, mime_type = await _generate_elevenlabs_audio(req.text, req.accent)
            filename = "tts.mp3"
        else:  # "free" or other values use MelonTTS
            audio_data, mime_type = await _generate_melotts_audio(req.text, req.accent)
            filename = "tts.mp3" if mime_type == "audio/mpeg" else "tts.wav"
        
        print(f"[TTS API] Generation completed: model={req.model}, mime={mime_type}, size={len(audio_data)} bytes")
        
        # Return audio stream (return correct MIME type based on actual format)
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type=mime_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "no-cache",
            }
        )
    except Exception as e:
        print(f"[TTS API] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")

