"""WordWriter — Ghi file Word đã dịch, giữ nguyên định dạng gốc."""

import logging
from pathlib import Path
from typing import Callable

from src.core.logging_config import safe_file_label, sanitize_error
from src.writers.base import FileWriter

logger = logging.getLogger(__name__)


class WordWriter(FileWriter):
    """Writer cho file Word (.docx, .doc).

    Giữ nguyên: styles (bold, italic, font, ...), hình ảnh, page layout.
    Dịch: paragraphs, tables, textbox/shapes.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]

    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file Word giữ nguyên định dạng.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch.
        """
        ext = source_path.suffix.lower()
        if ext == ".doc":
            self._write_doc(source_path, output_path, translate_fn)
        else:
            self._write_docx(source_path, output_path, translate_fn)

    def _write_docx(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .docx bằng python-docx — giữ nguyên formatting ở cấp run."""
        import docx

        doc = docx.Document(source_path)

        # Dịch paragraphs
        for para in doc.paragraphs:
            self._translate_paragraph(para, translate_fn)

        # Dịch tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        self._translate_paragraph(para, translate_fn)

        # Dịch headers và footers
        for section in doc.sections:
            for header in [section.header, section.first_page_header, section.even_page_header]:
                if header and header.is_linked_to_previous is False:
                    for para in header.paragraphs:
                        self._translate_paragraph(para, translate_fn)
            for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
                if footer and footer.is_linked_to_previous is False:
                    for para in footer.paragraphs:
                        self._translate_paragraph(para, translate_fn)

        # Dịch text trong shapes/textboxes (XML)
        self._translate_shapes_docx(doc, translate_fn)

        doc.save(output_path)
        logger.info("Đã ghi file docx: %s", safe_file_label(output_path))

    def _translate_paragraph(
        self,
        para: "docx.text.paragraph.Paragraph",
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch một paragraph, giữ nguyên formatting của run đầu tiên.

        Ghép text từ tất cả runs → dịch → gán vào run đầu tiên → xoá text runs còn lại.
        """
        runs = para.runs
        if not runs:
            return

        full_text = "".join(r.text for r in runs)
        if not full_text.strip():
            return

        translated = translate_fn(full_text)

        # Gán text dịch vào run đầu tiên (giữ formatting)
        runs[0].text = translated
        # Xoá text các run còn lại
        for run in runs[1:]:
            run.text = ""

    def _translate_shapes_docx(
        self,
        doc: "docx.Document",
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch text trong shapes/textboxes bằng XML manipulation."""
        from lxml import etree

        nsmap = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        }

        try:
            body = doc.element.body

            # Tìm tất cả textbox (wps:txbx)
            for txbx in body.iter(f'{{{nsmap["wps"]}}}txbx'):
                for p_elem in txbx.iter(f'{{{nsmap["w"]}}}p'):
                    texts = []
                    r_elements = []
                    for r in p_elem.iter(f'{{{nsmap["w"]}}}r'):
                        for t in r.iter(f'{{{nsmap["w"]}}}t'):
                            if t.text:
                                texts.append(t.text)
                                r_elements.append(t)

                    full_text = "".join(texts)
                    if full_text.strip() and r_elements:
                        translated = translate_fn(full_text)
                        r_elements[0].text = translated
                        for t_elem in r_elements[1:]:
                            t_elem.text = ""

            # Tìm drawingML text (a:t)
            for t_elem in body.iter(f'{{{nsmap["a"]}}}t'):
                if t_elem.text and t_elem.text.strip():
                    t_elem.text = translate_fn(t_elem.text)

        except Exception as e:
            logger.debug("Không thể dịch shapes trong docx: %s", sanitize_error(e))

    def _write_doc(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch file .doc — chuyển sang .docx trước bằng LibreOffice.

        Output luôn là .docx vì python-docx không ghi được .doc.
        """
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.run(
                    [
                        "libreoffice", "--headless", "--convert-to", "docx",
                        str(source_path), "--outdir", tmp_dir,
                    ],
                    capture_output=True, timeout=60, check=True,
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "Cần cài LibreOffice để xử lý file .doc. "
                    "Vui lòng cài đặt hoặc chuyển file sang .docx."
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(
                    f"Chuyển đổi file .doc quá lâu (>60s): {source_path.name}"
                )

            docx_path = Path(tmp_dir) / source_path.with_suffix(".docx").name
            if not docx_path.exists():
                raise RuntimeError(
                    f"Không thể chuyển đổi file .doc: {source_path.name}"
                )

            actual_output = output_path.with_suffix(".docx")
            self._write_docx(docx_path, actual_output, translate_fn)
