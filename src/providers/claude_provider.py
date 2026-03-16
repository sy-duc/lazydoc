"""ClaudeProvider — Triển khai AI Provider cho Anthropic Claude."""

import base64
import logging
from collections.abc import Generator

import anthropic

from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseProvider):
    """AI Provider sử dụng Anthropic Claude API.

    Sử dụng anthropic SDK với streaming response.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo ClaudeProvider.

        Args:
            api_key: Anthropic API key.
            model: Tên model Claude. Mặc định: claude-haiku-4-5-20251001.
        """
        super().__init__(api_key, model)
        self._client = anthropic.Anthropic(api_key=self._api_key)

    @property
    def name(self) -> str:
        return "claude"

    @property
    def default_model(self) -> str:
        return "claude-haiku-4-5-20251001"

    @property
    def supported_models(self) -> list[str]:
        return ["claude-sonnet-4-20250514", "claude-haiku-4-5-20251001"]

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

                # Lấy usage sau khi stream kết thúc
                response = stream.get_final_message()
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            yield StreamChunk(
                is_final=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.error("Claude describe_image lỗi: %s", e)
            raise

    def validate_key(self) -> bool:
        """Kiểm tra API key Claude bằng cách đếm token (miễn phí)."""
        try:
            # Dùng count_tokens — không tạo message, không tốn tiền
            self._client.messages.count_tokens(
                model=self._model,
                messages=[{"role": "user", "content": "test"}],
            )
            return True
        except anthropic.AuthenticationError:
            logger.warning("Claude API key không hợp lệ.")
            return False
        except Exception as e:
            logger.error("Claude validate_key lỗi: %s", e)
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

                # Lấy usage sau khi stream kết thúc
                response = stream.get_final_message()
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens

            yield StreamChunk(
                is_final=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception as e:
            logger.error("Claude streaming lỗi: %s", e)
            raise
