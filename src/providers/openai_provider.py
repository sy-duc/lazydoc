"""OpenAIProvider — Triển khai AI Provider cho OpenAI."""

import base64
import logging
from collections.abc import Generator

from openai import AuthenticationError, OpenAI

from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """AI Provider sử dụng OpenAI API.

    Sử dụng openai SDK với streaming response.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo OpenAIProvider.

        Args:
            api_key: OpenAI API key.
            model: Tên model OpenAI. Mặc định: gpt-4o-mini.
        """
        super().__init__(api_key, model)
        self._client = OpenAI(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return "gpt-4o-mini"

    @property
    def supported_models(self) -> list[str]:
        return ["gpt-4o", "gpt-4o-mini"]

    def summarize(
        self,
        content: str,
        system_prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Tổng hợp nội dung bằng OpenAI, streaming response."""
        sys_prompt, user_prompt = self._build_summarize_prompt(content, system_prompt)
        yield from self._stream_chat(sys_prompt, user_prompt)

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
        """Dịch nội dung bằng OpenAI, streaming response."""
        sys_prompt, user_prompt = self._build_translate_prompt(
            content, target_lang, source_lang, domain, style, context, glossary
        )
        yield from self._stream_chat(sys_prompt, user_prompt)

    def describe_image(
        self,
        image_data: bytes,
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Mô tả hình ảnh bằng OpenAI Vision, streaming response."""
        image_prompt = self._build_image_prompt(prompt)
        b64_image = base64.b64encode(image_data).decode("utf-8")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": image_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64_image}",
                        },
                    },
                ],
            }
        ]

        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                temperature=0.3,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(text=chunk.choices[0].delta.content)

                # Usage info ở chunk cuối cùng (khi include_usage=True)
                if chunk.usage:
                    yield StreamChunk(
                        is_final=True,
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    )
        except Exception as e:
            logger.error("OpenAI describe_image lỗi: %s", e)
            raise

    def validate_key(self) -> bool:
        """Kiểm tra API key OpenAI bằng cách liệt kê models."""
        try:
            self._client.models.list()
            return True
        except AuthenticationError:
            logger.warning("OpenAI API key không hợp lệ.")
            return False
        except Exception as e:
            logger.error("OpenAI validate_key lỗi: %s", e)
            return False

    def _stream_chat(
        self, system_prompt: str, user_prompt: str
    ) -> Generator[StreamChunk, None, None]:
        """Gọi OpenAI Chat API với streaming và yield từng chunk.

        Args:
            system_prompt: System message.
            user_prompt: User message.

        Yields:
            StreamChunk chứa text từ response.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                temperature=0.3,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(text=chunk.choices[0].delta.content)

                # Usage info ở chunk cuối
                if chunk.usage:
                    yield StreamChunk(
                        is_final=True,
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    )
        except Exception as e:
            logger.error("OpenAI streaming lỗi: %s", e)
            raise
