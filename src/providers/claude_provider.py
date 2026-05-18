"""ClaudeProvider — Triển khai AI Provider cho Anthropic Claude."""

import base64
import logging
from collections.abc import Generator

import anthropic

from src.core.logging_config import sanitize_error
from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseProvider):
    """AI Provider sử dụng Anthropic Claude API.

    Sử dụng anthropic SDK với streaming response.
    Tự động chọn model mới nhất từ API, fallback về claude-haiku nếu lỗi.
    """

    _FALLBACK_MODEL = "claude-haiku-4-5-20251001"
    _FALLBACK_MODELS = ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"]

    # Cache danh sách model (class-level, share giữa các instance)
    _cached_models: list[str] | None = None

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo ClaudeProvider.

        Args:
            api_key: Anthropic API key.
            model: Tên model Claude. Nếu None, tự chọn model mới nhất.
        """
        self._api_key = api_key
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._model = model or self._resolve_default_model()
        logger.info("Claude model đã chọn: %s", self._model)

    @property
    def name(self) -> str:
        return "claude"

    @property
    def default_model(self) -> str:
        return self._resolve_default_model()

    @property
    def supported_models(self) -> list[str]:
        return self._fetch_available_models()

    def _resolve_default_model(self) -> str:
        """Chọn model mặc định: ưu tiên haiku (nhanh/rẻ) > sonnet > opus.

        Trong cùng tier, chọn version mới nhất (sắp xếp giảm dần theo tên).

        Returns:
            Tên model mặc định.
        """
        models = self._fetch_available_models()
        stable = [m for m in models if "preview" not in m and "beta" not in m]
        if not stable:
            return self._FALLBACK_MODEL

        # Ưu tiên theo tier, lấy version mới nhất trong mỗi tier
        for tier in ("haiku", "sonnet", "opus"):
            tier_models = sorted(
                [m for m in stable if tier in m], reverse=True
            )
            if tier_models:
                return tier_models[0]

        return sorted(stable, reverse=True)[0]

    def _fetch_available_models(self) -> list[str]:
        """Lấy danh sách model Claude từ API, cache kết quả.

        Returns:
            Danh sách tên model Claude.
        """
        if ClaudeProvider._cached_models is not None:
            return ClaudeProvider._cached_models

        try:
            models = []
            for m in self._client.models.list():
                model_id = m.id
                if "claude" in model_id:
                    models.append(model_id)

            if models:
                ClaudeProvider._cached_models = sorted(models)
                logger.info("Claude models available: %s", models)
                return ClaudeProvider._cached_models
        except Exception as e:
            logger.warning("Không thể lấy danh sách model Claude: %s. Dùng fallback.", sanitize_error(e))

        ClaudeProvider._cached_models = list(self._FALLBACK_MODELS)
        return ClaudeProvider._cached_models

    def summarize(
        self,
        content: str,
        system_prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Tổng hợp nội dung bằng Claude, streaming response."""
        sys_prompt, user_prompt = self._build_summarize_prompt(content, system_prompt)
        yield from self._stream_messages(sys_prompt, user_prompt)

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
        """Dịch nội dung bằng Claude, streaming response."""
        sys_prompt, user_prompt = self._build_translate_prompt(
            content, target_lang, source_lang, domain, style, context, glossary
        )
        yield from self._stream_messages(sys_prompt, user_prompt)

    def describe_image(
        self,
        image_data: bytes,
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Mô tả hình ảnh bằng Claude Vision, streaming response."""
        image_prompt = self._build_image_prompt(prompt)
        b64_image = base64.b64encode(image_data).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": b64_image,
                        },
                    },
                    {
                        "type": "text",
                        "text": image_prompt,
                    },
                ],
            }
        ]

        try:
            input_tokens = 0
            output_tokens = 0

            with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                messages=messages,
                temperature=0.3,
            ) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(text=text)

                response = stream.get_final_message()
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            yield StreamChunk(
                is_final=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.error("Claude describe_image lỗi: %s", sanitize_error(e))
            raise

    def validate_key(self) -> bool:
        """Kiểm tra API key Claude bằng cách đếm token (miễn phí)."""
        try:
            self._client.messages.count_tokens(
                model=self._model,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except anthropic.AuthenticationError:
            logger.warning("Claude API key không hợp lệ.")
            return False
        except Exception as e:
            logger.error("Claude validate_key lỗi: %s", sanitize_error(e))
            return False

    def _stream_messages(
        self, system_prompt: str, user_prompt: str
    ) -> Generator[StreamChunk, None, None]:
        """Gọi Claude Messages API với streaming và yield từng chunk.

        Args:
            system_prompt: System prompt.
            user_prompt: User message.

        Yields:
            StreamChunk chứa text từ response.
        """
        try:
            input_tokens = 0
            output_tokens = 0

            with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=0.3,
            ) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(text=text)

                response = stream.get_final_message()
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            yield StreamChunk(
                is_final=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.error("Claude streaming lỗi: %s", sanitize_error(e))
            raise
