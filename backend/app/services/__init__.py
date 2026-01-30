"""
Services Module

Provides interfaces for various external services:
- ASR (Automatic Speech Recognition): OpenAI Whisper API
- TTS (Text-to-Speech): ElevenLabs
- Diarization (Speaker Recognition): pyannote.audio
"""

# ASR service (new interface)
from .asr_base import (
    ASRService,
    TranscriptionResult,
    TranscriptSegment,
    WordTimestamp,
)
from .asr_factory import (
    get_asr_service,
    transcribe_audio,
)
from .asr_openai_adapter import openai_whisper_service

# ASR utility functions (audio conversion)
from .asr_openai import webm_to_wav_16k_mono

# TTS service
from .tts_elevenlabs import (
    synth_and_stream_free,
    synth_and_stream_paid,
)

# Diarization service
from .diarization import diarization_service

__all__ = [
    # ASR - service interface
    "ASRService",
    "TranscriptionResult",
    "TranscriptSegment",
    "WordTimestamp",
    "get_asr_service",
    "transcribe_audio",
    "openai_whisper_service",
    # ASR - utility functions
    "webm_to_wav_16k_mono",
    # TTS
    "synth_and_stream_free",
    "synth_and_stream_paid",
    # Diarization
    "diarization_service",
]



