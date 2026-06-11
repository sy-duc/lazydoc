"""TaskProvider - Chọn model theo tác vụ và fallback kỹ thuật có kiểm soát."""

import logging
from collections.abc import Callable, Generator
from typing import Any

from src.core.logging_config import sanitize_error
from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)

_MODEL_ERROR_KEYWORDS = (
    "model not found",
    "model_not_found",
    "model does not exist",
    "model is not available",
    "model unavailable",
    "unsupported model",
    "model is not supported",
    "not found for api version",
    "do not have access to model",
    "does not have access to model",
)


def _is_model_error(error: Exception) -> bool:
    """Trả về True khi lỗi cho biết model không tồn tại hoặc không khả dụng."""
    status_code = (
        getattr(error, "status_code", None)
        or getattr(error, "code", None)
    )
    if status_code == 404:
        return True

    message = str(error).lower()
    if any(keyword in message for keyword in _MODEL_ERROR_KEYWORDS):
        return True
    return "model" in message and (
        "does not exist" in message
        or "not found" in message
        or "not available" in message
        or "not supported" in message
    )


class TaskProvider(BaseProvider):
    """Provider proxy dùng primary model và fallback khi model lỗi kỹ thuật."""

    def __init__(
        self,
        provider_factory: Callable[[str], BaseProvider],
        primary_model: str,
        fallback_model: str | None = None,
    ) -> None:
        self._provider_factory = provider_factory
        self._primary_model = primary_model
        self._fallback_model = fallback_model
        self._provider = provider_factory(primary_model)

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def default_model(self) -> str:
        return self._primary_model

    @property
    def supported_models(self) -> list[str]:
        return self._provider.supported_models

    @property
    def model(self) -> str:
        return self._provider.model

    def summarize(
        self,
        content: str,
        system_prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        yield from self._call_with_fallback("summarize", content, system_prompt)

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
        yield from self._call_with_fallback(
            "translate",
            content,
            target_lang,
            source_lang,
            domain,
            style,
            context,
            glossary,
        )

    def describe_image(
        self,
        image_data: bytes,
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        yield from self._call_with_fallback("describe_image", image_data, prompt)

    def describe_images_batch(
        self,
        images: list[bytes],
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        yield from self._call_with_fallback("describe_images_batch", images, prompt)

    def validate_key(self) -> bool:
        return self._provider.validate_key()

    def _call_with_fallback(
        self,
        method_name: str,
        *args: Any,
    ) -> Generator[StreamChunk, None, None]:
        """Retry một lần bằng fallback nếu primary model lỗi trước khi stream."""
        emitted = False
        try:
            method = getattr(self._provider, method_name)
            for chunk in method(*args):
                emitted = True
                yield chunk
            return
        except Exception as error:
            if emitted or not self._fallback_model or not _is_model_error(error):
                raise

            logger.warning(
                "Model %s không khả dụng (%s). Chuyển sang fallback %s.",
                self._provider.model,
                sanitize_error(error),
                self._fallback_model,
            )
            self._provider = self._provider_factory(self._fallback_model)
            self._fallback_model = None

        method = getattr(self._provider, method_name)
        yield from method(*args)
