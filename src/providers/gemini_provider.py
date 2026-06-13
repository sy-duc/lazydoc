"""GeminiProvider — Triển khai AI Provider cho Google Gemini."""

import base64
import logging
from collections.abc import Generator

from google import genai
from google.genai import types

from src.core.logging_config import sanitize_error
from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """AI Provider sử dụng Google Gemini API.

    Sử dụng google-genai SDK với streaming response.
    """

    # Fallback hardcode khi không thể gọi API lấy danh sách model
    _FALLBACK_MODEL = "gemini-2.5-flash"
    _FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.5-pro"]

    # Cache danh sách model (class-level, share giữa các instance)
    _cached_models: list[str] | None = None

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo GeminiProvider.

        Args:
            api_key: Google AI API key.
            model: Tên model Gemini. Nếu None, tự chọn từ API.
        """
        self._api_key = api_key
        self._client = genai.Client(api_key=self._api_key)
        self._model = model or self._resolve_default_model()
        logger.info("Gemini model đã chọn: %s", self._model)

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def default_model(self) -> str:
        return self._resolve_default_model()

    @property
    def supported_models(self) -> list[str]:
        return self._fetch_available_models()

    def _resolve_default_model(self) -> str:
        """Chọn model mặc định: ưu tiên flash version mới nhất.

        Ưu tiên: flash (cân bằng giá/chất lượng) > pro > flash-lite.
        Trong cùng loại, chọn version cao nhất (2.5 > 2.0 > 1.5).
        Bỏ qua preview/experimental.

        Returns:
            Tên model mặc định.
        """
        models = self._fetch_available_models()
        # Lọc bỏ preview, experimental, và alias "-latest" (không có trong bảng giá)
        stable = [
            m for m in models
            if "preview" not in m
            and "exp" not in m
            and not m.endswith("-latest")
        ]
        if not stable:
            return self._FALLBACK_MODEL

        # Sắp xếp giảm dần theo version (gemini-2.5 > gemini-2.0 > gemini-1.5)
        stable.sort(reverse=True)

        # Ưu tiên: flash (không lite) > pro > flash-lite
        for keyword, exclude in [("flash", "lite"), ("pro", None), ("flash-lite", None)]:
            for m in stable:
                if keyword in m and (exclude is None or exclude not in m):
                    return m

        return stable[0]

    def _fetch_available_models(self) -> list[str]:
        """Lấy danh sách model từ API, cache kết quả.

        Returns:
            Danh sách tên model hỗ trợ generateContent.
        """
        if GeminiProvider._cached_models is not None:
            return GeminiProvider._cached_models

        try:
            models = []
            for m in self._client.models.list():
                model_id = m.name.replace("models/", "")
                actions = m.supported_actions or []
                if "gemini" in model_id and any(
                    "generateContent" in a for a in actions
                ):
                    models.append(model_id)

            if models:
                GeminiProvider._cached_models = sorted(models)
                logger.info("Gemini models available: %s", models)
                return GeminiProvider._cached_models
        except Exception as e:
            logger.warning("Không thể lấy danh sách model Gemini: %s. Dùng fallback.", sanitize_error(e))

        GeminiProvider._cached_models = self._FALLBACK_MODELS
        return GeminiProvider._cached_models

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
        translation_instructions: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Dịch nội dung bằng Gemini, streaming response."""
        sys_prompt, user_prompt = self._build_translate_prompt(
            content, target_lang, source_lang, domain, style, context,
            glossary, translation_instructions
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
            logger.error("Gemini describe_image lỗi: %s", sanitize_error(e))
            raise

    def describe_images_batch(
        self,
        images: list[bytes],
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Mô tả nhiều hình ảnh trong một API call bằng Gemini Vision."""
        batch_prompt = self._build_image_batch_prompt(len(images), prompt)

        contents: list = [batch_prompt]
        for img_data in images:
            contents.append(types.Part.from_bytes(data=img_data, mime_type="image/png"))

        try:
            response_stream = self._client.models.generate_content_stream(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.3),
            )

            last_chunk = None
            for chunk in response_stream:
                if chunk.text:
                    yield StreamChunk(text=chunk.text)
                last_chunk = chunk

            usage = last_chunk.usage_metadata if last_chunk else None
            yield StreamChunk(
                is_final=True,
                input_tokens=usage.prompt_token_count if usage else 0,
                output_tokens=usage.candidates_token_count if usage else 0,
            )
        except Exception as e:
            logger.error("Gemini describe_images_batch lỗi: %s", sanitize_error(e))
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
            logger.error("Gemini validate_key lỗi: %s", sanitize_error(e))
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
            logger.error("Gemini streaming lỗi: %s", sanitize_error(e))
            raise
