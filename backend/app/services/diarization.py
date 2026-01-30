# backend/app/services/diarization.py
"""
Speaker Diarization Service
Uses pyannote.audio pretrained models, no need to train yourself
"""
import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class DiarizationService:
    """
    Speaker Diarization Service
    
    Features:
    - Automatically identify different speakers in audio
    - Return timestamps + speaker ID
    - Support 3-person scenarios (configurable)
    """
    
    def __init__(self):
        self.enabled = os.getenv("ENABLE_DIARIZATION", "true").lower() == "true"
        self.model_name = os.getenv("DIARIZATION_MODEL", "pyannote/speaker-diarization-3.1")
        self.pipeline = None
        
        if self.enabled:
            try:
                hf_token = os.getenv("HF_TOKEN")
                if not hf_token:
                    logger.warning(
                        "[Diarization] HF_TOKEN not set. "
                        "Get one from https://huggingface.co/settings/tokens"
                    )
                    self.enabled = False
                    return
                
                logger.info(f"[Diarization] Loading model: {self.model_name}")
                
                # Lazy import (avoid requiring pyannote installation at startup)
                from pyannote.audio import Pipeline
                
                # ✅ New huggingface_hub uses token parameter (compatible with old use_auth_token)
                try:
                    # Try new API first (token)
                    self.pipeline = Pipeline.from_pretrained(
                        self.model_name,
                        token=hf_token
                    )
                except TypeError:
                    # Fallback to old API (use_auth_token)
                    self.pipeline = Pipeline.from_pretrained(
                        self.model_name,
                        use_auth_token=hf_token
                    )
                
                logger.info("[Diarization] Model loaded successfully ✓")
                
            except ImportError as e:
                logger.error(
                    "[Diarization] pyannote.audio not installed. "
                    "Run: pip install pyannote.audio torch torchaudio"
                )
                self.enabled = False
            except Exception as e:
                logger.error(f"[Diarization] Failed to load model: {e}")
                self.enabled = False
        else:
            logger.info("[Diarization] Service disabled by config")
    
    async def analyze_speakers(
        self, 
        audio_path: str, 
        num_speakers: Optional[int] = None
    ) -> List[Dict]:
        """
        Analyze speakers in audio
        
        Parameters:
        - audio_path: WAV file path (16kHz mono)
        - num_speakers: Expected number of speakers (None=auto-detect, recommended: 3)
        
        Returns:
        [
            {"start_ms": 0, "end_ms": 3200, "speaker_id": "SPEAKER_00"},
            {"start_ms": 3200, "end_ms": 6100, "speaker_id": "SPEAKER_01"},
            ...
        ]
        """
        if not self.enabled or not self.pipeline:
            logger.warning("[Diarization] Service not available, returning empty segments")
            return []
        
        try:
            logger.info(
                f"[Diarization] Analyzing {audio_path}, "
                f"num_speakers={num_speakers if num_speakers else 'auto-detect'}"
            )
            
            # Execute diarization (may take several seconds to tens of seconds)
            diarization = self.pipeline(
                audio_path,
                num_speakers=num_speakers
            )
            
            # Convert to our required format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "start_ms": int(turn.start * 1000),  # seconds → milliseconds
                    "end_ms": int(turn.end * 1000),
                    "speaker_id": speaker  # "SPEAKER_00", "SPEAKER_01", ...
                })
            
            # Count number of speakers
            speaker_count = len(set(s["speaker_id"] for s in segments))
            logger.info(
                f"[Diarization] ✓ Detected {speaker_count} speakers, "
                f"{len(segments)} segments"
            )
            
            return segments
        
        except Exception as e:
            logger.error(f"[Diarization] Analysis failed: {e}", exc_info=True)
            return []
    
    def is_available(self) -> bool:
        """Check if service is available"""
        return self.enabled and self.pipeline is not None


# Global singleton
diarization_service = DiarizationService()

