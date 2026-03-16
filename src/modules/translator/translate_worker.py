"""TranslateWorker — Worker thread cho việc dịch file."""

import logging
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)


class TranslateWorker(QThread):
    """Worker chạy trên thread riêng để dịch file không block UI.

    Signals:
        file_started: Phát khi bắt đầu dịch một file (Path).
        file_completed: Phát khi dịch xong một file (Path, Path output).
        file_failed: Phát khi dịch thất bại (Path, str lỗi).
        progress_updated: Phát khi cập nhật tiến độ (int phần trăm).
        all_completed: Phát khi toàn bộ file đã xử lý xong (int thành công, int thất bại, list[Path] output).
    """

    file_started = Signal(Path)
    file_completed = Signal(Path, Path)
    file_failed = Signal(Path, str)
    progress_updated = Signal(int)
    all_completed = Signal(int, int, list)

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        translate_fn: Callable[[str], str],
        target_lang: str,
        parent: object = None,
    ) -> None:
        """Khởi tạo TranslateWorker.

        Args:
            files: Danh sách file cần dịch.
            output_dir: Thư mục đầu ra (Downloads).
            translate_fn: Hàm dịch đã bind sẵn ngôn ngữ + glossary.
            target_lang: Mã ngôn ngữ đích (dùng cho tên file).
            parent: QObject cha.
        """
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._translate_fn = translate_fn
        self._target_lang = target_lang
        self._cancelled = False

    def run(self) -> None:
        """Thực thi dịch từng file trên worker thread."""
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

            try:
                writer = WriterFactory.get_writer(file_path)

                # Tạo tên file output (dịch tên file)
                output_path = self._make_output_path(file_path)

                # Dịch và ghi file
                writer.write_translated(file_path, output_path, self._translate_fn)

                # Xác định file output thực tế (có thể đổi extension)
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

            # Cập nhật tiến độ
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

    def _make_output_path(self, source_path: Path) -> Path:
        """Tạo đường dẫn output — dịch tên file.

        Args:
            source_path: Đường dẫn file gốc.

        Returns:
            Đường dẫn file output trong thư mục Downloads.
        """
        stem = source_path.stem
        ext = source_path.suffix

        # Dịch tên file
        translated_name = self._translate_fn(stem)
        # Loại bỏ ký tự không hợp lệ trong tên file
        translated_name = self._sanitize_filename(translated_name)

        output_path = self._output_dir / f"{translated_name}{ext}"

        # Tránh trùng tên
        counter = 1
        while output_path.exists():
            output_path = self._output_dir / f"{translated_name} ({counter}){ext}"
            counter += 1

        return output_path

    def _find_actual_output(self, expected_path: Path) -> Path:
        """Tìm file output thực tế (extension có thể thay đổi).

        Một số writer đổi extension (vd: .xls → .xlsx, .doc → .docx, .pdf → .txt).
        """
        if expected_path.exists():
            return expected_path

        # Thử các extension thay thế
        alternatives = [".xlsx", ".docx", ".pptx", ".txt"]
        for alt_ext in alternatives:
            alt_path = expected_path.with_suffix(alt_ext)
            if alt_path.exists():
                return alt_path

        return expected_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Loại bỏ ký tự không hợp lệ trong tên file.

        Args:
            name: Tên file cần xử lý.

        Returns:
            Tên file đã loại bỏ ký tự không hợp lệ.
        """
        import re
        # Loại bỏ ký tự không hợp lệ trên Windows/Linux
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        # Trim whitespace
        sanitized = sanitized.strip()
        # Nếu rỗng, dùng tên mặc định
        if not sanitized:
            sanitized = "translated"
        return sanitized
