"""PdfProcessor — Trích xuất nội dung từ file PDF (.pdf)."""

import logging
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor

logger = logging.getLogger(__name__)


class PdfProcessor(FileProcessor):
    """Processor cho file PDF (.pdf).

    Hỗ trợ text-based PDF. OCR cho PDF scan (cần pytesseract).
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def extract(self, file_path: Path) -> ExtractedContent:
        """Trích xuất nội dung từ file PDF.

        Args:
            file_path: Đường dẫn file PDF.

        Returns:
            ExtractedContent với text và bảng biểu từ PDF.
        """
        self.validate_file(file_path)

        import pdfplumber

        text_content: dict[str, str] = {}
        tables: dict[str, list[list[list[str]]]] = {}
        images: dict[str, bytes] = {}
        total_pages = 0

        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)

            for page_idx, page in enumerate(pdf.pages, 1):
                page_key = f"Trang {page_idx}"
                page_parts: list[str] = []

                # Extract text
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    page_parts.append(page_text)

                # Extract tables
                page_tables = page.extract_tables()
                page_table_data: list[list[list[str]]] = []
                for tbl_idx, table in enumerate(page_tables):
                    clean_table: list[list[str]] = []
                    for row in table:
                        clean_row = [str(cell) if cell is not None else "" for cell in row]
                        clean_table.append(clean_row)
                    page_table_data.append(clean_table)
                # Không thêm bảng vào page_parts để tránh gửi trùng lặp lên AI

                if page_parts:
                    text_content[page_key] = "\n".join(page_parts)
                if page_table_data:
                    tables[f"{page_key}_tables"] = page_table_data

                # Extract images (lấy metadata, dữ liệu ảnh để gửi AI vision)
                if page.images:
                    for img_idx, img in enumerate(page.images):
                        try:
                            img_page = page.crop((img["x0"], img["top"], img["x1"], img["bottom"]))
                            pil_image = img_page.to_image(resolution=150).original
                            import io
                            buf = io.BytesIO()
                            pil_image.save(buf, format="PNG")
                            images[f"page{page_idx}_img{img_idx + 1}.png"] = buf.getvalue()
                        except Exception as e:
                            logger.warning("Không thể extract ảnh trang %d: %s", page_idx, e)

        # Nếu không extract được text → có thể là PDF scan
        if not text_content:
            logger.warning("PDF không có text: %s — có thể là PDF scan (cần OCR).", file_path.name)
            text_content["main"] = "[PDF scan — cần OCR để trích xuất nội dung]"

        content = ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content=text_content,
            tables=tables,
            images=images,
            metadata={
                "pages": total_pages,
                "tables": sum(len(t) for t in tables.values()),
                "images": len(images),
            },
        )

        logger.info(
            "Đã extract file pdf: %s (%d trang, %d bảng, %d ảnh)",
            file_path.name, total_pages,
            content.metadata["tables"], content.metadata["images"],
        )
        return content
