import tempfile, os
import ffmpeg
import httpx
from ..config import settings

def webm_to_wav_16k_mono(webm_path: str) -> str:
    """Convert webm/opus to 16k mono wav, return wav path (caller responsible for deletion)"""
    # Validate input file
    if not os.path.exists(webm_path):
        raise FileNotFoundError(f"Input file not found: {webm_path}")
    
    file_size = os.path.getsize(webm_path)
    if file_size == 0:
        raise ValueError(f"Input file is empty: {webm_path}")
    
    print(f"[ffmpeg] Converting {webm_path} ({file_size} bytes) to WAV...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
        try:
            (
                ffmpeg
                .input(webm_path)
                # ❌ Removed audio filtering (may introduce distortion, affecting Whisper recognition)
                .output(
                    wav_file.name, 
                    ac=1,           # Mono
                    ar="16000",     # 16kHz sample rate (Whisper recommended)
                    format="wav",
                    acodec="pcm_s16le",  # 16-bit PCM (lossless)
                    loglevel="error"     # Only show errors
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # ✅ Validate converted WAV file
            wav_size = os.path.getsize(wav_file.name)
            if wav_size == 0:
                raise ValueError(f"Converted WAV file is empty: {wav_file.name}")
            
            # Check WAV file header (should be "RIFF")
            with open(wav_file.name, "rb") as f:
                wav_header = f.read(4)
                if wav_header != b'RIFF':
                    raise ValueError(f"Invalid WAV file header: {wav_header.hex()}")
            
            print(f"[ffmpeg] Conversion successful: {wav_file.name} ({wav_size} bytes)")
            return wav_file.name
        except ffmpeg.Error as e:
            # Print detailed error information
            print(f"[ffmpeg] ERROR converting {webm_path}:")
            print(f"[ffmpeg] stdout: {e.stdout.decode('utf-8', errors='ignore') if e.stdout else 'N/A'}")
            print(f"[ffmpeg] stderr: {e.stderr.decode('utf-8', errors='ignore') if e.stderr else 'N/A'}")
            # Clean up failed output file
            if os.path.exists(wav_file.name):
                try:
                    os.unlink(wav_file.name)
                except:
                    pass
            raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode('utf-8', errors='ignore')[:200] if e.stderr else 'Unknown error'}")

async def transcribe_wav_via_url(wav_path: str) -> str:
    """
    Call ASR via HTTP direct connection to WHISPER_API_URL:
      POST multipart/form-data:
        - model=settings.whisper_model
        - file=@wav (audio/wav)
        - response_format=verbose_json
      Header: Authorization: Bearer OPENAI_API_KEY
    """
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    data = {
        "model": settings.whisper_model,
        "response_format": "verbose_json",
    }

    async with httpx.AsyncClient(timeout=120) as client:
        with open(wav_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            resp = await client.post(settings.whisper_api_url, headers=headers, data=data, files=files)
        resp.raise_for_status()
        js = resp.json()
        return (js.get("text") or "").strip()
