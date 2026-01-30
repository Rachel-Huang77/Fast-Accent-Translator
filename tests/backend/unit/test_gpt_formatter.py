"""
Unit tests for services.gpt_formatter module.
Tests GPT formatting, fallback logic, and error handling.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.gpt_formatter import GPTFormatterService


class TestGPTFormatterFallback:
    """Tests for fallback logic when GPT is unavailable."""

    def test_simple_split_basic_sentences(self):
        """_simple_split should split text by punctuation."""
        formatter = GPTFormatterService()
        text = "Hello world. How are you? I'm fine!"
        result = formatter._simple_split(text)
        
        assert len(result) == 3
        assert result[0]["text"] == "Hello world"
        assert result[1]["text"] == "How are you"
        assert result[2]["text"] == "I'm fine"

    def test_simple_split_assigns_speakers_alternating(self):
        """_simple_split should assign speakers A/B alternating."""
        formatter = GPTFormatterService()
        text = "First sentence. Second sentence. Third sentence."
        result = formatter._simple_split(text)
        
        assert result[0]["speaker"] == "A"
        assert result[1]["speaker"] == "B"
        assert result[2]["speaker"] == "A"

    def test_simple_split_empty_text(self):
        """_simple_split should handle empty text."""
        formatter = GPTFormatterService()
        result = formatter._simple_split("")
        assert result == []

    def test_simple_split_whitespace_only(self):
        """_simple_split should handle whitespace-only text."""
        formatter = GPTFormatterService()
        result = formatter._simple_split("   \n\t   ")
        assert result == []

    @pytest.mark.asyncio
    async def test_format_conversation_fallback_when_gpt_unavailable(self):
        """format_conversation should use fallback when GPT unavailable."""
        formatter = GPTFormatterService()
        # Mock is_available to return False
        with patch.object(formatter, 'is_available', return_value=False):
            text = "Hello. How are you?"
            result = await formatter.format_conversation(text)
            
            # Should use simple split
            assert len(result) == 2
            assert result[0]["text"] == "Hello"
            assert result[1]["text"] == "How are you"

    @pytest.mark.asyncio
    async def test_format_conversation_fallback_on_error(self):
        """format_conversation should fallback to simple_split on GPT error."""
        formatter = GPTFormatterService()
        text = "Test text. Another sentence."
        
        # Mock is_available to return True, but API call fails
        with patch.object(formatter, 'is_available', return_value=True), \
             patch('httpx.AsyncClient') as mock_client:
            # Simulate API error
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("API Error")
            
            result = await formatter.format_conversation(text)
            
            # Should fallback to simple split
            assert len(result) >= 1
            assert all("text" in item and "speaker" in item for item in result)

    @pytest.mark.asyncio
    async def test_format_conversation_with_comparison_fallback(self):
        """format_conversation_with_comparison should use fallback when GPT unavailable."""
        formatter = GPTFormatterService()
        webspeech = "Hello from webspeech"
        whisper = "Hello from whisper"
        
        with patch.object(formatter, 'is_available', return_value=False):
            result = await formatter.format_conversation_with_comparison(webspeech, whisper)
            
            # Should use simple split on whisper text
            assert "sentences" in result
            assert len(result["sentences"]) > 0


class TestGPTFormatterAPI:
    """Tests for GPT API integration (mocked)."""

    @pytest.mark.asyncio
    async def test_format_conversation_calls_gpt_api(self):
        """format_conversation should call GPT API when available."""
        formatter = GPTFormatterService()
        text = "Hello world"
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": '{"sentences": [{"text": "Hello world", "speaker": "A"}]}'
                }
            }]
        }
        
        with patch.object(formatter, 'is_available', return_value=True), \
             patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: mock_response,
                    raise_for_status=MagicMock()
                )
            )
            
            result = await formatter.format_conversation(text)
            
            assert len(result) == 1
            assert result[0]["text"] == "Hello world"
            assert result[0]["speaker"] == "A"

    @pytest.mark.asyncio
    async def test_format_conversation_handles_invalid_json(self):
        """format_conversation should fallback on invalid JSON response."""
        formatter = GPTFormatterService()
        text = "Test text"
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Invalid JSON response"
                }
            }]
        }
        
        with patch.object(formatter, 'is_available', return_value=True), \
             patch('httpx.AsyncClient') as mock_client, \
             patch('json.loads', side_effect=ValueError("Invalid JSON")):
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=MagicMock(
                    status_code=200,
                    json=lambda: mock_response,
                    raise_for_status=MagicMock()
                )
            )
            
            # Should fallback to simple split
            result = await formatter.format_conversation(text)
            assert len(result) >= 1

