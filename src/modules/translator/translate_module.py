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

    Quản lý:
    - Argos Translate engine (dịch offline).
    - Glossary (áp dụng thuật ngữ khi dịch).
    - Worker thread (QThread) để không block UI.
    - Hỗ trợ cancel giữa chừng.

    Signals:
        translate_started: Phát khi bắt đầu quá trình dịch.
        file_started: Phát khi bắt đầu dịch một file (Path).
        file_completed: Phát khi dịch xong một file (Path, Path output).
        file_failed: Phát khi dịch thất bại (Path, str lỗi).
        progress_updated: Phát khi cập nhật tiến độ (int phần trăm).
        translate_completed: Phát khi toàn bộ quá trình hoàn tất
            (int thành công, int thất bại, list[Path] output files).
        error_occurred: Phát khi có lỗi nghiêm trọng (str thông báo lỗi).
    """

    translate_started = Signal()
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
        """Đặt thư mục output.

        Args:
            path: Đường dẫn thư mục.
        """
        self._output_dir = path

    def start_translate(self, config: dict) -> None:
        """Bắt đầu dịch theo cấu hình từ TranslateDialog.

        Args:
            config: Dict cấu hình từ dialog, gồm:
                - files: list[Path] danh sách file cần dịch.
                - target_language: str mã ngôn ngữ đích (vi, en, ja).
                - mode: str chế độ dịch (default, smart).
                - domain: str lĩnh vực (chỉ dùng cho smart mode).
                - style: str văn phong (chỉ dùng cho smart mode).
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

        # Phát hiện ngôn ngữ nguồn từ file đầu tiên
        source_lang = self._detect_source_lang(files[0], target_lang)
        logger.info(
            "Bắt đầu dịch %d file: %s → %s (chế độ: %s)",
            len(files), source_lang, target_lang, mode,
        )

        if mode == "default":
            self._start_argos_translate(files, source_lang, target_lang)
        else:
            # AI mode — chưa triển khai
            self.error_occurred.emit(
                "Chế độ dịch thông minh (AI) chưa được triển khai. "
                "Vui lòng sử dụng chế độ Mặc định."
            )

    def cancel(self) -> None:
        """Hủy dịch đang chạy. File đã dịch xong vẫn được giữ."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            logger.info("Đã gửi lệnh hủy dịch.")

    def _start_argos_translate(
        self,
        files: list[Path],
        source_lang: str,
        target_lang: str,
    ) -> None:
        """Khởi chạy dịch bằng Argos Translate.

        Args:
            files: Danh sách file.
            source_lang: Mã ngôn ngữ nguồn.
            target_lang: Mã ngôn ngữ đích.
        """
        # Đảm bảo model Argos đã cài đặt
        try:
            self._argos.ensure_models(source_lang, target_lang)
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
            return

        # Tạo hàm dịch bind sẵn ngôn ngữ + glossary
        translate_fn = self._argos.create_translate_fn(
            source_lang, target_lang, self._glossary
        )

        # Đảm bảo thư mục output tồn tại
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Khởi chạy worker thread
        self.translate_started.emit()
        self._worker = TranslateWorker(
            files, self._output_dir, translate_fn, target_lang, self
        )
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.file_failed.connect(self._on_file_failed)
        self._worker.progress_updated.connect(self._on_progress_updated)
        self._worker.all_completed.connect(self._on_all_completed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _detect_source_lang(self, file_path: Path, target_lang: str) -> str:
        """Phát hiện ngôn ngữ nguồn từ nội dung file.

        Đọc một mẫu text từ file để phát hiện ngôn ngữ.

        Args:
            file_path: File mẫu.
            target_lang: Ngôn ngữ đích (loại trừ).

        Returns:
            Mã ngôn ngữ phát hiện được.
        """
        sample_text = ""

        try:
            ext = file_path.suffix.lower()

            if ext in (".txt", ".csv"):
                try:
                    sample_text = file_path.read_text(encoding="utf-8")[:2000]
                except UnicodeDecodeError:
                    sample_text = file_path.read_text(encoding="latin-1")[:2000]

            elif ext in (".xlsx", ".xls"):
                from src.processors.factory import ProcessorFactory
                processor = ProcessorFactory.get_processor(file_path)
                content = processor.extract(file_path)
                sample_text = content.get_full_text()[:2000]

            elif ext in (".docx", ".doc"):
                from src.processors.factory import ProcessorFactory
                processor = ProcessorFactory.get_processor(file_path)
                content = processor.extract(file_path)
                sample_text = content.get_full_text()[:2000]

            elif ext in (".pptx", ".ppt"):
                from src.processors.factory import ProcessorFactory
                processor = ProcessorFactory.get_processor(file_path)
                content = processor.extract(file_path)
                sample_text = content.get_full_text()[:2000]

            elif ext == ".pdf":
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    if pdf.pages:
                        sample_text = pdf.pages[0].extract_text() or ""

        except Exception as e:
            logger.warning("Không thể đọc mẫu để phát hiện ngôn ngữ: %s", e)

        detected = self._argos.detect_language(sample_text, exclude_lang=target_lang)
        logger.info("Phát hiện ngôn ngữ nguồn: %s (từ %s)", detected, file_path.name)
        return detected

    # --- Slots nội bộ ---

    def _on_file_started(self, file_path: Path) -> None:
        """Chuyển tiếp signal file_started."""
        self.file_started.emit(file_path)

    def _on_file_completed(self, file_path: Path, output_path: Path) -> None:
        """Chuyển tiếp signal file_completed."""
        self.file_completed.emit(file_path, output_path)

    def _on_file_failed(self, file_path: Path, error_msg: str) -> None:
        """Chuyển tiếp signal file_failed."""
        self.file_failed.emit(file_path, error_msg)

    def _on_progress_updated(self, percent: int) -> None:
        """Chuyển tiếp signal progress_updated."""
        self.progress_updated.emit(percent)

    def _on_all_completed(
        self, success_count: int, fail_count: int, output_files: list
    ) -> None:
        """Chuyển tiếp signal translate_completed."""
        self.translate_completed.emit(success_count, fail_count, output_files)
        logger.info(
            "Dịch hoàn tất: %d thành công, %d thất bại. Output: %s",
            success_count, fail_count, self._output_dir,
        )

    def _cleanup_worker(self) -> None:
        """Dọn dẹp worker sau khi kết thúc."""
        if self._worker:
            self._worker.deleteLater()
            self._worker = None
