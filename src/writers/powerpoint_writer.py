"""PowerPointWriter — Ghi file PowerPoint đã dịch, giữ nguyên định dạng gốc."""

import logging
from pathlib import Path
from typing import Callable

from src.core.logging_config import safe_file_label
from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class PowerPointWriter(FileWriter):
    """Writer cho file PowerPoint (.pptx, .ppt).

    Giữ nguyên: layout, hình ảnh, biểu đồ, animations, transitions.
    Dịch: text frames (title, body, textbox), table cells, speaker notes.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pptx", ".ppt"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file PowerPoint giữ nguyên định dạng.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch.
        """
        ext = source_path.suffix.lower()
        if ext == ".ppt":
            self._write_ppt(source_path, output_path, translate_fn)
        else:
            self._write_pptx(source_path, output_path, translate_fn)

    def _write_pptx(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .pptx bằng python-pptx — giữ nguyên formatting ở cấp run."""
        from pptx import Presentation

        prs = Presentation(source_path)

        for slide in prs.slides:
            for shape in self._iter_shapes(slide.shapes):
                # Dịch text frame
                if shape.has_text_frame:
                    self._translate_text_frame(shape.text_frame, translate_fn)

                # Dịch bảng
                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            self._translate_text_frame(cell.text_frame, translate_fn)

            # Dịch speaker notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                self._translate_text_frame(
                    slide.notes_slide.notes_text_frame, translate_fn
                )

        prs.save(output_path)
        logger.info("Đã ghi file pptx: %s", safe_file_label(output_path))

    def _iter_shapes(self, shapes: "pptx.shapes.shapetree.SlideShapes"):
        """Duyệt tất cả shapes bao gồm group shapes (đệ quy).

        Args:
            shapes: Collection shapes.

        Yields:
            Từng shape đơn lẻ.
        """
        for shape in shapes:
            yield shape
            if shape.shape_type is not None and shape.shape_type == 6:
                try:
                    yield from self._iter_shapes(shape.shapes)
                except Exception:
                    pass

    def _translate_text_frame(
        self,
        text_frame: "pptx.util.TextFrame",
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch một text frame, giữ nguyên formatting ở cấp paragraph/run.

        Mỗi paragraph được dịch riêng. Text dịch gán vào run đầu tiên,
        xoá text các run còn lại.
        """
        for para in text_frame.paragraphs:
            runs = para.runs
            if not runs:
                continue

            full_text = "".join(r.text for r in runs)
            if not full_text.strip():
                continue

            translated = translate_fn(full_text)

            runs[0].text = translated
            for run in runs[1:]:
                run.text = ""

    def _write_ppt(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .ppt — chuyển sang .pptx trước bằng LibreOffice.

        Output luôn là .pptx vì python-pptx không ghi được .ppt.
        """
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.run(
                    [
                        "libreoffice", "--headless", "--convert-to", "pptx",
                        str(source_path), "--outdir", tmp_dir,
                    ],
                    capture_output=True, timeout=60, check=True,
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "Cần cài LibreOffice để xử lý file .ppt. "
                    "Vui lòng cài đặt hoặc chuyển file sang .pptx."
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    f"Chuyển đổi file .ppt quá lâu (>60s): {source_path.name}"
                )

            pptx_path = Path(tmp_dir) / source_path.with_suffix(".pptx").name
            if not pptx_path.exists():
                raise RuntimeError(
                    f"Không thể chuyển đổi file .ppt: {source_path.name}"
                )

            actual_output = output_path.with_suffix(".pptx")
            self._write_pptx(pptx_path, actual_output, translate_fn)
