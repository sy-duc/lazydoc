"""CsvProcessor — Trích xuất nội dung từ file .csv."""

import csv
import logging
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor

logger = logging.getLogger(__name__)


class CsvProcessor(FileProcessor):
    """Processor cho file CSV (.csv)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def extract(self, file_path: Path) -> ExtractedContent:
        """Đọc file .csv, giữ cấu trúc bảng.

        Args:
            file_path: Đường dẫn file .csv.

        Returns:
            ExtractedContent với tables chứa dữ liệu bảng
            và text_content chứa dạng text readable.
        """
        self.validate_file(file_path)

        # Thử đọc với utf-8, fallback sang latin-1
        try:
            text_raw = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text_raw = file_path.read_text(encoding="latin-1")

        # Detect dialect
        try:
            dialect = csv.Sniffer().sniff(text_raw[:4096])
        except csv.Error:
            dialect = csv.excel

        rows: list[list[str]] = []
        for row in csv.reader(text_raw.splitlines(), dialect=dialect):
            rows.append(row)

        content = ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content={},
            tables={"main": [rows]},
            metadata={"rows": len(rows), "columns": len(rows[0]) if rows else 0},
        )

        logger.info(
            "Đã extract file csv: %s (%d hàng, %d cột)",
            file_path.name, content.metadata["rows"], content.metadata["columns"],
        )
        return content
