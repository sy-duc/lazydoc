"""BaseProvider — Abstract interface cho các AI Provider (Strategy Pattern)."""

from abc import ABC, abstractmethod
from collections.abc import Generator
from dataclasses import dataclass, field


@dataclass
class AIResponse:
    """Kết quả phản hồi từ AI Provider.

    Attributes:
        text: Nội dung phản hồi đầy đủ (ghép từ các chunk streaming).
        input_tokens: Số token đầu vào.
        output_tokens: Số token đầu ra.
        model: Tên model đã sử dụng.
    """

    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class StreamChunk:
    """Một chunk trong quá trình streaming response.

    Attributes:
        text: Đoạn text trong chunk này.
        input_tokens: Số token đầu vào (chỉ có ở chunk cuối hoặc usage chunk).
        output_tokens: Số token đầu ra (chỉ có ở chunk cuối hoặc usage chunk).
        is_final: True nếu đây là chunk cuối cùng.
    """

    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    is_final: bool = False


class BaseProvider(ABC):
    """Abstract interface cho AI Provider.

    Tất cả provider (Gemini, OpenAI, Claude) phải triển khai interface này.
    Sử dụng Strategy Pattern để chuyển đổi provider tại runtime.
    """

    def __init__(self, api_key: str, model: str | None = None) -> None:
        """Khởi tạo provider.

        Args:
            api_key: API key đã giải mã.
            model: Tên model cụ thể. Nếu None, dùng default_model.
        """
        self._api_key = api_key
        self._model = model or self.default_model

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên provider (gemini, openai, claude)."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Model mặc định của provider."""
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        """Danh sách model mà provider hỗ trợ."""
        ...

    @property
    def model(self) -> str:
        """Model đang sử dụng."""
        return self._model

    @abstractmethod
    def summarize(
        self,
        content: str,
        system_prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Tổng hợp nội dung, streaming từng chunk.

        Args:
            content: Nội dung cần tổng hợp.
            system_prompt: Prompt hệ thống tùy chỉnh.

        Yields:
            StreamChunk chứa text và thông tin token.
        """
        ...

    @abstractmethod
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
        """Dịch nội dung, streaming từng chunk.

        Args:
            content: Nội dung cần dịch.
            target_lang: Ngôn ngữ đích (vi, en, ja).
            source_lang: Ngôn ngữ nguồn (tự detect nếu None).
            domain: Lĩnh vực (CNTT, Y tế, Tài chính, ...).
            style: Văn phong (Báo cáo, Súc tích, ...).
            context: Ngữ cảnh bổ sung từ kết quả tổng hợp.
            glossary: Bảng thuật ngữ {term_gốc: term_dịch}.

        Yields:
            StreamChunk chứa text đã dịch.
        """
        ...

    @abstractmethod
    def describe_image(
        self,
        image_data: bytes,
        prompt: str | None = None,
    ) -> Generator[StreamChunk, None, None]:
        """Mô tả hình ảnh bằng AI vision, streaming.

        Args:
            image_data: Dữ liệu ảnh dạng bytes.
            prompt: Prompt tùy chỉnh cho mô tả ảnh.

        Yields:
            StreamChunk chứa mô tả ảnh.
        """
        ...

    @abstractmethod
    def validate_key(self) -> bool:
        """Kiểm tra API key có hợp lệ không.

        Returns:
            True nếu key hợp lệ và có thể gọi API.
        """
        ...

    def _build_summarize_prompt(
        self, content: str, system_prompt: str | None = None
    ) -> tuple[str, str]:
        """Tạo system prompt và user prompt cho tổng hợp.

        Args:
            content: Nội dung cần tổng hợp.
            system_prompt: System prompt tùy chỉnh.

        Returns:
            Tuple (system_prompt, user_prompt).
        """
        sys_prompt = system_prompt or (
            "Bạn là trợ lý AI chuyên tổng hợp thông tin từ tài liệu. "
            "Hãy tóm tắt nội dung một cách chính xác, rõ ràng, và có cấu trúc. "
            "Trả lời bằng tiếng Việt."
        )
        user_prompt = (
            "Hãy tổng hợp nội dung tài liệu sau:\n\n"
            f"{content}"
        )
        return sys_prompt, user_prompt

    def _build_translate_prompt(
        self,
        content: str,
        target_lang: str,
        source_lang: str | None = None,
        domain: str | None = None,
        style: str | None = None,
        context: str | None = None,
        glossary: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """Tạo system prompt và user prompt cho dịch thuật.

        Args:
            content: Nội dung cần dịch.
            target_lang: Ngôn ngữ đích.
            source_lang: Ngôn ngữ nguồn.
            domain: Lĩnh vực.
            style: Văn phong.
            context: Ngữ cảnh bổ sung.
            glossary: Bảng thuật ngữ.

        Returns:
            Tuple (system_prompt, user_prompt).
        """
        lang_names = {"vi": "tiếng Việt", "en": "tiếng Anh", "ja": "tiếng Nhật"}
        target_name = lang_names.get(target_lang, target_lang)

        sys_parts = [
            f"Bạn là dịch giả chuyên nghiệp. Dịch chính xác sang {target_name}.",
            "Giữ nguyên cấu trúc và định dạng gốc.",
            "CHỈ trả về bản dịch, KHÔNG thêm giải thích hay ghi chú.",
        ]

        if source_lang:
            source_name = lang_names.get(source_lang, source_lang)
            sys_parts.append(f"Ngôn ngữ nguồn: {source_name}.")

        if domain and domain != "Mặc định":
            sys_parts.append(f"Lĩnh vực chuyên môn: {domain}.")

        if style and style != "Mặc định":
            sys_parts.append(f"Văn phong dịch: {style}.")

        if context:
            sys_parts.append(f"Ngữ cảnh tài liệu: {context}")

        if glossary:
            glossary_text = "\n".join(
                f"  - {src} → {tgt}" for src, tgt in glossary.items()
            )
            sys_parts.append(f"Bảng thuật ngữ bắt buộc:\n{glossary_text}")

        sys_prompt = "\n".join(sys_parts)
        user_prompt = f"Dịch nội dung sau:\n\n{content}"
        return sys_prompt, user_prompt

    def _build_image_prompt(self, prompt: str | None = None) -> str:
        """Tạo prompt cho mô tả hình ảnh.

        Args:
            prompt: Prompt tùy chỉnh.

        Returns:
            Prompt cho AI vision.
        """
        return prompt or (
            "Mô tả chi tiết nội dung hình ảnh này bằng tiếng Việt. "
            "Nếu là biểu đồ/bảng biểu, hãy trích xuất dữ liệu cụ thể."
        )
