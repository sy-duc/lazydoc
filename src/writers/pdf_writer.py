"""PdfWriter — Ghi file PDF đã dịch (xuất ra .txt vì PDF không ghi lại được dễ dàng)."""

import logging
from pathlib import Path
from typing import Callable

from src.core.logging_config import safe_file_label
from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class PdfWriter(FileWriter):
    """Writer cho file PDF (.pdf).

    PDF không thể ghi lại giữ nguyên định dạng gốc một cách đơn giản.
    Giải pháp: extract text → dịch → xuất ra file .txt.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch nội dung PDF và xuất ra file .txt.

        Args:
            source_path: Đường dẫn file PDF gốc.
            output_path: Đường dẫn file đầu ra (.txt).
            translate_fn: Hàm dịch.
        """
        import pdfplumber

        translated_parts: list[str] = []

        with pdfplumber.open(source_path) as pdf:
            for page_idx, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    translated = translate_fn(page_text)
                    translated_parts.append(
                        f"--- Trang {page_idx} ---\n{translated}"
                    )

                # Dịch bảng
                for tbl_idx, table in enumerate(page.extract_tables()):
                    table_lines: list[str] = []
                    for row in table:
                        translated_row = []
                        for cell in row:
                            if cell and cell.strip():
                                translated_row.append(translate_fn(cell))
                            else:
                                translated_row.append(cell or "")
                        table_lines.append("\t".join(translated_row))
                    if table_lines:
                        translated_parts.append(
                            f"[Bảng {tbl_idx + 1}]\n" + "\n".join(table_lines)
                        )

        # Xuất ra .txt
        actual_output = output_path.with_suffix(".txt")
        actual_output.write_text("\n\n".join(translated_parts), encoding="utf-8")
        logger.info(
            "Đã ghi file pdf -> txt: %s (%d phần)",
            safe_file_label(actual_output), len(translated_parts),
        )
