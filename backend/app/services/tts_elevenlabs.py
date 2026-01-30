import torch
import httpx
import asyncio
from typing import AsyncGenerator
from app.core.pubsub import channel
from app.config import settings  # ✅ Use unified config.py settings

def _pick_voice_id_by_accent(accent: str) -> str:
    """
    Select corresponding Voice ID based on accent
    
    Configuration priority:
    1. VOICE_ID_AMERICAN etc. in .env file
    2. Hardcoded default values in config.py
    """
    a = (accent or "").lower()
    if "australia" in a: 
        return settings.voice_id_australia
    if "british" in a: 
        return settings.voice_id_british
    if "chinese" in a: 
        return settings.voice_id_chinese
    if "india" in a: 
        return settings.voice_id_india
    # Default to American English
    return settings.voice_id_american

async def _stream_elevenlabs(
    text: str, 
    voice_id: str,
    stability: float = 0.88,
    similarity_boost: float = 0.73,
    style: float = 0.73,
    use_speaker_boost: bool = True
) -> AsyncGenerator[bytes, None]:
    """
    Call ElevenLabs API for streaming TTS
    
    Parameters:
    - text: Text to synthesize
    - voice_id: ElevenLabs voice ID
    - stability: Stability (0-1), higher = more stable, lower = more expressive
    - similarity_boost: Similarity boost (0-1), similarity to original voice
    - style: Style exaggeration (0-1), speech expressiveness
    - use_speaker_boost: Whether to enable speaker boost
    
    Configuration source: app.config.settings
    - eleven_api_base: API base URL
    - eleven_api_key: API key
    """
    if not text or not text.strip():
        print("[tts] skip empty text")
        return
    if not settings.eleven_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is missing")

    url = f"{settings.eleven_api_base}/text-to-speech/{voice_id}/stream?optimize_streaming_latency=4"
    headers = {
        "xi-api-key": settings.eleven_api_key,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",  # ⚡ Turbo model: lower latency
        "output_format": "mp3_44100_64",  # 🔧 64kbps: balance quality and speed
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": use_speaker_boost
        },
    }

    print(f"[tts] HTTP POST {url} voice={voice_id}, stability={stability}, similarity={similarity_boost}, style={style}")
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk
                await asyncio.sleep(0)

async def _synth_and_stream_common(conv_id: str, text: str, accent: str):
    voice_id = _pick_voice_id_by_accent(accent)
    # 1) Notify frontend to start
    await channel.pub_tts_json(conv_id, {"type": "start", "mime": "audio/mpeg"})
    print(f"[tts→ws] start -> {conv_id}")

    try:
        # 2) Stream chunks (using optimized voice parameters)
        got_any = False
        async for chunk in _stream_elevenlabs(
            text=text,
            voice_id=voice_id,
            stability=0.88,
            similarity_boost=0.73,
            style=0.73,
            use_speaker_boost=True
        ):
            got_any = True
            await channel.pub_tts_bytes(conv_id, chunk)
        print(f"[tts] stream done, got_any={got_any}")
    finally:
        # 3) Notify frontend to end
        await channel.pub_tts_json(conv_id, {"type": "stop"})
        print(f"[tts→ws] stop  -> {conv_id}")


# ================================ MeloTTS Local Model Related =====================================
# Global model instance (lazy loading, avoid reloading models)
_melotts_model_cache = {}  # Cache by language: {'EN': model, 'ZH': model}
_melotts_executor = None

def _get_melotts_executor():
    """Get thread pool executor"""
    global _melotts_executor
    if _melotts_executor is None:
        from concurrent.futures import ThreadPoolExecutor
        _melotts_executor = ThreadPoolExecutor(max_workers=2)
    return _melotts_executor

def _get_melotts_model(language: str):
    """
    Get or initialize MeloTTS model (with caching)
    
    Args:
        language: Language code 'EN' or 'ZH'
    
    Returns:
        tuple: (model, speaker_ids)
    """
    import os
    import sys
    
    # Check cache
    if language in _melotts_model_cache:
        model = _melotts_model_cache[language]
        speaker_ids = model.hps.data.spk2id
        # Ensure dictionary type
        if not isinstance(speaker_ids, dict):
            speaker_ids = dict(speaker_ids)
        return model, speaker_ids
    
    # Set offline mode (avoid auto-download)
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    
    # Add MeloTTS path to sys.path
    services_dir = os.path.dirname(os.path.abspath(__file__))
    melo_dir = os.path.join(services_dir, 'melo')
    
    if os.path.exists(melo_dir) and services_dir not in sys.path:
        sys.path.insert(0, services_dir)
    
    # Import MeloTTS
    try:
        from melo.api import TTS
    except ImportError as e:
        raise ImportError(
            f"Failed to import MeloTTS: {e}\n"
            "Please ensure melo/ directory is located at app/services/melo/"
        )
    
    # Determine model file path
    app_dir = os.path.dirname(services_dir)
    models_dir = os.path.join(app_dir, 'models', 'tts_models')
    lang_dir = os.path.join(models_dir, language)
    local_ckpt = os.path.join(lang_dir, 'checkpoint.pth')
    local_config = os.path.join(lang_dir, 'config.json')
    
    # Device selection (auto-select GPU/CPU)
    #device = 'auto'
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[melotts] The device used is: {device}")
    
    # Load model
    if os.path.exists(local_ckpt) and os.path.exists(local_config):
        print(f"[melotts] Loading local model: {language}")
        print(f"  - checkpoint: {local_ckpt}")
        print(f"  - config: {local_config}")
        model = TTS(
            language=language,
            device=device,
            use_hf=False,  # Use local files
            config_path=local_config,
            ckpt_path=local_ckpt
        )
    else:
        raise FileNotFoundError(
            f"Model files not found for {language}:\n"
            f"  - {local_ckpt}\n"
            f"  - {local_config}\n"
            f"Please ensure model files are copied to app/models/tts_models/{language}/"
        )
    
    # Cache model
    _melotts_model_cache[language] = model
    speaker_ids = model.hps.data.spk2id
    
    # Ensure dictionary type
    if not isinstance(speaker_ids, dict):
        speaker_ids = dict(speaker_ids)
    
    print(f"[melotts] Model loaded successfully: {language}, available speakers: {list(speaker_ids.keys())}")
    return model, speaker_ids

def _accent_to_speaker_id(accent: str, speaker_ids, language: str) -> int:
    """
    Map accent string to speaker_id
    
    Args:
        accent: Accent type (e.g., "australia", "british", "india", "american")
        speaker_ids: Model's speaker_ids (may be dict or HParams object)
        language: Language code
    
    Returns:
        int: speaker_id
    """
    # Ensure speaker_ids is a dictionary
    if not isinstance(speaker_ids, dict):
        speaker_ids = dict(speaker_ids)
    
    a = (accent or "").lower()
    
    if language == 'ZH':
        # Chinese model has only one speaker
        return speaker_ids.get('ZH', list(speaker_ids.values())[0])
    
    # English model has multiple accents
    # Note: Model uses hyphens (EN-INDIA), not underscores (EN_INDIA)
    if "australia" in a or "au" in a:
        return speaker_ids.get('EN-AU', speaker_ids.get('EN-Default', list(speaker_ids.values())[0]))
    elif "british" in a or "br" in a or "uk" in a:
        return speaker_ids.get('EN-BR', speaker_ids.get('EN-Default', list(speaker_ids.values())[0]))
    elif "india" in a or "indian" in a:
        # Fix: Use hyphen EN-INDIA instead of underscore EN_INDIA
        return speaker_ids.get('EN-INDIA', speaker_ids.get('EN-Default', list(speaker_ids.values())[0]))
    elif "american" in a or "us" in a:
        return speaker_ids.get('EN-US', speaker_ids.get('EN-Default', list(speaker_ids.values())[0]))
    else:
        # Default to EN-Default or first available
        return speaker_ids.get('EN-Default', list(speaker_ids.values())[0])

async def _synth_and_stream_local(conv_id: str, text: str, accent: str):
    """
    Locally deployed MeloTTS model version
    Input/output identical to _synth_and_stream_common
    
    Args:
        conv_id: Conversation ID
        text: Text to synthesize
        accent: Accent type (australia/british/india/american/chinese)
    """
    print(f"[DEBUG][melotts] ========== TTS Start ==========")
    print(f"[DEBUG][melotts] conv_id: {conv_id}")
    print(f"[DEBUG][melotts] text: '{text}'")
    print(f"[DEBUG][melotts] accent: {accent}")
    print(f"[DEBUG][melotts] text length: {len(text) if text else 0}")
    
    import io
    import numpy as np
    
    # Check for empty text
    if not text or not text.strip():
        print("[melotts] Skipping empty text")
        return
    
    try:
        import soundfile as sf
        print("[DEBUG][melotts] soundfile imported successfully")
    except ImportError as e:
        print(f"[DEBUG][melotts] soundfile import failed: {e}")
        raise ImportError("Need to install soundfile: pip install soundfile")
    
    # Determine language model based on accent
    accent_lower = (accent or "").lower()
    if "chinese" in accent_lower or "china" in accent_lower:
        language = 'ZH'
    else:
        language = 'EN'  # American, British, Australian, Indian all use EN model
    
    print(f"[DEBUG][melotts] Selected language model: {language}")
    
    # 1) Notify frontend to start
    print(f"[DEBUG][melotts] Preparing to send start message to channel")
    await channel.pub_tts_json(conv_id, {"type": "start", "mime": "audio/mpeg"})
    print(f"[DEBUG][melotts→ws] start message sent -> {conv_id}")
    
    try:
        # 2) Get model (use cache)
        print(f"[DEBUG][melotts] Starting to load model...")
        model, speaker_ids = _get_melotts_model(language)
        print(f"[DEBUG][melotts] Model loaded successfully, speaker_ids: {speaker_ids}")
        
        speaker_id = _accent_to_speaker_id(accent, speaker_ids, language)
        print(f"[DEBUG][melotts] Selected speaker_id: {speaker_id}")
        
        print(f"[melotts] Synthesizing speech: text='{text[:50]}...', accent={accent}, speaker_id={speaker_id}, language={language}")
        
        # 3) Generate audio in thread pool (avoid blocking event loop)
        print(f"[DEBUG][melotts] Preparing to synthesize audio in thread pool...")
        executor = _get_melotts_executor()
        loop = asyncio.get_event_loop()
        
        def synthesize():
            """Synchronous synthesis function executed in thread pool"""
            print(f"[DEBUG][melotts] Thread pool: Starting to call model.tts_to_file")
            audio = model.tts_to_file(
                text=text,
                speaker_id=speaker_id,
                output_path=None,  # Return numpy array instead of saving file
                speed=1.0,
                quiet=True  # Don't show progress bar
            )
            sample_rate = model.hps.data.sampling_rate
            print(f"[DEBUG][melotts] Thread pool: Audio synthesis complete, sample_rate={sample_rate}")
            return audio, sample_rate
        
        audio, sample_rate = await loop.run_in_executor(executor, synthesize)
        print(f"[DEBUG][melotts] Audio data received, shape={audio.shape if hasattr(audio, 'shape') else 'N/A'}")
        
        # 4) Convert to MP3 bytes (using pydub + ffmpeg)
        print(f"[DEBUG][melotts] Starting to convert to MP3 bytes...")
        audio = np.clip(audio, -1.0, 1.0)
        
        try:
            from pydub import AudioSegment
            
            # Convert to 16-bit PCM
            audio_int16 = (audio * 32767.0).astype(np.int16)
            
            # Create AudioSegment
            audio_segment = AudioSegment(
                audio_int16.tobytes(),
                frame_rate=sample_rate,
                sample_width=2,  # 16-bit = 2 bytes
                channels=1
            )
            
            # Export as MP3
            mp3_buffer = io.BytesIO()
            audio_segment.export(mp3_buffer, format="mp3", bitrate="128k")
            mp3_buffer.seek(0)
            audio_bytes = mp3_buffer.read()
            print(f"[DEBUG][melotts] MP3 conversion complete, total size: {len(audio_bytes)} bytes")
        except ImportError:
            # If pydub unavailable, fallback to WAV
            print(f"[DEBUG][melotts] pydub unavailable, falling back to WAV format...")
            audio = audio.astype(np.float32)
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, audio, sample_rate, format='WAV', subtype='PCM_16')
            wav_buffer.seek(0)
            audio_bytes = wav_buffer.read()
            print(f"[DEBUG][melotts] WAV conversion complete, total size: {len(audio_bytes)} bytes")
        
        # 5) Send audio data in chunks
        chunk_size = 8192
        got_any = False
        chunk_count = 0
        
        print(f"[DEBUG][melotts] Starting to send audio data in chunks, chunk_size={chunk_size}")
        for offset in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[offset:offset + chunk_size]
            if chunk:
                got_any = True
                chunk_count += 1
                await channel.pub_tts_bytes(conv_id, chunk)
                if chunk_count <= 3 or chunk_count % 10 == 0:  # Only print first few and every 10th
                    print(f"[DEBUG][melotts] Sent chunk #{chunk_count}, size={len(chunk)}")
            await asyncio.sleep(0)  # Yield control
        
        print(f"[DEBUG][melotts] Audio data sending complete!")
        print(f"[melotts] stream done, got_any={got_any}, total_chunks={chunk_count}, total_size={len(audio_bytes)} bytes")
        
    except Exception as e:
        print(f"[DEBUG][melotts] ❌ Error occurred: {e}")
        print(f"[DEBUG][melotts] Error type: {type(e).__name__}")
        import traceback
        print(f"[DEBUG][melotts] Full stack trace:")
        traceback.print_exc()
        raise
    finally:
        # 6) Notify frontend to end
        print(f"[DEBUG][melotts] Preparing to send stop message")
        await channel.pub_tts_json(conv_id, {"type": "stop"})
        print(f"[DEBUG][melotts→ws] stop message sent -> {conv_id}")
        print(f"[DEBUG][melotts] ========== TTS End ==========")

# =====================================================================


async def synth_and_stream_free(conv_id: str, text: str, accent: str):
    await _synth_and_stream_local(conv_id, text, accent)

async def synth_and_stream_paid(conv_id: str, text: str, accent: str):
    await _synth_and_stream_common(conv_id, text, accent)
