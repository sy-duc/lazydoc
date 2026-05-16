"""Test Writers — Kiểm thử các bộ ghi file dịch."""

import csv
import tempfile
from pathlib import Path

import pytest

from src.writers.factory import WriterFactory


def _mock_translate(text: str) -> str:
    """Hàm dịch giả — thêm prefix [T] để nhận biết text đã dịch."""
    if not text or not text.strip():
        return text
    return f"[T] {text}"


class TestWriterFactory:
    """Test WriterFactory."""

    def test_supported_extensions(self) -> None:
        """Kiểm tra danh sách extension được hỗ trợ."""
        exts = WriterFactory.get_supported_extensions()
        assert ".txt" in exts
        assert ".md" in exts
        assert ".csv" in exts
        assert ".xlsx" in exts
        assert ".docx" in exts
        assert ".pptx" in exts
        assert ".pdf" not in exts

    def test_is_supported(self) -> None:
        assert WriterFactory.is_supported(Path("test.txt"))
        assert WriterFactory.is_supported(Path("test.xlsx"))
        assert not WriterFactory.is_supported(Path("test.mp3"))

    def test_get_writer_unsupported(self) -> None:
        with pytest.raises(ValueError, match="Không hỗ trợ"):
            WriterFactory.get_writer(Path("test.mp3"))


class TestTxtWriter:
    """Test TxtWriter."""

    def test_write_translated_txt(self) -> None:
        """Dịch file txt giữ nguyên cấu trúc đoạn."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.txt"
            output = Path(tmp) / "output.txt"
            source.write_text("Hello World\n\nThis is a test.", encoding="utf-8")

            writer = WriterFactory.get_writer(source)
            writer.write_translated(source, output, _mock_translate)

            result = output.read_text(encoding="utf-8")
            assert "[T] Hello World" in result
            assert "[T] This is a test." in result


class TestCsvWriter:
    """Test CsvWriter."""

    def test_write_translated_csv(self) -> None:
        """Dịch file csv giữ nguyên cấu trúc bảng."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.csv"
            output = Path(tmp) / "output.csv"

            with open(source, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Name", "Description"])
                w.writerow(["Alice", "A developer"])

            writer = WriterFactory.get_writer(source)
            writer.write_translated(source, output, _mock_translate)

            with open(output, encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            assert rows[0][0] == "[T] Name"
            assert rows[1][1] == "[T] A developer"


class TestExcelWriter:
    """Test ExcelWriter."""

    def test_write_translated_xlsx(self) -> None:
        """Dịch file xlsx giữ nguyên formatting."""
        openpyxl = pytest.importorskip("openpyxl")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.xlsx"
            output = Path(tmp) / "output.xlsx"

            # Tạo file xlsx test
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Báo cáo"
            ws["A1"] = "Tiêu đề"
            ws["B1"] = "Nội dung"
            ws["A2"] = 12345  # Số — không dịch
            ws["B2"] = "Đây là test"
            wb.save(source)
            wb.close()

            writer = WriterFactory.get_writer(source)
            writer.write_translated(source, output, _mock_translate)

            # Kiểm tra output
            wb_out = openpyxl.load_workbook(output)
            ws_out = wb_out.active
            assert "[T]" in ws_out["A1"].value
            assert "[T]" in ws_out["B2"].value
            assert ws_out["A2"].value == 12345  # Số giữ nguyên
            # Tên sheet đã dịch (ký tự [ ] bị loại bỏ vì Excel không hỗ trợ)
            assert "Báo cáo" in wb_out.sheetnames[0]
            assert wb_out.sheetnames[0] != "Báo cáo"  # Đã dịch, khác gốc
            wb_out.close()


class TestWordWriter:
    """Test WordWriter."""

    def test_write_translated_docx(self) -> None:
        """Dịch file docx giữ nguyên formatting."""
        docx = pytest.importorskip("docx")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.docx"
            output = Path(tmp) / "output.docx"

            # Tạo file docx test
            doc = docx.Document()
            doc.add_paragraph("Hello World")
            doc.add_paragraph("Second paragraph")
            doc.save(source)

            writer = WriterFactory.get_writer(source)
            writer.write_translated(source, output, _mock_translate)

            # Kiểm tra output
            doc_out = docx.Document(output)
            texts = [p.text for p in doc_out.paragraphs if p.text.strip()]
            assert any("[T]" in t for t in texts)


class TestPowerPointWriter:
    """Test PowerPointWriter."""

    def test_write_translated_pptx(self) -> None:
        """Dịch file pptx giữ nguyên formatting."""
        pptx = pytest.importorskip("pptx")

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test.pptx"
            output = Path(tmp) / "output.pptx"

            # Tạo file pptx test
            prs = pptx.Presentation()
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            slide.shapes.title.text = "Tiêu đề slide"
            slide.placeholders[1].text = "Nội dung slide"
            prs.save(source)

            writer = WriterFactory.get_writer(source)
            writer.write_translated(source, output, _mock_translate)

            # Kiểm tra output
            prs_out = pptx.Presentation(output)
            slide_out = prs_out.slides[0]
            title_text = slide_out.shapes.title.text
            assert "[T]" in title_text
