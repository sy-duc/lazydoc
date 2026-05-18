"""CsvWriter — Ghi file .csv đã dịch."""

import csv
import logging
from pathlib import Path
from typing import Callable

from src.core.logging_config import safe_file_label
from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class CsvWriter(FileWriter):
    """Writer cho file CSV (.csv)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .csv giữ nguyên cấu trúc bảng.

        Dịch từng cell, giữ nguyên delimiter và cấu trúc hàng/cột.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch.
        """
        try:
            text_raw = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text_raw = source_path.read_text(encoding="latin-1")

        # Detect dialect gốc
        try:
            dialect = csv.Sniffer().sniff(text_raw[:4096])
        except csv.Error:
            dialect = csv.excel

        rows: list[list[str]] = []
        for row in csv.reader(text_raw.splitlines(), dialect=dialect):
            translated_row = []
            for cell in row:
                if cell.strip():
                    translated_row.append(translate_fn(cell))
                else:
                    translated_row.append(cell)
            rows.append(translated_row)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, dialect=dialect)
            writer.writerows(rows)

        logger.info("Đã ghi file csv: %s (%d hàng)", safe_file_label(output_path), len(rows))
