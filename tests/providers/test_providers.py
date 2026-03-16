"""Test cụ thể cho từng AI Provider — Mock API calls."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.providers.base import StreamChunk


class TestGeminiProvider:
    """Test GeminiProvider với mock google-generativeai SDK."""

    @patch("src.providers.gemini_provider.genai")
    def test_init(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key="test-key")
        mock_genai.configure.assert_called_once_with(api_key="test-key")
        assert provider.name == "gemini"
        assert provider.model == "gemini-1.5-flash"

    @patch("src.providers.gemini_provider.genai")
    def test_custom_model(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key="key", model="gemini-1.5-pro")
        assert provider.model == "gemini-1.5-pro"

    @patch("src.providers.gemini_provider.genai")
    def test_supported_models(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider

        provider = GeminiProvider(api_key="key")
        assert "gemini-1.5-flash" in provider.supported_models
        assert "gemini-1.5-pro" in provider.supported_models

    @patch("src.providers.gemini_provider.genai")
    def test_summarize_streaming(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider

        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.text = "Đây là "
        mock_chunk2 = MagicMock()
        mock_chunk2.text = "tóm tắt."

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.__iter__ = lambda self: iter([mock_chunk1, mock_chunk2])
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 100
        mock_usage.candidates_token_count = 50
        mock_response.usage_metadata = mock_usage
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        provider = GeminiProvider(api_key="key")
        chunks = list(provider.summarize("Test content"))

        # Phải có ít nhất text chunks + 1 final chunk
        text_chunks = [c for c in chunks if c.text]
        final_chunks = [c for c in chunks if c.is_final]

        assert len(text_chunks) >= 1
        assert len(final_chunks) == 1
        assert final_chunks[0].input_tokens == 100
        assert final_chunks[0].output_tokens == 50

    @patch("src.providers.gemini_provider.genai")
    def test_validate_key_success(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider

        mock_genai.list_models.return_value = iter([MagicMock()])

        provider = GeminiProvider(api_key="valid-key")
        assert provider.validate_key() is True

    @patch("src.providers.gemini_provider.genai")
    def test_validate_key_failure(self, mock_genai) -> None:
        from src.providers.gemini_provider import GeminiProvider
        from google.api_core.exceptions import PermissionDenied

        mock_genai.list_models.side_effect = PermissionDenied("Invalid key")

        provider = GeminiProvider(api_key="bad-key")
        assert provider.validate_key() is False


class TestOpenAIProvider:
    """Test OpenAIProvider với mock openai SDK."""

    @patch("src.providers.openai_provider.OpenAI")
    def test_init(self, mock_openai_cls) -> None:
        from src.providers.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-test")
        mock_openai_cls.assert_called_once_with(api_key="sk-test")
        assert provider.name == "openai"
        assert provider.model == "gpt-4o-mini"

    @patch("src.providers.openai_provider.OpenAI")
    def test_summarize_streaming(self, mock_openai_cls) -> None:
        from src.providers.openai_provider import OpenAIProvider

        # Mock streaming response
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Tóm tắt "
        chunk1.usage = None

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "nội dung."
        chunk2.usage = None

        chunk_final = MagicMock()
        chunk_final.choices = []
        chunk_final.usage = MagicMock()
        chunk_final.usage.prompt_tokens = 200
        chunk_final.usage.completion_tokens = 80

        mock_client.chat.completions.create.return_value = iter(
            [chunk1, chunk2, chunk_final]
        )

        provider = OpenAIProvider(api_key="sk-test")
        chunks = list(provider.summarize("Test content"))

        text_chunks = [c for c in chunks if c.text]
        final_chunks = [c for c in chunks if c.is_final]

        assert len(text_chunks) == 2
        assert len(final_chunks) == 1
        assert final_chunks[0].input_tokens == 200

    @patch("src.providers.openai_provider.OpenAI")
    def test_validate_key_success(self, mock_openai_cls) -> None:
        from src.providers.openai_provider import OpenAIProvider

        provider = OpenAIProvider(api_key="sk-valid")
        assert provider.validate_key() is True

    @patch("src.providers.openai_provider.OpenAI")
    def test_validate_key_failure(self, mock_openai_cls) -> None:
        from src.providers.openai_provider import OpenAIProvider
        from openai import AuthenticationError

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.models.list.side_effect = AuthenticationError(
            message="Invalid key",
            response=MagicMock(status_code=401),
            body=None,
        )

        provider = OpenAIProvider(api_key="sk-bad")
        assert provider.validate_key() is False


class TestClaudeProvider:
    """Test ClaudeProvider với mock anthropic SDK."""

    @patch("src.providers.claude_provider.anthropic.Anthropic")
    def test_init(self, mock_anthropic_cls) -> None:
        from src.providers.claude_provider import ClaudeProvider

        provider = ClaudeProvider(api_key="sk-ant-test")
        mock_anthropic_cls.assert_called_once_with(api_key="sk-ant-test")
        assert provider.name == "claude"
        assert provider.model == "claude-haiku-4-5-20251001"

    @patch("src.providers.claude_provider.anthropic.Anthropic")
    def test_summarize_streaming(self, mock_anthropic_cls) -> None:
        from src.providers.claude_provider import ClaudeProvider

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Mock stream context manager
        mock_stream = MagicMock()
        mock_stream.text_stream = iter(["Tóm tắt ", "nội dung."])

        mock_final = MagicMock()
        mock_final.usage.input_tokens = 150
        mock_final.usage.output_tokens = 60
        mock_stream.get_final_message.return_value = mock_final

        mock_client.messages.stream.return_value.__enter__ = MagicMock(
            return_value=mock_stream
        )
        mock_client.messages.stream.return_value.__exit__ = MagicMock(
            return_value=False
        )

        provider = ClaudeProvider(api_key="sk-ant-test")
        chunks = list(provider.summarize("Test content"))

        text_chunks = [c for c in chunks if c.text]
        final_chunks = [c for c in chunks if c.is_final]

        assert len(text_chunks) == 2
        assert len(final_chunks) == 1
        assert final_chunks[0].input_tokens == 150

    @patch("src.providers.claude_provider.anthropic.Anthropic")
    def test_validate_key_success(self, mock_anthropic_cls) -> None:
        from src.providers.claude_provider import ClaudeProvider

        provider = ClaudeProvider(api_key="sk-ant-valid")
        assert provider.validate_key() is True

    @patch("src.providers.claude_provider.anthropic.Anthropic")
    def test_validate_key_failure(self, mock_anthropic_cls) -> None:
        from src.providers.claude_provider import ClaudeProvider
        import anthropic

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {}

        mock_client.messages.count_tokens.side_effect = anthropic.AuthenticationError(
            message="Invalid key",
            response=mock_response,
            body=None,
        )

        provider = ClaudeProvider(api_key="sk-ant-bad")
        assert provider.validate_key() is False
