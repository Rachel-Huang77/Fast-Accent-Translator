"""
Unit tests for services.diarization_matcher module.
Tests sentence alignment, speaker assignment, and text similarity.
"""
import pytest
from app.services.diarization_matcher import (
    normalize_text,
    text_similarity,
    align_sentences_with_whisper,
    assign_speakers_to_sentences,
    analyze_speaker_changes
)


class TestTextNormalization:
    """Tests for text normalization."""

    def test_normalize_text_lowercase(self):
        """normalize_text should convert to lowercase."""
        assert normalize_text("Hello World") == "hello world"

    def test_normalize_text_removes_punctuation(self):
        """normalize_text should remove punctuation."""
        assert normalize_text("Hello, world!") == "hello world"

    def test_normalize_text_removes_extra_spaces(self):
        """normalize_text should remove extra spaces."""
        assert normalize_text("Hello    world") == "hello world"

    def test_normalize_text_handles_empty(self):
        """normalize_text should handle empty string."""
        assert normalize_text("") == ""


class TestTextSimilarity:
    """Tests for text similarity calculation."""

    def test_text_similarity_identical_texts(self):
        """text_similarity should return 1.0 for identical texts."""
        assert text_similarity("Hello world", "Hello world") == 1.0

    def test_text_similarity_different_texts(self):
        """text_similarity should return low value for different texts."""
        similarity = text_similarity("Hello world", "Goodbye universe")
        assert 0.0 <= similarity < 0.5

    def test_text_similarity_case_insensitive(self):
        """text_similarity should be case insensitive."""
        assert text_similarity("Hello", "HELLO") == 1.0

    def test_text_similarity_ignores_punctuation(self):
        """text_similarity should ignore punctuation."""
        sim1 = text_similarity("Hello, world!", "Hello world")
        assert sim1 > 0.9


class TestSentenceAlignment:
    """Tests for sentence alignment with Whisper segments."""

    def test_align_sentences_with_whisper_basic(self):
        """align_sentences_with_whisper should align sentences with segments."""
        gpt_sentences = [
            {"text": "Hello world", "speaker": "A"},
            {"text": "How are you", "speaker": "B"}
        ]
        whisper_segments = [
            {"start": 0.0, "end": 1.5, "text": "Hello world"},
            {"start": 1.5, "end": 3.0, "text": "How are you"}
        ]
        
        result = align_sentences_with_whisper(gpt_sentences, whisper_segments)
        
        assert len(result) == 2
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 1.5
        assert result[0]["text"] == "Hello world"
        assert result[0]["gpt_speaker"] == "A"

    def test_align_sentences_with_whisper_empty_input(self):
        """align_sentences_with_whisper should handle empty input."""
        assert align_sentences_with_whisper([], []) == []
        assert align_sentences_with_whisper([{"text": "Hello"}], []) == []


class TestSpeakerAssignment:
    """Tests for speaker assignment to sentences."""

    def test_assign_speakers_to_sentences_basic(self):
        """assign_speakers_to_sentences should assign speakers based on time overlap."""
        sentences = [
            {"start": 0.0, "end": 2.0, "text": "Hello"},
            {"start": 2.0, "end": 4.0, "text": "Hi there"}
        ]
        diar_segments = [
            {"start": 0.0, "end": 2.0, "speaker_id": "SPEAKER_00"},
            {"start": 2.0, "end": 4.0, "speaker_id": "SPEAKER_01"}
        ]
        
        result = assign_speakers_to_sentences(sentences, diar_segments)
        
        assert len(result) == 2
        assert result[0]["speaker_id"] == "SPEAKER_00"
        assert result[1]["speaker_id"] == "SPEAKER_01"

    def test_assign_speakers_to_sentences_no_overlap(self):
        """assign_speakers_to_sentences should handle no overlap."""
        sentences = [{"start": 0.0, "end": 1.0, "text": "Hello"}]
        diar_segments = [{"start": 10.0, "end": 12.0, "speaker_id": "SPEAKER_00"}]
        
        result = assign_speakers_to_sentences(sentences, diar_segments)
        
        # Should assign first available speaker or default
        assert len(result) == 1
        assert "speaker_id" in result[0]


class TestSpeakerChangeAnalysis:
    """Tests for speaker change analysis."""

    def test_analyze_speaker_changes_counts_changes(self):
        """analyze_speaker_changes should count speaker changes."""
        labeled_sentences = [
            {"text": "Hello", "speaker_id": "SPEAKER_00"},
            {"text": "Hi", "speaker_id": "SPEAKER_01"},
            {"text": "How are you", "speaker_id": "SPEAKER_01"},
            {"text": "I'm fine", "speaker_id": "SPEAKER_00"}
        ]
        
        result = analyze_speaker_changes(labeled_sentences)
        
        assert "total_sentences" in result
        assert "speakers" in result  # Function returns "speakers" not "total_speakers"
        assert "speaker_changes" in result
        assert result["total_sentences"] == 4
        assert result["speaker_changes"] >= 2  # At least 2 changes
        assert len(result["speakers"]) == 2  # Should have 2 unique speakers

