"""
Unit tests for services.asr_factory module.
Tests ASR service factory and transcription function.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.asr_factory import get_asr_service, transcribe_audio
from app.services.asr_base import TranscriptionResult


class TestASRFactory:
    """Tests for ASR service factory."""

    @patch('app.services.asr_factory.openai_whisper_service')
    def test_get_asr_service_returns_openai_service(self, mock_service):
        """get_asr_service should return OpenAI Whisper service."""
        mock_service.is_available.return_value = True
        mock_service.name = "OpenAI Whisper API"
        
        service = get_asr_service()
        
        assert service == mock_service
        mock_service.is_available.assert_called_once()

    @patch('app.services.asr_factory.openai_whisper_service')
    def test_get_asr_service_raises_when_unavailable(self, mock_service):
        """get_asr_service should raise RuntimeError when service unavailable."""
        mock_service.is_available.return_value = False
        
        with pytest.raises(RuntimeError, match="OpenAI Whisper API not available"):
            get_asr_service()

    @pytest.mark.asyncio
    @patch('app.services.asr_factory.get_asr_service')
    async def test_transcribe_audio_calls_service_transcribe(self, mock_get_service):
        """transcribe_audio should call service.transcribe with correct parameters."""
        mock_service = MagicMock()
        mock_result = TranscriptionResult(
            full_text="Test transcription",
            segments=[],
            language="en"
        )
        mock_service.transcribe = AsyncMock(return_value=mock_result)
        mock_get_service.return_value = mock_service
        
        result = await transcribe_audio("test.wav", language="en", word_timestamps=True)
        
        assert result == mock_result
        mock_service.transcribe.assert_called_once_with(
            audio_path="test.wav",
            language="en",
            word_timestamps=True
        )

