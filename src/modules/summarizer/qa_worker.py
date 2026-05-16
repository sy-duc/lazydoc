"""QAWorker — Worker thread cho Q&A sau khi tổng hợp."""

import logging
import time

from PySide6.QtCore import QThread, Signal

from src.providers.base import BaseProvider

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0
_QA_HISTORY_LIMIT = 5

_RETRYABLE_KEYWORDS = (
    "timeout", "timed out", "connection", "reset by peer",
    "rate limit", "too many requests", "overloaded", "unavailable",
    "503", "502", "504", "429",
)


def _is_retryable(e: Exception) -> bool:
    s = str(e).lower()
    return any(kw in s for kw in _RETRYABLE_KEYWORDS)


class QAWorker(QThread):
    """Worker chạy Q&A với báo cáo tổng hợp làm context.

    Dùng generated report (không phải raw documents) làm context để tiết kiệm
    token. Giữ rolling window 5 Q&A gần nhất trong history.

    Signals:
        streaming_text: Phát text streaming (str chunk).
        cost_updated: Phát token usage (int input, int output).
        completed: Phát khi hoàn tất (bool thành_công, str lỗi).
    """

    streaming_text = Signal(str)
    cost_updated = Signal(int, int)
    completed = Signal(bool, str)

    def __init__(
        self,
        summary_context: str,
        qa_history: list[tuple[str, str]],
        question: str,
        provider: BaseProvider,
        parent: object = None,
    ) -> None:
        """Khởi tạo QAWorker.

        Args:
            summary_context: Báo cáo tổng hợp đã sinh ra (làm context).
            qa_history: Lịch sử Q&A trước đó [(câu_hỏi, câu_trả_lời), ...].
            question: Câu hỏi mới của người dùng.
            provider: BaseProvider instance.
            parent: QObject cha.
        """
        super().__init__(parent)
        self._summary_context = summary_context
        self._qa_history = qa_history[-_QA_HISTORY_LIMIT:]
        self._question = question
        self._provider = provider
        self._cancelled = False

    def run(self) -> None:
        """Thực thi Q&A trên worker thread."""
        try:
            system_prompt = (
                "Bạn là trợ lý AI phân tích tài liệu. "
                "Trả lời câu hỏi DỰA TRÊN báo cáo tổng hợp được cung cấp. "
                "Nếu báo cáo không có đủ thông tin → nói rõ điều đó thay vì đoán. "
                "Trả lời bằng tiếng Việt, ngắn gọn và chính xác."
            )

            history_text = ""
            if self._qa_history:
                pairs = [
                    f"Người dùng: {q}\nTrợ lý: {a}"
                    for q, a in self._qa_history
                ]
                history_text = "\n\n".join(pairs)

            content = f"BÁO CÁO TỔNG HỢP:\n{self._summary_context}\n\n---\n\n"
            if history_text:
                content += f"LỊCH SỬ HỘI THOẠI:\n{history_text}\n\n---\n\n"
            content += f"CÂU HỎI MỚI: {self._question}"

            for attempt in range(_MAX_RETRIES):
                try:
                    for chunk in self._provider.summarize(content, system_prompt):
                        if self._cancelled:
                            self.completed.emit(False, "Đã hủy")
                            return
                        if chunk.text:
                            self.streaming_text.emit(chunk.text)
                        if chunk.is_final:
                            self.cost_updated.emit(chunk.input_tokens, chunk.output_tokens)
                    self.completed.emit(True, "")
                    return
                except Exception as e:
                    is_last = attempt == _MAX_RETRIES - 1
                    if not _is_retryable(e) or is_last:
                        raise
                    delay = _RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "QA API lỗi tạm thời (lần %d/%d), thử lại sau %.0fs: %s",
                        attempt + 1, _MAX_RETRIES, delay, e,
                    )
                    time.sleep(delay)

        except Exception as e:
            logger.error("QA worker lỗi: %s", e, exc_info=True)
            self.completed.emit(False, str(e))

    def cancel(self) -> None:
        """Yêu cầu hủy Q&A đang chạy."""
        self._cancelled = True
