"""SummaryModule — Điều phối tổng hợp thông tin, quản lý worker thread."""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.modules.summarizer.summary_worker import SummaryWorker
from src.processors.base import ExtractedContent

logger = logging.getLogger(__name__)


def _get_downloads_dir() -> Path:
    """Lấy thư mục Downloads của người dùng.

    Returns:
        Đường dẫn đến thư mục Downloads.
    """
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path.home() / "Tải xuống"
    if not downloads.exists():
        downloads = Path.home()
    return downloads


class SummaryModule(QObject):
    """Module điều phối tổng hợp thông tin từ tài liệu.

    Quản lý:
    - Worker thread để gọi AI không block UI.
    - Forward signal từ worker lên UI layer.
    - Hỗ trợ cancel giữa chừng.

    Signals:
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        streaming_text: Phát text streaming cho UI typing effect (str chunk).
        file_info_ready: Phát thông tin từng file (str tên_file, str ý_nghĩa, str ngôn_ngữ).
        detail_file_ready: Phát đường dẫn file .md (str path).
        cost_updated: Phát token usage kèm thông tin provider
            (str provider_name, str model, int input_tokens, int output_tokens).
        summary_completed: Phát khi hoàn tất (bool thành_công, str lỗi).
    """

    status_updated = Signal(str)
    streaming_text = Signal(str)
    file_info_ready = Signal(str, str, str)
    detail_file_ready = Signal(str)
    cost_updated = Signal(str, str, int, int)
    summary_completed = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo SummaryModule."""
        super().__init__(parent)
        self._worker: SummaryWorker | None = None
        self._output_dir = _get_downloads_dir()
        self._provider_manager = None

    @property
    def is_running(self) -> bool:
        """Kiểm tra worker đang chạy hay không."""
        return self._worker is not None and self._worker.isRunning()

    @property
    def output_dir(self) -> Path:
        """Thư mục output hiện tại."""
        return self._output_dir

    def set_provider_manager(self, provider_manager: object) -> None:
        """Đặt ProviderManager để lấy AI provider.

        Args:
            provider_manager: ProviderManager instance.
        """
        self._provider_manager = provider_manager

    def start_summary(self, contents: dict[Path, ExtractedContent]) -> None:
        """Bắt đầu tổng hợp thông tin từ các file đã extract.

        Validate provider, tạo worker và khởi chạy trên thread riêng.

        Args:
            contents: Dict {file_path: ExtractedContent} từ extract cache.
        """
        if self.is_running:
            logger.warning("Tổng hợp đang chạy, không thể bắt đầu mới.")
            return

        if not contents:
            self.summary_completed.emit(False, "Không có nội dung để tổng hợp.")
            return

        # Validate provider
        if not self._provider_manager or not self._provider_manager.provider:
            self.summary_completed.emit(
                False,
                "Chưa cấu hình AI Provider. Vào Cài đặt để thêm API key.",
            )
            return

        provider = self._provider_manager.provider
        logger.info(
            "Bắt đầu tổng hợp %d file với %s (%s)",
            len(contents), provider.name, provider.model,
        )

        # Khởi chạy worker
        self._worker = SummaryWorker(
            contents=contents,
            provider=provider,
            parent=self,
        )
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.streaming_text.connect(self._on_streaming_text)
        self._worker.file_info_ready.connect(self._on_file_info_ready)
        self._worker.detail_file_ready.connect(self._on_detail_file_ready)
        self._worker.cost_updated.connect(self._on_cost_updated)
        self._worker.completed.connect(self._on_completed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def cancel(self) -> None:
        """Hủy tổng hợp đang chạy. Kết quả đã hoàn thành vẫn được giữ."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            logger.info("Đã gửi lệnh hủy tổng hợp.")

    # --- Slots nội bộ: forward signal từ worker ---

    def _on_status_updated(self, msg: str) -> None:
        self.status_updated.emit(msg)

    def _on_streaming_text(self, text: str) -> None:
        self.streaming_text.emit(text)

    def _on_file_info_ready(
        self, file_name: str, purpose: str, language: str
    ) -> None:
        self.file_info_ready.emit(file_name, purpose, language)

    def _on_detail_file_ready(self, md_path: str) -> None:
        self.detail_file_ready.emit(md_path)

    def _on_cost_updated(self, input_tokens: int, output_tokens: int) -> None:
        """Forward cost update từ worker, kèm thông tin provider/model."""
        if self._provider_manager and self._provider_manager.provider:
            provider = self._provider_manager.provider
            self.cost_updated.emit(
                provider.name, provider.model,
                input_tokens, output_tokens,
            )

    def _on_completed(self, success: bool, error_msg: str) -> None:
        self.summary_completed.emit(success, error_msg)
        if success:
            logger.info("Tổng hợp hoàn tất thành công.")
        elif error_msg:
            logger.error("Tổng hợp thất bại: %s", error_msg)

    def _cleanup_worker(self) -> None:
        """Dọn dẹp worker sau khi kết thúc."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
