"""ExtractWorker — Worker thread cho việc trích xuất nội dung file."""

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from src.core.logging_config import safe_file_label, sanitize_error
from src.processors.base import ExtractedContent
from src.processors.factory import ProcessorFactory

logger = logging.getLogger(__name__)


class ExtractWorker(QThread):
    """Worker chạy trên thread riêng để extract file không block UI.

    Signals:
        file_started: Phát khi bắt đầu extract một file (Path).
        file_completed: Phát khi extract xong một file (Path, ExtractedContent).
        file_failed: Phát khi extract thất bại (Path, str lỗi).
        all_completed: Phát khi toàn bộ file đã xử lý xong (int thành công, int thất bại).
    """

    file_started = Signal(Path)
    file_completed = Signal(Path, ExtractedContent)
    file_failed = Signal(Path, str)
    all_completed = Signal(int, int)

    def __init__(self, files: list[Path], parent: object = None) -> None:
        """Khởi tạo ExtractWorker.

        Args:
            files: Danh sách file cần extract.
            parent: QObject cha.
        """
        super().__init__(parent)
        self._files = files
        self._cancelled = False

    def run(self) -> None:
        """Thực thi extract từng file trên worker thread."""
        success_count = 0
        fail_count = 0

        for file_path in self._files:
            if self._cancelled:
                logger.info("Extract bị hủy bởi người dùng.")
                break

            self.file_started.emit(file_path)

            try:
                processor = ProcessorFactory.get_processor(file_path)
                content = processor.extract(file_path)
                self.file_completed.emit(file_path, content)
                success_count += 1
                logger.info("Extract thành công: %s", safe_file_label(file_path))

            except Exception as e:
                error_msg = str(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error(
                    "Extract thất bại: %s - %s",
                    safe_file_label(file_path),
                    sanitize_error(e),
                )

        self.all_completed.emit(success_count, fail_count)

    def cancel(self) -> None:
        """Yêu cầu hủy extract. Worker sẽ dừng sau file đang xử lý."""
        self._cancelled = True
        logger.info("Đã yêu cầu hủy extract.")

    @property
    def is_cancelled(self) -> bool:
        """Kiểm tra worker đã bị hủy chưa."""
        return self._cancelled
