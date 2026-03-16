"""Test cho FileProcessor interface và ExtractedContent."""

import pytest
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor


class DummyProcessor(FileProcessor):
    """Processor giả để test abstract interface."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".dummy", ".test"]

    def extract(self, file_path: Path) -> ExtractedContent:
        self.validate_file(file_path)
        return ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content={"main": "nội dung test"},
        )


class TestExtractedContent:
    """Test dataclass ExtractedContent."""

    def test_default_values(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
        )
        assert content.text_content == {}
        assert content.tables == {}
        assert content.shapes_text == {}
        assert content.images == {}
        assert content.metadata == {}

    def test_has_content_empty(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
        )
        assert content.has_content is False

    def test_has_content_with_text(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
            text_content={"main": "nội dung"},
        )
        assert content.has_content is True

    def test_has_content_with_tables(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
            tables={"Sheet1": [[["a", "b"], ["c", "d"]]]},
        )
        assert content.has_content is True

    def test_get_full_text(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
            text_content={
                "Sheet1": "dữ liệu sheet 1",
                "Sheet2": "dữ liệu sheet 2",
            },
        )
        full_text = content.get_full_text()
        assert "[Sheet1]" in full_text
        assert "dữ liệu sheet 1" in full_text
        assert "[Sheet2]" in full_text
        assert "dữ liệu sheet 2" in full_text

    def test_get_full_text_skips_empty(self) -> None:
        content = ExtractedContent(
            file_path=Path("test.txt"),
            file_name="test.txt",
            file_size=100,
            text_content={"main": "có nội dung", "empty": "  "},
        )
        full_text = content.get_full_text()
        assert "[main]" in full_text
        assert "[empty]" not in full_text


class TestFileProcessor:
    """Test abstract FileProcessor interface."""

    def test_can_process_supported(self) -> None:
        processor = DummyProcessor()
        assert processor.can_process(Path("file.dummy")) is True
        assert processor.can_process(Path("file.test")) is True

    def test_can_process_unsupported(self) -> None:
        processor = DummyProcessor()
        assert processor.can_process(Path("file.xyz")) is False

    def test_can_process_case_insensitive(self) -> None:
        processor = DummyProcessor()
        assert processor.can_process(Path("file.DUMMY")) is True
        assert processor.can_process(Path("file.Test")) is True

    def test_validate_file_not_found(self) -> None:
        processor = DummyProcessor()
        with pytest.raises(FileNotFoundError, match="không tồn tại"):
            processor.validate_file(Path("/nonexistent/file.dummy"))

    def test_validate_file_wrong_extension(self, tmp_path: Path) -> None:
        test_file = tmp_path / "file.wrong"
        test_file.write_text("test")
        processor = DummyProcessor()
        with pytest.raises(ValueError, match="không được hỗ trợ"):
            processor.validate_file(test_file)

    def test_validate_file_is_directory(self, tmp_path: Path) -> None:
        processor = DummyProcessor()
        # tmp_path là directory, suffix rỗng nên sẽ raise ValueError
        with pytest.raises(ValueError):
            processor.validate_file(tmp_path)

    def test_extract_valid_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "file.dummy"
        test_file.write_text("nội dung test")
        processor = DummyProcessor()
        result = processor.extract(test_file)
        assert result.file_name == "file.dummy"
        assert result.text_content["main"] == "nội dung test"
