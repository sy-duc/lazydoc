"""TxtProcessor — Trích xuất nội dung từ file .txt."""

import logging
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor

logger = logging.getLogger(__name__)


class TxtProcessor(FileProcessor):
    """Processor cho file văn bản thuần (.txt)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def extract(self, file_path: Path) -> ExtractedContent:
        """Đọc toàn bộ nội dung file .txt.

        Args:
            file_path: Đường dẫn file .txt.

        Returns:
            ExtractedContent với text_content chứa nội dung file.
        """
        self.validate_file(file_path)

        # Thử đọc với utf-8, fallback sang latin-1
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file_path.read_text(encoding="latin-1")
            logger.warning("File %s không phải UTF-8, đọc bằng latin-1.", file_path.name)

        content = ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content={"main": text},
            metadata={"encoding": "utf-8", "lines": text.count("\n") + 1},
        )

        logger.info("Đã extract file txt: %s (%d dòng)", file_path.name, content.metadata["lines"])
        return content
