"""AIEngine — Engine dịch thuật sử dụng AI Provider với batch optimization."""

import logging
import re
import time
from typing import Callable

from src.providers.base import BaseProvider, StreamChunk

logger = logging.getLogger(__name__)

# Giới hạn ký tự mỗi batch gửi cho AI
_BATCH_CHAR_LIMIT = 3500

# Delimiter phân tách items trong batch — dùng ký tự Unicode hiếm
_ITEM_PREFIX = "⟦"
_ITEM_SUFFIX = "⟧"

# Retry config
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds, doubled mỗi lần

# Từ khóa trong error message → có thể retry
_RETRYABLE_KEYWORDS = (
    "timeout", "timed out", "connection", "reset by peer",
    "rate limit", "too many requests", "overloaded", "unavailable",
    "503", "502", "504", "429",
)


def _is_retryable(e: Exception) -> bool:
    """Kiểm tra lỗi có thể retry không (timeout, connection, rate limit)."""
    s = str(e).lower()
    return any(kw in s for kw in _RETRYABLE_KEYWORDS)


class AIEngine:
    """Engine dịch thuật qua AI Provider với batch optimization.

    Chiến lược 2 pha:
    - Pha 1 (collect): Thu thập tất cả text cần dịch từ file.
    - Pha 2 (translate): Gom thành batch theo giới hạn ký tự, gửi AI.
    - Pha 3 (lookup): Writer chạy lại, translate_fn tra dict thay vì gọi API.

    Lợi ích: system prompt (domain, style, glossary) chỉ gửi 1 lần/batch,
    AI có ngữ cảnh từ nhiều text liên quan → dịch sát nghĩa hơn.
    """

    def __init__(
        self,
        provider: BaseProvider,
        target_lang: str,
        source_lang: str | None = None,
        domain: str | None = None,
        style: str | None = None,
        context: str | None = None,
        glossary: dict[str, str] | None = None,
    ) -> None:
        """Khởi tạo AIEngine.

        Args:
            provider: AI Provider instance (Gemini, OpenAI, Claude).
            target_lang: Mã ngôn ngữ đích.
            source_lang: Mã ngôn ngữ nguồn (tự detect nếu None).
            domain: Lĩnh vực (CNTT, Y tế, ...).
            style: Văn phong (Báo cáo, Súc tích, ...).
            context: Ngữ cảnh bổ sung từ kết quả tổng hợp.
            glossary: Bảng thuật ngữ {term_gốc: term_dịch}.
        """
        self._provider = provider
        self._target_lang = target_lang
        self._source_lang = source_lang
        self._domain = domain
        self._style = style
        self._context = context
        self._glossary = glossary

        # State cho collect/lookup
        self._collected: list[str] = []
        self._collected_set: set[str] = set()
        self._lookup: dict[str, str] = {}
        self._collecting = False

        # Tích lũy token usage
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        # Callback cập nhật usage (set bởi worker)
        self._on_usage: Callable[[int, int], None] | None = None

    @property
    def provider_name(self) -> str:
        """Tên provider đang dùng."""
        return self._provider.name

    @property
    def model(self) -> str:
        """Model đang dùng."""
        return self._provider.model

    def set_usage_callback(self, callback: Callable[[int, int], None]) -> None:
        """Đặt callback nhận usage sau mỗi lần gọi API.

        Args:
            callback: Hàm nhận (input_tokens, output_tokens).
        """
        self._on_usage = callback

    # --- Pha 1: Collect ---

    def start_collecting(self) -> None:
        """Bắt đầu thu thập text. Reset state cũ."""
        self._collected = []
        self._collected_set = set()
        self._lookup = {}
        self._collecting = True

    def create_translate_fn(self) -> Callable[[str], str]:
        """Tạo hàm dịch dùng chung cho cả pha collect và lookup.

        - Khi đang collect: ghi nhận text, trả về text gốc.
        - Khi đã translate xong: tra dict lookup.

        Returns:
            Hàm dịch nhận text trả về text đã dịch (hoặc gốc khi collect).
        """
        def translate_fn(text: str) -> str:
            if not text or not text.strip():
                return text

            if self._collecting:
                # Pha collect: ghi nhận text mới, trả gốc
                stripped = text.strip()
                if stripped not in self._collected_set:
                    self._collected.append(text)
                    self._collected_set.add(stripped)
                return text

            # Pha lookup: tra dict
            return self._lookup.get(text.strip(), text)

        return translate_fn

    # --- Pha 2: Batch translate ---

    def flush_and_translate(self) -> None:
        """Dịch batch tất cả text đã thu thập, lưu vào lookup dict.

        Gom text thành các batch theo giới hạn ký tự, mỗi batch 1 API call.
        """
        self._collecting = False

        if not self._collected:
            return

        # Tạo các batch theo giới hạn ký tự
        batches = self._build_batches(self._collected)
        logger.info(
            "Batch translate: %d text → %d batch (limit %d chars/batch)",
            len(self._collected), len(batches), _BATCH_CHAR_LIMIT,
        )

        for batch_idx, batch in enumerate(batches):
            try:
                translated = self._translate_batch(batch)
                # Map kết quả vào lookup dict
                for original, result in zip(batch, translated):
                    self._lookup[original.strip()] = result
                logger.debug(
                    "Batch %d/%d: %d items dịch thành công.",
                    batch_idx + 1, len(batches), len(batch),
                )
            except Exception as e:
                logger.error("Batch %d/%d thất bại: %s", batch_idx + 1, len(batches), e)
                raise

    @staticmethod
    def _build_batches(texts: list[str]) -> list[list[str]]:
        """Chia danh sách text thành các batch theo giới hạn ký tự.

        Args:
            texts: Danh sách text cần dịch.

        Returns:
            Danh sách batch, mỗi batch là list[str].
        """
        batches: list[list[str]] = []
        current_batch: list[str] = []
        current_chars = 0

        for text in texts:
            text_len = len(text)

            # Text đơn lẻ vượt limit → gửi riêng 1 batch
            if text_len > _BATCH_CHAR_LIMIT:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_chars = 0
                batches.append([text])
                continue

            # Thêm vào batch hiện tại nếu còn chỗ
            if current_chars + text_len > _BATCH_CHAR_LIMIT and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

            current_batch.append(text)
            current_chars += text_len

        if current_batch:
            batches.append(current_batch)

        return batches

    def _translate_batch(self, texts: list[str]) -> list[str]:
        """Dịch một batch text qua AI Provider.

        Nếu batch chỉ có 1 item → gửi trực tiếp không cần format đánh số.
        Nếu nhiều items → đánh số [1], [2], ... và yêu cầu AI giữ format.

        Args:
            texts: Danh sách text trong batch.

        Returns:
            Danh sách text đã dịch (cùng thứ tự).
        """
        if len(texts) == 1:
            return [self._translate_single(texts[0])]

        return self._translate_numbered(texts)

    def _collect_chunks_with_retry(
        self, generator_factory: Callable[[], "Generator[StreamChunk, None, None]"]
    ) -> tuple[list[str], int, int]:
        """Gọi API và thu thập chunks, tự động retry khi gặp lỗi tạm thời.

        Args:
            generator_factory: Hàm trả về generator mới mỗi lần gọi.

        Returns:
            Tuple (chunks, input_tokens, output_tokens).

        Raises:
            Exception: Lỗi không thể retry hoặc đã hết số lần thử.
        """
        for attempt in range(_MAX_RETRIES):
            try:
                chunks: list[str] = []
                input_tokens = 0
                output_tokens = 0
                for chunk in generator_factory():
                    if chunk.text:
                        chunks.append(chunk.text)
                    if chunk.is_final:
                        input_tokens = chunk.input_tokens
                        output_tokens = chunk.output_tokens
                return chunks, input_tokens, output_tokens
            except Exception as e:
                is_last = attempt == _MAX_RETRIES - 1
                if not _is_retryable(e) or is_last:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "API lỗi tạm thời (lần %d/%d), thử lại sau %.0fs: %s",
                    attempt + 1, _MAX_RETRIES, delay, e,
                )
                time.sleep(delay)
        raise RuntimeError("Không thể hoàn thành sau khi retry.")  # không đến được đây

    def _translate_single(self, text: str) -> str:
        """Dịch một text đơn lẻ qua AI, có retry."""
        chunks, input_tokens, output_tokens = self._collect_chunks_with_retry(
            lambda: self._provider.translate(
                content=text,
                target_lang=self._target_lang,
                source_lang=self._source_lang,
                domain=self._domain,
                style=self._style,
                context=self._context,
                glossary=self._glossary,
            )
        )
        self._accumulate_usage(input_tokens, output_tokens)
        result = "".join(chunks)
        return result.strip() if result.strip() else text

    def _translate_numbered(self, texts: list[str]) -> list[str]:
        """Dịch nhiều text bằng format đánh số.

        Gửi:
            ⟦1⟧ text_1
            ⟦2⟧ text_2
        Nhận:
            ⟦1⟧ bản_dịch_1
            ⟦2⟧ bản_dịch_2

        Args:
            texts: Danh sách text cần dịch.

        Returns:
            Danh sách text đã dịch (cùng thứ tự).
        """
        # Tạo nội dung đánh số
        numbered_lines = []
        for i, text in enumerate(texts, 1):
            # Thay newline bằng dấu đặc biệt để giữ trên 1 dòng logic
            safe_text = text.replace("\n", " ↵ ")
            numbered_lines.append(f"{_ITEM_PREFIX}{i}{_ITEM_SUFFIX} {safe_text}")
        content = "\n".join(numbered_lines)

        # Gửi cho AI với chỉ thị giữ format đánh số
        batch_instruction = (
            f"Dịch {len(texts)} mục bên dưới. "
            f"GIỮ NGUYÊN format đánh số {_ITEM_PREFIX}N{_ITEM_SUFFIX} ở đầu mỗi mục. "
            f"Mỗi mục dịch trên 1 dòng. CHỈ trả về bản dịch, KHÔNG thêm gì khác."
        )

        batch_content = f"{batch_instruction}\n\n{content}"
        chunks, input_tokens, output_tokens = self._collect_chunks_with_retry(
            lambda: self._provider.translate(
                content=batch_content,
                target_lang=self._target_lang,
                source_lang=self._source_lang,
                domain=self._domain,
                style=self._style,
                context=self._context,
                glossary=self._glossary,
            )
        )
        self._accumulate_usage(input_tokens, output_tokens)

        # Parse kết quả
        raw_response = "".join(chunks)
        parsed = self._parse_numbered_response(raw_response, len(texts))

        # Map về đúng thứ tự, fallback text gốc nếu parse lỗi
        results = []
        for i, text in enumerate(texts):
            translated = parsed.get(i + 1)
            if translated:
                # Khôi phục newline
                translated = translated.replace(" ↵ ", "\n")
                results.append(translated)
            else:
                logger.warning("Batch item %d không có trong response, giữ nguyên.", i + 1)
                results.append(text)

        return results

    @staticmethod
    def _parse_numbered_response(response: str, expected_count: int) -> dict[int, str]:
        """Parse response đánh số từ AI.

        Args:
            response: Response text từ AI.
            expected_count: Số item mong đợi.

        Returns:
            Dict {số_thứ_tự: text_đã_dịch}.
        """
        result: dict[int, str] = {}

        # Regex match ⟦N⟧ text
        pattern = re.compile(
            rf"{re.escape(_ITEM_PREFIX)}(\d+){re.escape(_ITEM_SUFFIX)}\s*(.*?)(?=\n{re.escape(_ITEM_PREFIX)}\d+{re.escape(_ITEM_SUFFIX)}|\Z)",
            re.DOTALL,
        )

        for match in pattern.finditer(response):
            idx = int(match.group(1))
            text = match.group(2).strip()
            if 1 <= idx <= expected_count:
                result[idx] = text

        return result

    def _accumulate_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Cập nhật token usage tích lũy."""
        self._total_input_tokens += input_tokens
        self._total_output_tokens += output_tokens
        if self._on_usage:
            self._on_usage(input_tokens, output_tokens)
