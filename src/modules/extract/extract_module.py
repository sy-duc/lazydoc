"""ExtractModule — Điều phối extract, quản lý cache và worker thread."""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.modules.extract.extract_worker import ExtractWorker
from src.processors.base import ExtractedContent

logger = logging.getLogger(__name__)


class ExtractModule(QObject):
    """Module điều phối trích xuất nội dung file.

    Quản lý:
    - Cache kết quả extract trong memory (tái sử dụng giữa Summary và Translate).
    - Worker thread (QThread) để không block UI.
    - Hỗ trợ cancel giữa chừng.

    Signals:
        extract_started: Phát khi bắt đầu quá trình extract.
        file_started: Phát khi bắt đầu extract một file (Path).
        file_completed: Phát khi extract xong một file (Path, ExtractedContent).
        file_failed: Phát khi extract thất bại (Path, str lỗi).
        extract_completed: Phát khi toàn bộ quá trình hoàn tất (int thành công, int thất bại).
    """

    extract_started = Signal()
    file_started = Signal(Path)
    file_completed = Signal(Path, ExtractedContent)
    file_failed = Signal(Path, str)
    extract_completed = Signal(int, int)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo ExtractModule."""
        super().__init__(parent)
        self._cache: dict[Path, ExtractedContent] = {}
        self._worker: ExtractWorker | None = None

    @property
    def is_running(self) -> bool:
        """Kiểm tra worker đang chạy hay không."""
        return self._worker is not None and self._worker.isRunning()

    def start_extract(self, files: list[Path]) -> None:
        """Bắt đầu extract danh sách file.

        File đã có trong cache sẽ được trả kết quả ngay mà không extract lại.
        Chỉ các file chưa cache mới được gửi cho worker thread.

        Args:
            files: Danh sách file cần extract.
        """
        if self.is_running:
            logger.warning("Extract đang chạy, không thể bắt đầu mới.")
            return

        # Tách file đã cache và chưa cache
        cached_count = 0
        uncached_files: list[Path] = []

        for file_path in files:
            if file_path in self._cache:
                # Trả kết quả từ cache ngay lập tức
                self.file_completed.emit(file_path, self._cache[file_path])
                cached_count += 1
                logger.info("Cache hit: %s", file_path.name)
            else:
                uncached_files.append(file_path)

        # Nếu tất cả đã cache, kết thúc ngay
        if not uncached_files:
            self.extract_completed.emit(cached_count, 0)
            return

        # Khởi chạy worker cho các file chưa cache
        self.extract_started.emit()
        self._worker = ExtractWorker(uncached_files, self)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.all_completed.connect(
            lambda s, f: self._on_all_completed(s + cached_count, f)
        )
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def cancel(self) -> None:
        """Hủy extract đang chạy. Kết quả đã hoàn thành vẫn được giữ."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            logger.info("Đã gửi lệnh hủy extract.")

    def get_cached(self, file_path: Path) -> ExtractedContent | None:
        """Lấy kết quả extract từ cache.

        Args:
            file_path: Đường dẫn file.

        Returns:
            ExtractedContent nếu có trong cache, None nếu chưa extract.
        """
        return self._cache.get(file_path)

    def get_all_cached(self) -> dict[Path, ExtractedContent]:
        """Lấy toàn bộ cache."""
        return dict(self._cache)

    def invalidate(self, file_path: Path) -> None:
        """Xóa cache của một file (khi file bị xóa khỏi bảng).

        Args:
            file_path: Đường dẫn file cần xóa khỏi cache.
        """
        if file_path in self._cache:
            del self._cache[file_path]
            logger.info("Đã xóa cache: %s", file_path.name)

    def clear_cache(self) -> None:
        """Xóa toàn bộ cache."""
        self._cache.clear()
        logger.info("Đã xóa toàn bộ extract cache.")

    # --- Slots nội bộ ---

    def _on_file_started(self, file_path: Path) -> None:
        """Chuyển tiếp signal file_started."""
        self.file_started.emit(file_path)

    def _on_file_completed(self, file_path: Path, content: ExtractedContent) -> None:
        """Lưu cache và chuyển tiếp signal file_completed."""
        self._cache[file_path] = content
        self.file_completed.emit(file_path, content)

    def _on_file_failed(self, file_path: Path, error_msg: str) -> None:
        """Chuyển tiếp signal file_failed."""
        self.file_failed.emit(file_path, error_msg)

    def _on_all_completed(self, success_count: int, fail_count: int) -> None:
        """Chuyển tiếp signal extract_completed."""
        self.extract_completed.emit(success_count, fail_count)

    def _cleanup_worker(self) -> None:
        """Dọn dẹp worker sau khi kết thúc."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
