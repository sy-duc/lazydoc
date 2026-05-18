"""TxtWriter — Ghi file .txt đã dịch."""

import logging
from pathlib import Path
from typing import Callable

from src.core.logging_config import safe_file_label
from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class TxtWriter(FileWriter):
    """Writer cho file văn bản thuần (.txt)."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".txt", ".md"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .txt theo từng đoạn (paragraph).

        Mỗi đoạn được phân tách bởi dòng trống sẽ được dịch riêng,
        giữ nguyên cấu trúc dòng trống.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch.
        """
        try:
            text = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = source_path.read_text(encoding="latin-1")

        # Tách theo đoạn (dòng trống), dịch từng đoạn
        paragraphs = text.split("\n\n")
        translated_parts: list[str] = []

        for para in paragraphs:
            if para.strip():
                translated_parts.append(translate_fn(para))
            else:
                translated_parts.append(para)

        output_path.write_text("\n\n".join(translated_parts), encoding="utf-8")
        logger.info("Đã ghi file txt: %s", safe_file_label(output_path))
