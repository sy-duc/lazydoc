"""File Processor Factory — Tạo processor phù hợp theo extension file."""

import logging
from pathlib import Path

from src.processors.base import FileProcessor

logger = logging.getLogger(__name__)

# Định dạng file được hỗ trợ, nhóm theo loại processor
SUPPORTED_EXTENSIONS: dict[str, list[str]] = {
    "txt": [".txt"],
    "csv": [".csv"],
    "excel": [".xlsx", ".xls"],
    "word": [".docx", ".doc"],
    "powerpoint": [".pptx", ".ppt"],
    "pdf": [".pdf"],
    "image": [".png", ".jpg", ".jpeg", ".bmp", ".gif"],
}


class ProcessorFactory:
    """Factory tạo File Processor phù hợp theo extension file.

    Sử dụng lazy import để chỉ load processor khi cần,
    tránh import toàn bộ thư viện xử lý file khi khởi động.
    """

    # Mapping extension → tên processor type
    _extension_map: dict[str, str] = {}

    @classmethod
    def _build_extension_map(cls) -> None:
        """Xây dựng mapping từ extension → processor type."""
        if cls._extension_map:
            return
        for processor_type, extensions in SUPPORTED_EXTENSIONS.items():
            for ext in extensions:
                cls._extension_map[ext] = processor_type

    @classmethod
    def _create_processor(cls, processor_type: str) -> FileProcessor:
        """Lazy import và tạo instance processor theo type.

        Args:
            processor_type: Loại processor (txt, csv, excel, ...).

        Returns:
            Instance của FileProcessor tương ứng.

        Raises:
            ValueError: Nếu processor_type chưa được triển khai.
        """
        if processor_type == "txt":
            from src.processors.txt_processor import TxtProcessor
            return TxtProcessor()
        elif processor_type == "csv":
            from src.processors.csv_processor import CsvProcessor
            return CsvProcessor()
        elif processor_type == "excel":
            from src.processors.excel_processor import ExcelProcessor
            return ExcelProcessor()
        elif processor_type == "word":
            from src.processors.word_processor import WordProcessor
            return WordProcessor()
        elif processor_type == "powerpoint":
            from src.processors.powerpoint_processor import PowerPointProcessor
            return PowerPointProcessor()
        elif processor_type == "pdf":
            from src.processors.pdf_processor import PdfProcessor
            return PdfProcessor()
        elif processor_type == "image":
            from src.processors.image_processor import ImageProcessor
            return ImageProcessor()
        else:
            raise ValueError(f"Processor type chưa được triển khai: {processor_type}")

    @classmethod
    def get_processor(cls, file_path: Path | str) -> FileProcessor:
        """Nhận file path, trả về processor phù hợp theo extension.

        Args:
            file_path: Đường dẫn file cần xử lý.

        Returns:
            Instance của FileProcessor có thể xử lý file.

        Raises:
            ValueError: Nếu extension file không được hỗ trợ.
        """
        cls._build_extension_map()
        path = Path(file_path)
        ext = path.suffix.lower()

        processor_type = cls._extension_map.get(ext)
        if processor_type is None:
            supported = sorted(cls._extension_map.keys())
            raise ValueError(
                f"Định dạng '{ext}' không được hỗ trợ. "
                f"Các định dạng hỗ trợ: {', '.join(supported)}"
            )

        logger.debug("Tạo %s processor cho file: %s", processor_type, path.name)
        return cls._create_processor(processor_type)

    @classmethod
    def is_supported(cls, file_path: Path | str) -> bool:
        """Kiểm tra file có được hỗ trợ không.

        Args:
            file_path: Đường dẫn file cần kiểm tra.

        Returns:
            True nếu extension file nằm trong danh sách hỗ trợ.
        """
        cls._build_extension_map()
        ext = Path(file_path).suffix.lower()
        return ext in cls._extension_map

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Trả về danh sách tất cả extension được hỗ trợ.

        Returns:
            List các extension (đã sắp xếp).
        """
        cls._build_extension_map()
        return sorted(cls._extension_map.keys())
