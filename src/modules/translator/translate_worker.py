"""TranslateWorker — Worker thread cho việc dịch file."""

import logging
import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal

from src.modules.translator.argos_engine import ArgosEngine

logger = logging.getLogger(__name__)


class TranslateWorker(QThread):
    """Worker chạy trên thread riêng để dịch file không block UI.

    Toàn bộ công việc nặng (detect ngôn ngữ, tải model, dịch file)
    đều chạy trên thread này, không block UI.

    Signals:
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        file_started: Phát khi bắt đầu dịch một file (Path).
        file_completed: Phát khi dịch xong một file (Path, Path output).
        file_failed: Phát khi dịch thất bại (Path, str lỗi).
        progress_updated: Phát khi cập nhật tiến độ (int phần trăm).
        all_completed: Phát khi toàn bộ file đã xử lý xong
            (int thành công, int thất bại, list[Path] output).
        error_occurred: Phát khi có lỗi nghiêm trọng (str thông báo).
    """

    status_updated = Signal(str)
    file_started = Signal(Path)
    file_completed = Signal(Path, Path)
    file_failed = Signal(Path, str)
    progress_updated = Signal(int)
    all_completed = Signal(int, int, list)
    error_occurred = Signal(str)

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        target_lang: str,
        argos_engine: ArgosEngine,
        glossary_manager: object | None = None,
        parent: object = None,
    ) -> None:
        """Khởi tạo TranslateWorker.

        Args:
            files: Danh sách file cần dịch.
            output_dir: Thư mục đầu ra (Downloads).
            target_lang: Mã ngôn ngữ đích.
            argos_engine: ArgosEngine instance.
            glossary_manager: GlossaryManager instance (tuỳ chọn).
            parent: QObject cha.
        """
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._target_lang = target_lang
        self._argos = argos_engine
        self._glossary = glossary_manager
        self._cancelled = False

    def run(self) -> None:
        """Thực thi toàn bộ pipeline dịch trên worker thread.

        Pipeline: detect ngôn ngữ → tải model → dịch từng file → ghi output.
        """
        # Bước 1: Phát hiện ngôn ngữ nguồn
        self.status_updated.emit("Đang phát hiện ngôn ngữ...")
        source_lang = self._detect_source_lang(self._files[0], self._target_lang)
        logger.info("Phát hiện ngôn ngữ nguồn: %s", source_lang)

        if self._cancelled:
            return

        # Bước 2: Đảm bảo model Argos đã cài đặt
        self.status_updated.emit("Đang chuẩn bị model dịch...")
        try:
            self._argos.ensure_models(source_lang, self._target_lang)
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
            return

        if self._cancelled:
            return

        # Bước 3: Tạo hàm dịch
        translate_fn = self._argos.create_translate_fn(
            source_lang, self._target_lang, self._glossary
        )

        # Bước 4: Dịch từng file
        self._translate_files(translate_fn)

    def _translate_files(self, translate_fn: Callable[[str], str]) -> None:
        """Dịch từng file và ghi output."""
        from src.writers.factory import WriterFactory

        success_count = 0
        fail_count = 0
        output_files: list[Path] = []
        total = len(self._files)

        for idx, file_path in enumerate(self._files):
            if self._cancelled:
                logger.info("Dịch bị hủy bởi người dùng.")
                break

            self.file_started.emit(file_path)
            self.status_updated.emit(f"Đang dịch: {file_path.name}")

            try:
                writer = WriterFactory.get_writer(file_path)
                output_path = self._make_output_path(file_path, translate_fn)
                writer.write_translated(file_path, output_path, translate_fn)

                actual_output = self._find_actual_output(output_path)
                self.file_completed.emit(file_path, actual_output)
                output_files.append(actual_output)
                success_count += 1
                logger.info("Dịch thành công: %s → %s", file_path.name, actual_output.name)

            except Exception as e:
                error_msg = str(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error("Dịch thất bại: %s — %s", file_path.name, e)

            percent = int((idx + 1) / total * 100)
            self.progress_updated.emit(percent)

        self.all_completed.emit(success_count, fail_count, output_files)

    def cancel(self) -> None:
        """Yêu cầu hủy dịch. Worker sẽ dừng sau file đang xử lý."""
        self._cancelled = True
        logger.info("Đã yêu cầu hủy dịch.")

    @property
    def is_cancelled(self) -> bool:
        """Kiểm tra worker đã bị hủy chưa."""
        return self._cancelled

    def _detect_source_lang(self, file_path: Path, target_lang: str) -> str:
        """Phát hiện ngôn ngữ nguồn từ nội dung file (chạy trên worker thread).

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

            elif ext in (".xlsx", ".xls", ".docx", ".doc", ".pptx", ".ppt"):
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

    def _make_output_path(
        self, source_path: Path, translate_fn: Callable[[str], str]
    ) -> Path:
        """Tạo đường dẫn output — dịch tên file.

        Args:
            source_path: Đường dẫn file gốc.
            translate_fn: Hàm dịch.

        Returns:
            Đường dẫn file output trong thư mục Downloads.
        """
        stem = source_path.stem
        ext = source_path.suffix

        translated_name = translate_fn(stem)
        translated_name = self._sanitize_filename(translated_name)

        output_path = self._output_dir / f"{translated_name}{ext}"

        counter = 1
        while output_path.exists():
            output_path = self._output_dir / f"{translated_name} ({counter}){ext}"
            counter += 1

        return output_path

    def _find_actual_output(self, expected_path: Path) -> Path:
        """Tìm file output thực tế (extension có thể thay đổi)."""
        if expected_path.exists():
            return expected_path

        alternatives = [".xlsx", ".docx", ".pptx", ".txt"]
        for alt_ext in alternatives:
            alt_path = expected_path.with_suffix(alt_ext)
            if alt_path.exists():
                return alt_path

        return expected_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Loại bỏ ký tự không hợp lệ trong tên file."""
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "translated"
        return sanitized
