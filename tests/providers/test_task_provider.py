"""Test TaskProvider model routing và fallback kỹ thuật."""

from collections.abc import Generator

import pytest

from src.providers.base import BaseProvider, StreamChunk
from src.providers.task_provider import TaskProvider


class StubProvider(BaseProvider):
    def __init__(
        self,
        model: str,
        error: Exception | None = None,
    ) -> None:
        super().__init__("key", model)
        self._error = error

    @property
    def name(self) -> str:
        return "stub"

    @property
    def default_model(self) -> str:
        return "default"

    @property
    def supported_models(self) -> list[str]:
        return ["primary", "fallback"]

    def summarize(
        self, content: str, system_prompt: str | None = None
    ) -> Generator[StreamChunk, None, None]:
        if self._error:
            raise self._error
        yield StreamChunk(text=f"{self.model}:{content}")

    def translate(self, *args, **kwargs) -> Generator[StreamChunk, None, None]:
        yield from self.summarize(args[0])

    def describe_image(self, *args, **kwargs) -> Generator[StreamChunk, None, None]:
        yield from self.summarize("image")

    def describe_images_batch(
        self, *args, **kwargs
    ) -> Generator[StreamChunk, None, None]:
        yield from self.summarize("images")

    def validate_key(self) -> bool:
        return True


def test_uses_primary_model() -> None:
    provider = TaskProvider(
        provider_factory=lambda model: StubProvider(model),
        primary_model="primary",
        fallback_model="fallback",
    )

    chunks = list(provider.summarize("content"))

    assert provider.model == "primary"
    assert chunks[0].text == "primary:content"


def test_falls_back_when_model_is_not_found() -> None:
    def factory(model: str) -> StubProvider:
        error = RuntimeError("model not found") if model == "primary" else None
        return StubProvider(model, error)

    provider = TaskProvider(factory, "primary", "fallback")

    chunks = list(provider.summarize("content"))

    assert provider.model == "fallback"
    assert chunks[0].text == "fallback:content"


def test_falls_back_for_model_404() -> None:
    class ModelNotFoundError(RuntimeError):
        status_code = 404

    def factory(model: str) -> StubProvider:
        error = ModelNotFoundError("not found") if model == "primary" else None
        return StubProvider(model, error)

    provider = TaskProvider(factory, "primary", "fallback")

    list(provider.summarize("content"))

    assert provider.model == "fallback"


@pytest.mark.parametrize(
    "message",
    ["timeout", "429 rate limit", "connection reset by peer"],
)
def test_does_not_fallback_for_transient_errors(message: str) -> None:
    provider = TaskProvider(
        provider_factory=lambda model: StubProvider(model, RuntimeError(message)),
        primary_model="primary",
        fallback_model="fallback",
    )

    with pytest.raises(RuntimeError, match=message):
        list(provider.summarize("content"))

    assert provider.model == "primary"


def test_does_not_fallback_after_stream_has_started() -> None:
    class PartialProvider(StubProvider):
        def summarize(
            self, content: str, system_prompt: str | None = None
        ) -> Generator[StreamChunk, None, None]:
            yield StreamChunk(text="partial")
            raise RuntimeError("model not found")

    provider = TaskProvider(
        provider_factory=lambda model: PartialProvider(model),
        primary_model="primary",
        fallback_model="fallback",
    )

    with pytest.raises(RuntimeError, match="model not found"):
        list(provider.summarize("content"))

    assert provider.model == "primary"
