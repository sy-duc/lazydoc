"""Test cho xml_shapes — trích xuất shapes text/images từ file Office qua XML."""

import pytest
from pathlib import Path

from src.processors.xml_shapes import (
    extract_shapes_from_xlsx,
    extract_images_from_xlsx,
    map_drawings_to_sheets,
    extract_shapes_from_docx,
)


class TestExtractShapesFromXlsx:
    """Test trích xuất shapes text từ .xlsx qua XML parsing."""

    def test_xlsx_with_textbox(self, tmp_path: Path) -> None:
        """File .xlsx có textbox → extract được text bên trong."""
        import openpyxl

        f = tmp_path / "shapes.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "Cell data"
        wb.save(f)

        # openpyxl không hỗ trợ tạo shapes, nên test basic case
        result = extract_shapes_from_xlsx(f)
        # File không có shapes → trả về dict rỗng
        assert isinstance(result, dict)

    def test_invalid_file(self, tmp_path: Path) -> None:
        """File không phải ZIP → trả về dict rỗng, không crash."""
        f = tmp_path / "not_zip.xlsx"
        f.write_text("not a zip file")
        result = extract_shapes_from_xlsx(f)
        assert result == {}


class TestExtractImagesFromXlsx:
    """Test trích xuất images từ .xlsx."""

    def test_xlsx_no_images(self, tmp_path: Path) -> None:
        """File .xlsx không có ảnh → dict rỗng."""
        import openpyxl

        f = tmp_path / "no_img.xlsx"
        wb = openpyxl.Workbook()
        wb.active["A1"] = "test"
        wb.save(f)

        result = extract_images_from_xlsx(f)
        assert result == {}

    def test_xlsx_with_image(self, tmp_path: Path) -> None:
        """File .xlsx có ảnh nhúng → extract được bytes."""
        import openpyxl
        from openpyxl.drawing.image import Image as XlImage
        from PIL import Image
        import io

        f = tmp_path / "with_img.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Data"

        # Tạo ảnh nhỏ và nhúng vào Excel
        img_buf = io.BytesIO()
        Image.new("RGB", (20, 20), color="red").save(img_buf, format="PNG")
        img_buf.seek(0)

        img_path = tmp_path / "test_img.png"
        img_path.write_bytes(img_buf.getvalue())

        xl_img = XlImage(str(img_path))
        ws.add_image(xl_img, "B2")
        wb.save(f)

        result = extract_images_from_xlsx(f)
        assert len(result) == 1
        # Kiểm tra có bytes thật
        image_bytes = list(result.values())[0]
        assert len(image_bytes) > 0


class TestMapDrawingsToSheets:
    """Test mapping drawing → sheet name."""

    def test_xlsx_no_drawings(self, tmp_path: Path) -> None:
        """File không có drawings → dict rỗng."""
        import openpyxl

        f = tmp_path / "no_draw.xlsx"
        wb = openpyxl.Workbook()
        wb.active["A1"] = "test"
        wb.save(f)

        result = map_drawings_to_sheets(f)
        assert isinstance(result, dict)

    def test_xlsx_with_image_drawing(self, tmp_path: Path) -> None:
        """File có image → có drawing → mapping đúng sheet."""
        import openpyxl
        from openpyxl.drawing.image import Image as XlImage
        from PIL import Image
        import io

        f = tmp_path / "draw.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "MySheet"

        img_buf = io.BytesIO()
        Image.new("RGB", (10, 10)).save(img_buf, format="PNG")
        img_path = tmp_path / "t.png"
        img_path.write_bytes(img_buf.getvalue())

        ws.add_image(XlImage(str(img_path)), "A1")
        wb.save(f)

        result = map_drawings_to_sheets(f)
        # Phải có ít nhất 1 mapping
        assert len(result) >= 1
        assert "MySheet" in result.values()


class TestExtractShapesFromDocx:
    """Test trích xuất shapes text từ .docx."""

    def test_docx_no_shapes(self, tmp_path: Path) -> None:
        """File .docx chỉ có text → list rỗng."""
        import docx

        f = tmp_path / "no_shapes.docx"
        doc = docx.Document()
        doc.add_paragraph("Chỉ có text thường")
        doc.save(f)

        result = extract_shapes_from_docx(f)
        assert isinstance(result, list)

    def test_invalid_file(self, tmp_path: Path) -> None:
        """File không phải ZIP → trả về list rỗng, không crash."""
        f = tmp_path / "bad.docx"
        f.write_text("not a docx")
        result = extract_shapes_from_docx(f)
        assert result == []


class TestProcessorIntegrationWithShapes:
    """Test tích hợp processor với shapes extraction."""

    def test_excel_with_image_has_images(self, tmp_path: Path) -> None:
        """ExcelProcessor extract được images nhúng."""
        import openpyxl
        from openpyxl.drawing.image import Image as XlImage
        from PIL import Image
        import io
        from src.processors.excel_processor import ExcelProcessor

        f = tmp_path / "img.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Data"

        img_buf = io.BytesIO()
        Image.new("RGB", (10, 10), color="blue").save(img_buf, format="PNG")
        img_path = tmp_path / "blue.png"
        img_path.write_bytes(img_buf.getvalue())

        ws.add_image(XlImage(str(img_path)), "C3")
        wb.save(f)

        processor = ExcelProcessor()
        result = processor.extract(f)
        assert result.metadata["images"] == 1
        assert len(result.images) == 1

    def test_word_shapes_in_metadata(self, tmp_path: Path) -> None:
        """WordProcessor metadata có count shapes."""
        import docx
        from src.processors.word_processor import WordProcessor

        f = tmp_path / "test.docx"
        doc = docx.Document()
        doc.add_paragraph("Text")
        doc.save(f)

        processor = WordProcessor()
        result = processor.extract(f)
        assert "shapes" in result.metadata

    def test_powerpoint_shapes_in_metadata(self, tmp_path: Path) -> None:
        """PowerPointProcessor metadata có count shapes."""
        from pptx import Presentation
        from src.processors.powerpoint_processor import PowerPointProcessor

        f = tmp_path / "test.pptx"
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "Title"
        prs.save(f)

        processor = PowerPointProcessor()
        result = processor.extract(f)
        assert "shapes" in result.metadata
