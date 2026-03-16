"""WriterFactory — Factory tạo writer phù hợp theo loại file."""

import logging
from pathlib import Path

from src.writers.base import FileWriter

logger = logging.getLogger(__name__)

# Mapping extension → (module_path, class_name) — lazy import
_WRITER_REGISTRY: dict[str, tuple[str, str]] = {
    ".txt": ("src.writers.txt_writer", "TxtWriter"),
    ".csv": ("src.writers.csv_writer", "CsvWriter"),
    ".xlsx": ("src.writers.excel_writer", "ExcelWriter"),
    ".xls": ("src.writers.excel_writer", "ExcelWriter"),
    ".docx": ("src.writers.word_writer", "WordWriter"),
    ".doc": ("src.writers.word_writer", "WordWriter"),
    ".pptx": ("src.writers.powerpoint_writer", "PowerPointWriter"),
    ".ppt": ("src.writers.powerpoint_writer", "PowerPointWriter"),
    ".pdf": ("src.writers.pdf_writer", "PdfWriter"),
}


class WriterFactory:
    """Factory tạo FileWriter phù hợp theo extension file."""

    @staticmethod
    def get_writer(file_path: Path) -> FileWriter:
        """Lấy writer phù hợp cho file.

        Args:
            file_path: Đường dẫn file cần ghi.

        Returns:
            FileWriter instance.

        Raises:
            ValueError: Nếu không hỗ trợ loại file.
        """
        ext = file_path.suffix.lower()
        if ext not in _WRITER_REGISTRY:
            raise ValueError(
                f"Không hỗ trợ ghi file định dạng '{ext}'. "
                f"Các định dạng hỗ trợ: {list(_WRITER_REGISTRY.keys())}"
            )

        module_path, class_name = _WRITER_REGISTRY[ext]

        import importlib
        module = importlib.import_module(module_path)
        writer_class = getattr(module, class_name)
        return writer_class()

    @staticmethod
    def is_supported(file_path: Path) -> bool:
        """Kiểm tra file có được hỗ trợ ghi không.

        Args:
            file_path: Đường dẫn file.

        Returns:
            True nếu extension được hỗ trợ.
        """
        return file_path.suffix.lower() in _WRITER_REGISTRY

    @staticmethod
    def get_supported_extensions() -> list[str]:
        """Lấy danh sách extension được hỗ trợ."""
        return list(_WRITER_REGISTRY.keys())
