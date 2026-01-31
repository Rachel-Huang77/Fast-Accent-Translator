# app/config.py
import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class Settings(BaseModel):
    # General app settings
    APP_NAME: str = "Fast Accent Translator API"
    env: str = os.getenv("ENV", "dev")
    
    # Host & Port settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # CORS origins for frontend
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # production frontend (Vercel)
        "https://fast-accent-translator.vercel.app"
    ]
    
    # OpenAI Whisper API Settings (for ASR)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    whisper_api_url: str = os.getenv("WHISPER_API_URL", "https://api.openai.com/v1/audio/transcriptions")
    whisper_model: str = os.getenv("WHISPER_MODEL", "whisper-1")
    
    # Diarization Settings
    # ⚠️ Speaker recognition accuracy is not ideal, disabled by default (code retained, can be enabled anytime)
    enable_diarization: bool = os.getenv("ENABLE_DIARIZATION", "false").lower() in ("true", "1", "yes")
    
    # GPT Post-Processing Settings
    # ✅ Use GPT for formatting and sentence segmentation (recommended)
    enable_gpt_formatting: bool = os.getenv("ENABLE_GPT_FORMATTING", "true").lower() in ("true", "1", "yes")
    gpt_model: str = os.getenv("GPT_MODEL", "gpt-4o-mini")  # gpt-3.5-turbo, gpt-4, gpt-4o-mini
    
    # ElevenLabs API Settings (for TTS)
    eleven_api_key: str | None = os.getenv("ELEVENLABS_API_KEY")
    eleven_api_base: str = os.getenv("ELEVENLABS_API_URL", "https://api.elevenlabs.io/v1")
    default_voice_id: str = os.getenv("DEFAULT_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    
    # Voice Mapping for accents
    # ✅ Use default Voice ID when not set in .env (ElevenLabs preset voices)
    voice_id_american: str = os.getenv("VOICE_ID_AMERICAN", "EXAVITQu4vr4xnSDxMaL")
    voice_id_australia: str = os.getenv("VOICE_ID_AUSTRALIA", "IKne3meq5aSn9XLyUdCD")
    voice_id_british: str = os.getenv("VOICE_ID_BRITISH", "JBFqnCBsd6RMkjVDRZzb")
    voice_id_chinese: str = os.getenv("VOICE_ID_CHINESE", "hkfHEbBvdQFNX4uWHqRF")
    voice_id_india: str = os.getenv("VOICE_ID_INDIA", "kL06KYMvPY56NluIQ72m")

settings = Settings()  # Instantiate configuration
