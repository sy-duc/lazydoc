"""PowerPointProcessor — Trích xuất nội dung từ file PowerPoint (.pptx, .ppt)."""

import logging
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor

logger = logging.getLogger(__name__)


class PowerPointProcessor(FileProcessor):
    """Processor cho file PowerPoint (.pptx, .ppt).

    Hỗ trợ slides, shapes (bao gồm group shapes), speaker notes, hình ảnh.
    File .ppt được xử lý nếu có LibreOffice (chuyển đổi → .pptx).
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".pptx", ".ppt"]

    def extract(self, file_path: Path) -> ExtractedContent:
        """Trích xuất nội dung từ file PowerPoint.

        Args:
            file_path: Đường dẫn file PowerPoint.

        Returns:
            ExtractedContent với text từng slide, shapes, notes.
        """
        self.validate_file(file_path)

        ext = file_path.suffix.lower()
        if ext == ".ppt":
            return self._extract_ppt(file_path)
        return self._extract_pptx(file_path)

    def _iter_shapes(self, shapes: "pptx.shapes.shapetree.SlideShapes") -> "Iterator":
        """Duyệt tất cả shapes bao gồm shapes bên trong group.

        Args:
            shapes: Collection shapes của slide.

        Yields:
            Từng shape đơn lẻ, bao gồm shapes lồng trong group.
        """
        for shape in shapes:
            yield shape
            # Nếu là group shape → đệ quy lấy shapes bên trong
            if shape.shape_type is not None and shape.shape_type == 6:  # MSO_SHAPE_TYPE.GROUP
                try:
                    for child_shape in self._iter_shapes(shape.shapes):
                        yield child_shape
                except Exception:
                    pass

    def _extract_pptx(self, file_path: Path) -> ExtractedContent:
        """Trích xuất từ file .pptx bằng python-pptx."""
        from pptx import Presentation

        prs = Presentation(file_path)

        text_content: dict[str, str] = {}
        shapes_text: dict[str, list[str]] = {}
        tables: dict[str, list[list[list[str]]]] = {}
        images: dict[str, bytes] = {}

        for slide_idx, slide in enumerate(prs.slides, 1):
            slide_key = f"Slide {slide_idx}"
            slide_texts: list[str] = []
            slide_shapes: list[str] = []
            slide_tables: list[list[list[str]]] = []

            for shape in self._iter_shapes(slide.shapes):
                # Text từ text frame
                if shape.has_text_frame:
                    text = shape.text_frame.text.strip()
                    if text:
                        # Placeholder (title, body, ...) và text box → text chính
                        if shape.is_placeholder or shape.shape_type == 1:
                            slide_texts.append(text)
                        else:
                            slide_shapes.append(text)

                # Bảng biểu
                if shape.has_table:
                    table_data: list[list[str]] = []
                    for row in shape.table.rows:
                        row_data = [cell.text for cell in row.cells]
                        table_data.append(row_data)
                    slide_tables.append(table_data)
                    slide_texts.append("[Bảng]")
                    for row in table_data:
                        slide_texts.append("\t".join(row))

                # Hình ảnh
                if hasattr(shape, "image"):
                    try:
                        image_data = shape.image.blob
                        ext = shape.image.content_type.split("/")[-1]
                        image_name = f"slide{slide_idx}_{shape.shape_id}.{ext}"
                        images[image_name] = image_data
                    except Exception as e:
                        logger.warning("Không thể đọc ảnh slide %d: %s", slide_idx, e)

            # Speaker notes
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes = slide.notes_slide.notes_text_frame.text.strip()
                if notes:
                    slide_texts.append(f"[Ghi chú] {notes}")

            if slide_texts:
                text_content[slide_key] = "\n".join(slide_texts)
            if slide_shapes:
                shapes_text[slide_key] = slide_shapes
            if slide_tables:
                tables[slide_key] = slide_tables

        total_shapes = sum(len(v) for v in shapes_text.values())

        content = ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content=text_content,
            tables=tables,
            shapes_text=shapes_text,
            images=images,
            metadata={
                "slides": len(prs.slides),
                "shapes": total_shapes,
                "images": len(images),
            },
        )

        logger.info(
            "Đã extract file pptx: %s (%d slide, %d shapes, %d ảnh)",
            file_path.name, len(prs.slides), total_shapes, len(images),
        )
        return content

    def _extract_ppt(self, file_path: Path) -> ExtractedContent:
        """Trích xuất từ file .ppt (chuyển đổi sang .pptx trước).

        Yêu cầu LibreOffice được cài đặt trên hệ thống.
        """
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pptx", str(file_path), "--outdir", tmp_dir],
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
            except FileNotFoundError:
                raise RuntimeError(
                    "Cần cài LibreOffice để xử lý file .ppt. "
                    "Vui lòng cài đặt hoặc chuyển file sang .pptx."
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"Chuyển đổi file .ppt quá lâu (>60s): {file_path.name}")

            pptx_path = Path(tmp_dir) / file_path.with_suffix(".pptx").name
            if not pptx_path.exists():
                raise RuntimeError(f"Không thể chuyển đổi file .ppt: {file_path.name}")

            result = self._extract_pptx(pptx_path)
            result.file_path = file_path
            result.file_name = file_path.name
            result.file_size = file_path.stat().st_size
            return result
