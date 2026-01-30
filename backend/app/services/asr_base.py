"""
ASR Service Abstract Interface

Provides unified interface for different ASR providers (OpenAI Whisper API / Local Whisper / Others).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class WordTimestamp:
    """Word-level timestamp"""
    word: str
    start_sec: float  # Relative time (seconds), from audio start
    end_sec: float
    
    @property
    def start_ms(self) -> int:
        """Convert to milliseconds"""
        return int(self.start_sec * 1000)
    
    @property
    def end_ms(self) -> int:
        return int(self.end_sec * 1000)


@dataclass
class TranscriptSegment:
    """
    Transcription segment (sentence/segment level)
    
    Note: Timestamps here are relative time (from audio start), not Unix timestamps
    """
    text: str
    start_sec: float  # Relative time (seconds)
    end_sec: float
    words: Optional[List[WordTimestamp]] = None  # Optional word-level timestamps
    
    @property
    def start_ms(self) -> int:
        """Convert to milliseconds"""
        return int(self.start_sec * 1000)
    
    @property
    def end_ms(self) -> int:
        return int(self.end_sec * 1000)
    
    def __repr__(self):
        return f"TranscriptSegment(text='{self.text[:30]}...', start={self.start_sec:.2f}s, end={self.end_sec:.2f}s)"


@dataclass
class TranscriptionResult:
    """Complete transcription result"""
    full_text: str  # Full text (for TTS)
    segments: List[TranscriptSegment]  # Segmented text (for display and speaker matching)
    language: Optional[str] = None  # Detected language
    duration_sec: Optional[float] = None  # Total audio duration


class ASRService(ABC):
    """ASR Service Abstract Base Class"""
    
    @abstractmethod
    async def transcribe(
        self, 
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = False
    ) -> TranscriptionResult:
        """
        Transcribe audio file
        
        Parameters:
        - audio_path: WAV file path (16kHz mono)
        - language: Optional language hint (e.g., "en", "zh")
        - word_timestamps: Whether to return word-level timestamps
        
        Returns:
        - TranscriptionResult: Contains full text and segment information
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if service is available"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Service name (e.g., "OpenAI Whisper API")"""
        pass



