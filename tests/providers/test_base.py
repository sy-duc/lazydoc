"""Test BaseProvider — Kiểm tra abstract interface và prompt builders."""

import pytest

from src.providers.base import AIResponse, BaseProvider, StreamChunk


# --- Concrete implementation cho testing ---

class MockProvider(BaseProvider):
    """Provider giả để test abstract interface."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model-v1"

    @property
    def supported_models(self) -> list[str]:
        return ["mock-model-v1", "mock-model-v2"]

    def summarize(self, content, system_prompt=None):
        sys_p, user_p = self._build_summarize_prompt(content, system_prompt)
        yield StreamChunk(text=f"Summary: {content[:20]}", is_final=True)

    def translate(self, content, target_lang, source_lang=None,
                  domain=None, style=None, context=None, glossary=None):
        sys_p, user_p = self._build_translate_prompt(
            content, target_lang, source_lang, domain, style, context, glossary
        )
        yield StreamChunk(text=f"Translated: {content[:20]}", is_final=True)

    def describe_image(self, image_data, prompt=None):
        yield StreamChunk(text="Image description", is_final=True)

    def describe_images_batch(self, images, prompt=None):
        yield StreamChunk(text="Batch description", is_final=True)

    def validate_key(self):
        return True


# --- Tests ---

class TestStreamChunk:
    """Test StreamChunk dataclass."""

    def test_default_values(self) -> None:
        chunk = StreamChunk()
        assert chunk.text == ""
        assert chunk.input_tokens == 0
        assert chunk.output_tokens == 0
        assert chunk.is_final is False

    def test_with_values(self) -> None:
        chunk = StreamChunk(text="hello", input_tokens=10, output_tokens=5, is_final=True)
        assert chunk.text == "hello"
        assert chunk.input_tokens == 10
        assert chunk.output_tokens == 5
        assert chunk.is_final is True


class TestAIResponse:
    """Test AIResponse dataclass."""

    def test_default_values(self) -> None:
        resp = AIResponse()
        assert resp.text == ""
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.model == ""


class TestBaseProvider:
    """Test BaseProvider abstract interface."""

    def test_init_with_default_model(self) -> None:
        provider = MockProvider(api_key="test-key")
        assert provider.model == "mock-model-v1"
        assert provider.name == "mock"

    def test_init_with_custom_model(self) -> None:
        provider = MockProvider(api_key="test-key", model="mock-model-v2")
        assert provider.model == "mock-model-v2"

    def test_summarize_yields_chunks(self) -> None:
        provider = MockProvider(api_key="test-key")
        chunks = list(provider.summarize("Test content"))
        assert len(chunks) == 1
        assert chunks[0].is_final is True
        assert "Summary" in chunks[0].text

    def test_translate_yields_chunks(self) -> None:
        provider = MockProvider(api_key="test-key")
        chunks = list(provider.translate("Test content", target_lang="en"))
        assert len(chunks) == 1
        assert "Translated" in chunks[0].text

    def test_describe_image_yields_chunks(self) -> None:
        provider = MockProvider(api_key="test-key")
        chunks = list(provider.describe_image(b"\x89PNG"))
        assert len(chunks) == 1
        assert chunks[0].text == "Image description"

    def test_validate_key(self) -> None:
        provider = MockProvider(api_key="test-key")
        assert provider.validate_key() is True

    def test_supported_models(self) -> None:
        provider = MockProvider(api_key="test-key")
        assert "mock-model-v1" in provider.supported_models
        assert "mock-model-v2" in provider.supported_models


class TestBuildSummarizePrompt:
    """Test _build_summarize_prompt."""

    def test_default_prompt(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, user_p = provider._build_summarize_prompt("Nội dung test")
        assert "tổng hợp" in sys_p.lower()
        assert "Nội dung test" in user_p

    def test_custom_system_prompt(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, user_p = provider._build_summarize_prompt("Content", "Custom system")
        assert sys_p == "Custom system"
        assert "Content" in user_p


class TestBuildTranslatePrompt:
    """Test _build_translate_prompt."""

    def test_basic_translate(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, user_p = provider._build_translate_prompt("Hello", "vi")
        assert "tiếng Việt" in sys_p
        assert "Hello" in user_p

    def test_with_domain_and_style(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, user_p = provider._build_translate_prompt(
            "Content", "en", domain="CNTT", style="Báo cáo"
        )
        assert "CNTT" in sys_p
        assert "Báo cáo" in sys_p

    def test_with_glossary(self) -> None:
        provider = MockProvider(api_key="key")
        glossary = {"máy tính": "computer", "phần mềm": "software"}
        sys_p, user_p = provider._build_translate_prompt(
            "Content", "en", glossary=glossary
        )
        assert "máy tính" in sys_p
        assert "computer" in sys_p

    def test_with_context(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, user_p = provider._build_translate_prompt(
            "Content", "ja", context="Báo cáo tài chính Q3"
        )
        assert "Báo cáo tài chính Q3" in sys_p

    def test_default_domain_ignored(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, _ = provider._build_translate_prompt(
            "Content", "en", domain="Mặc định"
        )
        assert "Mặc định" not in sys_p

    def test_with_source_lang(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, _ = provider._build_translate_prompt(
            "Content", "en", source_lang="vi"
        )
        assert "tiếng Việt" in sys_p

    def test_target_lang_japanese(self) -> None:
        provider = MockProvider(api_key="key")
        sys_p, _ = provider._build_translate_prompt("Content", "ja")
        assert "tiếng Nhật" in sys_p


class TestBuildImagePrompt:
    """Test _build_image_prompt."""

    def test_default_prompt(self) -> None:
        provider = MockProvider(api_key="key")
        prompt = provider._build_image_prompt()
        assert "hình ảnh" in prompt.lower()

    def test_custom_prompt(self) -> None:
        provider = MockProvider(api_key="key")
        prompt = provider._build_image_prompt("Describe this chart")
        assert prompt == "Describe this chart"
