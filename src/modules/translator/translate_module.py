"""TranslateModule — Điều phối dịch thuật, quản lý worker thread."""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from src.modules.glossary.glossary_manager import GlossaryManager
from src.modules.translator.argos_engine import ArgosEngine
from src.modules.translator.translate_worker import TranslateWorker

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


class TranslateModule(QObject):
    """Module điều phối dịch thuật.

    Toàn bộ công việc nặng (detect ngôn ngữ, tải model, dịch file)
    đều được đẩy sang worker thread, không block UI.

    Signals:
        translate_started: Phát khi bắt đầu quá trình dịch.
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        file_started: Phát khi bắt đầu dịch một file (Path).
        file_completed: Phát khi dịch xong một file (Path, Path output).
        file_failed: Phát khi dịch thất bại (Path, str lỗi).
        progress_updated: Phát khi cập nhật tiến độ (int phần trăm).
        translate_completed: Phát khi toàn bộ quá trình hoàn tất
            (int thành công, int thất bại, list[Path] output files).
        error_occurred: Phát khi có lỗi nghiêm trọng (str thông báo lỗi).
    """

    translate_started = Signal()
    status_updated = Signal(str)
    file_started = Signal(Path)
    file_completed = Signal(Path, Path)
    file_failed = Signal(Path, str)
    progress_updated = Signal(int)
    translate_completed = Signal(int, int, list)
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo TranslateModule."""
        super().__init__(parent)
        self._argos = ArgosEngine()
        self._glossary = GlossaryManager()
        self._worker: TranslateWorker | None = None
        self._output_dir = _get_downloads_dir()

    @property
    def is_running(self) -> bool:
        """Kiểm tra worker đang chạy hay không."""
        return self._worker is not None and self._worker.isRunning()

    @property
    def output_dir(self) -> Path:
        """Thư mục output hiện tại."""
        return self._output_dir

    @output_dir.setter
    def output_dir(self, path: Path) -> None:
        """Đặt thư mục output."""
        self._output_dir = path

    def start_translate(self, config: dict) -> None:
        """Bắt đầu dịch theo cấu hình từ TranslateDialog.

        Chỉ validate nhanh rồi đẩy toàn bộ công việc nặng sang worker thread.

        Args:
            config: Dict cấu hình từ dialog.
        """
        if self.is_running:
            logger.warning("Dịch đang chạy, không thể bắt đầu mới.")
            return

        files: list[Path] = config["files"]
        target_lang: str = config["target_language"]
        mode: str = config.get("mode", "default")

        if not files:
            self.error_occurred.emit("Không có file nào để dịch.")
            return

        if mode != "default":
            self.error_occurred.emit(
                "Chế độ dịch thông minh (AI) chưa được triển khai. "
                "Vui lòng sử dụng chế độ Mặc định."
            )
            return

        logger.info("Bắt đầu dịch %d file sang %s (chế độ: %s)", len(files), target_lang, mode)

        # Đảm bảo thư mục output tồn tại
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Khởi chạy worker — toàn bộ công việc nặng chạy trên thread riêng
        self.translate_started.emit()
        self._worker = TranslateWorker(
            files=files,
            output_dir=self._output_dir,
            target_lang=target_lang,
            argos_engine=self._argos,
            glossary_manager=self._glossary,
            parent=self,
        )
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.progress_updated.connect(self._on_progress_updated)
        self._worker.all_completed.connect(self._on_all_completed)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def cancel(self) -> None:
        """Hủy dịch đang chạy. File đã dịch xong vẫn được giữ."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            logger.info("Đã gửi lệnh hủy dịch.")

    # --- Slots nội bộ ---

    def _on_status_updated(self, msg: str) -> None:
        self.status_updated.emit(msg)

    def _on_file_started(self, file_path: Path) -> None:
        self.file_started.emit(file_path)

    def _on_file_completed(self, file_path: Path, output_path: Path) -> None:
        self.file_completed.emit(file_path, output_path)

    def _on_file_failed(self, file_path: Path, error_msg: str) -> None:
        self.file_failed.emit(file_path, error_msg)

    def _on_progress_updated(self, percent: int) -> None:
        self.progress_updated.emit(percent)

    def _on_all_completed(
        self, success_count: int, fail_count: int, output_files: list
    ) -> None:
        self.translate_completed.emit(success_count, fail_count, output_files)
        logger.info(
            "Dịch hoàn tất: %d thành công, %d thất bại. Output: %s",
            success_count, fail_count, self._output_dir,
        )

    def _on_error(self, msg: str) -> None:
        self.error_occurred.emit(msg)

    def _cleanup_worker(self) -> None:
        """Dọn dẹp worker sau khi kết thúc."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
