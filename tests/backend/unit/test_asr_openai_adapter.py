"""
Unit tests for services.asr_openai_adapter module.
Tests OpenAI Whisper API adapter (parameter construction, error handling).
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.asr_openai_adapter import OpenAIWhisperService


class TestOpenAIWhisperAdapter:
    """Tests for OpenAI Whisper API adapter."""

    def test_is_available_with_api_key(self):
        """is_available should return True when API key is set."""
        with patch('app.services.asr_openai_adapter.settings') as mock_settings:
            mock_settings.openai_api_key = "test-key-123"
            service = OpenAIWhisperService()
            assert service.is_available() is True

    def test_is_available_without_api_key(self):
        """is_available should return False when API key is missing."""
        with patch('app.services.asr_openai_adapter.settings') as mock_settings:
            mock_settings.openai_api_key = None
            service = OpenAIWhisperService()
            assert service.is_available() is False

    @pytest.mark.asyncio
    async def test_transcribe_calls_openai_api(self):
        """transcribe should call OpenAI API with correct parameters."""
        mock_json_response = {
            "text": "Hello world",
            "language": "en",
            "duration": 2.0,
            "segments": [
                {"text": "Hello world", "start": 0.0, "end": 2.0}
            ]
        }
        
        with patch('app.services.asr_openai_adapter.settings') as mock_settings, \
             patch('httpx.AsyncClient') as mock_client_class:
            mock_settings.openai_api_key = "test-key"
            mock_settings.whisper_api_url = "https://api.openai.com/v1/audio/transcriptions"
            mock_settings.whisper_model = "whisper-1"
            
            mock_response = MagicMock()
            mock_response.json.return_value = mock_json_response
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            # Mock file open
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                service = OpenAIWhisperService()
                result = await service.transcribe(
                    audio_path="test.wav",
                    language="en",
                    word_timestamps=False
                )
                
                assert result.full_text == "Hello world"
                assert len(result.segments) == 1

    @pytest.mark.asyncio
    async def test_transcribe_handles_api_error(self):
        """transcribe should handle API errors gracefully."""
        with patch('app.services.asr_openai_adapter.settings') as mock_settings, \
             patch('httpx.AsyncClient') as mock_client_class:
            mock_settings.openai_api_key = "test-key"
            mock_settings.whisper_api_url = "https://api.openai.com/v1/audio/transcriptions"
            mock_settings.whisper_model = "whisper-1"
            
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_client_class.return_value = mock_client
            
            with patch('builtins.open', create=True):
                service = OpenAIWhisperService()
                with pytest.raises(Exception, match="API Error"):
                    await service.transcribe(
                        audio_path="test.wav",
                        language="en"
                    )

    @pytest.mark.asyncio
    async def test_transcribe_includes_temperature_parameter(self):
        """transcribe should include temperature=0.0 for determinism."""
        mock_json_response = {
            "text": "Test",
            "language": "en",
            "duration": 1.0,
            "segments": []
        }
        
        with patch('app.services.asr_openai_adapter.settings') as mock_settings, \
             patch('httpx.AsyncClient') as mock_client_class:
            mock_settings.openai_api_key = "test-key"
            mock_settings.whisper_api_url = "https://api.openai.com/v1/audio/transcriptions"
            mock_settings.whisper_model = "whisper-1"
            
            mock_response = MagicMock()
            mock_response.json.return_value = mock_json_response
            mock_response.raise_for_status = MagicMock()
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value.post = mock_post
            mock_client_class.return_value = mock_client
            
            with patch('builtins.open', create=True):
                service = OpenAIWhisperService()
                await service.transcribe(
                    audio_path="test.wav",
                    language="en"
                )
                
                # Check that temperature is included in data parameter
                call_args = mock_post.call_args
                assert call_args is not None
                data = call_args[1].get("data", {})
                assert data.get("temperature") == 0.0

