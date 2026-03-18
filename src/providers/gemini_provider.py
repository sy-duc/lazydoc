"""GeminiProvider — Triển khai AI Provider cho Google Gemini."""

import base64
import logging
from collections.abc import Generator

from google import genai
from google.genai import types

from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """AI Provider sử dụng Google Gemini API.

    Sử dụng google-genai SDK với streaming response.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo GeminiProvider.

        Args:
            api_key: Google AI API key.
            model: Tên model Gemini. Mặc định: gemini-1.5-flash.
        """
        super().__init__(api_key, model)
        self._client = genai.Client(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-2.0-flash"

    @property
    def supported_models(self) -> list[str]:
        return ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-preview-05-20"]

    def summarize(
        self,
        content: str,
        system_prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Tổng hợp nội dung bằng Gemini, streaming response."""
        sys_prompt, user_prompt = self._build_summarize_prompt(content, system_prompt)
        yield from self._stream_text(sys_prompt, user_prompt)

    def translate(
        self,
        content: str,
        target_lang: str,
        source_lang: str | None = None,
        domain: str | None = None,
        style: str | None = None,
        context: str | None = None,
        glossary: dict[str, str] | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Dịch nội dung bằng Gemini, streaming response."""
        sys_prompt, user_prompt = self._build_translate_prompt(
            content, target_lang, source_lang, domain, style, context, glossary
        )
        yield from self._stream_text(sys_prompt, user_prompt)

    def describe_image(
        self,
        image_data: bytes,
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Mô tả hình ảnh bằng Gemini Vision, streaming response."""
        image_prompt = self._build_image_prompt(prompt)

        # Tạo Part cho image
        image_part = types.Part.from_bytes(
            data=image_data,
            mime_type="image/png",
        )

        try:
            response_stream = self._client.models.generate_content_stream(
                model=self._model,
                contents=[image_prompt, image_part],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )

            last_chunk = None
            for chunk in response_stream:
                if chunk.text:
                    yield StreamChunk(text=chunk.text)
                last_chunk = chunk

            # Lấy usage từ chunk cuối
            usage = last_chunk.usage_metadata if last_chunk else None
            yield StreamChunk(
                is_final=True,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )
        except Exception as e:
            logger.error("Gemini describe_image lỗi: %s", e)
            raise

    def validate_key(self) -> bool:
        """Kiểm tra API key Gemini bằng cách liệt kê models (miễn phí)."""
        try:
            # Lấy 1 model để kiểm tra key hợp lệ
            for _ in self._client.models.list():
                break
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "permission" in error_str or "authenticat" in error_str or "api key" in error_str:
                logger.warning("Gemini API key không hợp lệ.")
                return False
            logger.error("Gemini validate_key lỗi: %s", e)
            return False

    def _stream_text(
        self, system_prompt: str, user_prompt: str
    ) -> Generator[StreamChunk, None, None]:
        """Gọi Gemini API với streaming và yield từng chunk.

        Args:
            system_prompt: System instruction.
            user_prompt: Nội dung người dùng.

        Yields:
            StreamChunk chứa text từ response.
        """
        try:
            response_stream = self._client.models.generate_content_stream(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                ),
            )

            last_chunk = None
            for chunk in response_stream:
                if chunk.text:
                    yield StreamChunk(text=chunk.text)
                last_chunk = chunk

            # Lấy usage metadata từ chunk cuối
            usage = last_chunk.usage_metadata if last_chunk else None
            yield StreamChunk(
                is_final=True,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )
        except Exception as e:
            logger.error("Gemini streaming lỗi: %s", e)
            raise
