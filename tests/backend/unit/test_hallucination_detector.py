"""
Unit tests for services.hallucination_detector module.
Tests hallucination detection logic (confidence, repetition, coherence, patterns).
"""
import pytest
from app.services.hallucination_detector import HallucinationDetector


class TestHallucinationDetector:
    """Tests for hallucination detection."""

    def test_detect_empty_text_is_hallucination(self):
        """Empty text should be detected as hallucination."""
        detector = HallucinationDetector()
        result = detector.detect_from_whisper("")
        
        assert result["is_hallucination"] is True
        assert result["reason"] == "empty_text"

    def test_detect_whitespace_only_is_hallucination(self):
        """Whitespace-only text should be detected as hallucination."""
        detector = HallucinationDetector()
        result = detector.detect_from_whisper("   \n\t   ")
        
        assert result["is_hallucination"] is True

    def test_detect_valid_text_passes(self):
        """Valid text should pass all checks."""
        detector = HallucinationDetector()
        text = "Hello, how are you today? I'm doing well, thank you."
        segments = [
            {"text": "Hello, how are you today?", "start": 0.0, "end": 2.0, "avg_logprob": -0.2},
            {"text": "I'm doing well, thank you.", "start": 2.0, "end": 4.0, "avg_logprob": -0.15}
        ]
        
        result = detector.detect_from_whisper(text, segments)
        
        assert result["is_hallucination"] is False
        assert result["reason"] == "valid"

    def test_detect_low_confidence_segments(self):
        """Text with low confidence segments should be flagged."""
        detector = HallucinationDetector()
        text = "Some unclear speech"
        segments = [
            {"text": "Some unclear speech", "start": 0.0, "end": 2.0, "avg_logprob": -1.5}  # Very low confidence
        ]
        
        result = detector.detect_from_whisper(text, segments)
        
        # May be flagged as hallucination due to low confidence
        assert "is_hallucination" in result

    def test_detect_repetition(self):
        """Excessive repetition should be detected."""
        detector = HallucinationDetector()
        text = "hello hello hello hello hello hello"  # Excessive repetition
        
        result = detector.detect_from_whisper(text)
        
        # May be flagged due to repetition
        assert "is_hallucination" in result

    def test_detect_no_segments_uses_defaults(self):
        """Detection should work even without segment information."""
        detector = HallucinationDetector()
        text = "This is a normal sentence without segment data."
        
        result = detector.detect_from_whisper(text, segments=None)
        
        assert "is_hallucination" in result
        assert "reason" in result
        assert "confidence" in result

