"""QAModule — Điều phối Q&A sau khi tổng hợp."""

import logging

from PySide6.QtCore import QObject, Signal

from src.core.logging_config import sanitize_error
from src.modules.summarizer.qa_worker import QAWorker

logger = logging.getLogger(__name__)


class QAModule(QObject):
    """Module điều phối Q&A với báo cáo tổng hợp làm context.

    Signals:
        streaming_text: Phát text streaming từ AI (str chunk).
        cost_updated: Phát token usage (int input, int output).
        completed: Phát khi hoàn tất (bool thành_công, str lỗi).
    """

    streaming_text = Signal(str)
    cost_updated = Signal(int, int)
    completed = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo QAModule."""
        super().__init__(parent)
        self._worker: QAWorker | None = None
        self._provider_manager = None
        self._active_provider = None

    @property
    def is_running(self) -> bool:
        """Kiểm tra worker đang chạy hay không."""
        return self._worker is not None and self._worker.isRunning()

    def set_provider_manager(self, provider_manager: object) -> None:
        """Đặt ProviderManager để lấy AI provider.

        Args:
            provider_manager: ProviderManager instance.
        """
        self._provider_manager = provider_manager

    def start_qa(
        self,
        summary_context: str,
        qa_history: list[tuple[str, str]],
        question: str,
    ) -> None:
        """Bắt đầu Q&A trên worker thread.

        Args:
            summary_context: Báo cáo tổng hợp (context cho AI).
            qa_history: Lịch sử Q&A trong session.
            question: Câu hỏi của người dùng.
        """
        if self.is_running:
            logger.warning("QA đang chạy, không thể bắt đầu mới.")
            return

        if not self._provider_manager or not self._provider_manager.provider:
            self.completed.emit(False, "Chưa cấu hình AI Provider.")
            return

        provider = self._provider_manager.get_provider("qa")
        if not provider:
            self.completed.emit(False, "Không thể khởi tạo model hỏi đáp.")
            return
        self._active_provider = provider
        logger.info("Bắt đầu Q&A với %s (%s)", provider.name, provider.model)

        self._worker = QAWorker(
            summary_context=summary_context,
            qa_history=qa_history,
            question=question,
            provider=provider,
            parent=self,
        )
        self._worker.streaming_text.connect(self.streaming_text)
        self._worker.cost_updated.connect(self.cost_updated)
        self._worker.completed.connect(self._on_completed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def cancel(self) -> None:
        """Hủy Q&A đang chạy."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            logger.info("Đã gửi lệnh hủy Q&A.")

    def _on_completed(self, success: bool, error_msg: str) -> None:
        self.completed.emit(success, error_msg)
        if not success and error_msg and error_msg != "Đã hủy":
            logger.error("Q&A thất bại: %s", sanitize_error(error_msg))

    def _cleanup_worker(self) -> None:
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
        self._active_provider = None
