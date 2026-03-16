"""GeminiProvider — Triển khai AI Provider cho Google Gemini."""

import base64
import logging
from collections.abc import Generator

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """AI Provider sử dụng Google Gemini API.

    Sử dụng google-generativeai SDK với streaming response.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo GeminiProvider.

        Args:
            api_key: Google AI API key.
            model: Tên model Gemini. Mặc định: gemini-1.5-flash.
        """
        super().__init__(api_key, model)
        genai.configure(api_key=self._api_key)
        self._client = genai.GenerativeModel(self._model)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return "gemini-1.5-flash"

    @property
    def supported_models(self) -> list[str]:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

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

        # Gemini nhận image dạng inline_data
        image_part = {
            "inline_data": {
                "mime_type": "image/png",
                "data": base64.b64encode(image_data).decode("utf-8"),
            }
        }

        try:
            response = self._client.generate_content(
                [image_prompt, image_part],
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                ),
            )

            for chunk in response:
                if chunk.text:
                    yield StreamChunk(text=chunk.text)

            # Lấy usage từ response sau khi stream xong
            usage = response.usage_metadata
            yield StreamChunk(
                is_final=True,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )
        except Exception as e:
            logger.error("Gemini describe_image lỗi: %s", e)
            raise

    def validate_key(self) -> bool:
        """Kiểm tra API key Gemini bằng cách liệt kê models."""
        try:
            # Gọi API nhẹ để kiểm tra key
            list(genai.list_models())
            return True
        except google_exceptions.PermissionDenied:
            logger.warning("Gemini API key không hợp lệ.")
            return False
        except google_exceptions.Unauthenticated:
            logger.warning("Gemini API key không hợp lệ.")
            return False
        except Exception as e:
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
        # Tạo model mới với system_instruction
        model = genai.GenerativeModel(
            self._model,
            system_instruction=system_prompt,
        )

        try:
            response = model.generate_content(
                user_prompt,
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                ),
            )

            for chunk in response:
                if chunk.text:
                    yield StreamChunk(text=chunk.text)

            # Lấy usage metadata sau khi stream hoàn tất
            usage = response.usage_metadata
            yield StreamChunk(
                is_final=True,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )
        except Exception as e:
            logger.error("Gemini streaming lỗi: %s", e)
            raise
