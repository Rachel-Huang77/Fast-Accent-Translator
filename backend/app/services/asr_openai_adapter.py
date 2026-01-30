"""
OpenAI Whisper API Adapter

Adapts existing OpenAI Whisper API calls to the new ASR interface
"""
import httpx
from typing import Optional
from .asr_base import ASRService, TranscriptionResult, TranscriptSegment, WordTimestamp
from ..config import settings


class OpenAIWhisperService(ASRService):
    """OpenAI Whisper API Service"""
    
    def __init__(self):
        self.api_key = settings.openai_api_key
        self.api_url = settings.whisper_api_url
        self.model = settings.whisper_model
    
    @property
    def name(self) -> str:
        return "OpenAI Whisper API"
    
    def is_available(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key)
    
    async def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = False
    ) -> TranscriptionResult:
        """
        Call OpenAI Whisper API for transcription
        
        Uses verbose_json format, returns segment-level timestamps
        
        Note: Does not use timestamp_granularities parameter, as it causes segments to be merged,
        affecting matching accuracy with diarization
        """
        if not self.is_available():
            raise RuntimeError(f"{self.name}: API key not configured")
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # Build request parameters (✅ Optimize accuracy)
        data = {
            "model": self.model,
            "response_format": "verbose_json",
            # ✅ High precision parameters
            "temperature": 0.0,  # 0 = most deterministic (most accurate, no randomness)
            "prompt": "Hello, hi, hey, good morning, how are you, I'm fine, thank you, and you, see you, bye.",  # ✅ Common conversation phrase examples to help Whisper understand context
        }
        
        if language:
            data["language"] = language
        
        # ❌ Do not use timestamp_granularities, as it merges segments, causing diarization matching to fail
        # if word_timestamps:
        #     data["timestamp_granularities"] = ["word", "segment"]
        
        # Send request
        async with httpx.AsyncClient(timeout=120) as client:
            with open(audio_path, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                resp = await client.post(self.api_url, headers=headers, data=data, files=files)
            resp.raise_for_status()
            result = resp.json()
        
        # Parse result
        full_text = (result.get("text") or "").strip()
        language_detected = result.get("language")
        duration = result.get("duration")
        
        # Parse segment information
        segments = []
        raw_segments = result.get("segments", [])
        
        if not raw_segments and full_text:
            # If no segment information, create a single segment
            segments.append(TranscriptSegment(
                text=full_text,
                start_sec=0.0,
                end_sec=duration or 0.0,
                words=None
            ))
        else:
            for seg in raw_segments:
                seg_text = seg.get("text", "").strip()
                seg_start = seg.get("start", 0.0)
                seg_end = seg.get("end", 0.0)
                
                # Parse word-level timestamps (if available)
                words = None
                if word_timestamps and "words" in seg:
                    words = [
                        WordTimestamp(
                            word=w.get("word", ""),
                            start_sec=w.get("start", 0.0),
                            end_sec=w.get("end", 0.0)
                        )
                        for w in seg.get("words", [])
                    ]
                
                segments.append(TranscriptSegment(
                    text=seg_text,
                    start_sec=seg_start,
                    end_sec=seg_end,
                    words=words
                ))
        
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            language=language_detected,
            duration_sec=duration
        )


# Global singleton (optional)
openai_whisper_service = OpenAIWhisperService()



