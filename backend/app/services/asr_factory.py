"""
ASR Service Factory

Uses OpenAI Whisper API for speech recognition
"""
from typing import Optional
from .asr_base import ASRService, TranscriptionResult
from .asr_openai_adapter import openai_whisper_service


def get_asr_service() -> ASRService:
    """
    Get ASR service
    
    Returns:
    - ASRService: OpenAI Whisper API service instance
    
    Note:
    - Need to configure OPENAI_API_KEY in .env
    """
    if not openai_whisper_service.is_available():
        raise RuntimeError(
            "OpenAI Whisper API not available. Please configure OPENAI_API_KEY in .env"
        )
    
    print(f"[ASR] Using {openai_whisper_service.name}")
    return openai_whisper_service


# Convenience function: directly transcribe audio
async def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    word_timestamps: bool = False
) -> TranscriptionResult:
    """
    Transcribe audio using OpenAI Whisper API
    
    Parameters:
    - audio_path: WAV file path
    - language: Optional language hint (e.g., "en", "zh")
    - word_timestamps: Whether to return word-level timestamps
    
    Returns:
    - TranscriptionResult: Transcription result
    """
    service = get_asr_service()
    return await service.transcribe(
        audio_path=audio_path,
        language=language,
        word_timestamps=word_timestamps
    )



