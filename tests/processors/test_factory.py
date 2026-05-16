"""Test cho ProcessorFactory."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.processors.factory import ProcessorFactory, SUPPORTED_EXTENSIONS


class TestProcessorFactory:
    """Test ProcessorFactory."""

    def setup_method(self) -> None:
        """Reset extension map trước mỗi test."""
        ProcessorFactory._extension_map = {}

    def test_is_supported_valid_extensions(self) -> None:
        for extensions in SUPPORTED_EXTENSIONS.values():
            for ext in extensions:
                assert ProcessorFactory.is_supported(f"file{ext}") is True

    def test_is_supported_invalid_extension(self) -> None:
        assert ProcessorFactory.is_supported("file.xyz") is False
        assert ProcessorFactory.is_supported("file.mp3") is False

    def test_is_supported_case_insensitive(self) -> None:
        assert ProcessorFactory.is_supported("file.TXT") is True
        assert ProcessorFactory.is_supported("file.Xlsx") is True
        assert ProcessorFactory.is_supported("file.PNG") is True

    def test_get_supported_extensions(self) -> None:
        extensions = ProcessorFactory.get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".txt" in extensions
        assert ".xlsx" in extensions
        assert ".docx" in extensions
        assert ".pptx" in extensions
        assert ".png" in extensions
        assert ".csv" in extensions
        assert ".pdf" not in extensions
        # Phải được sắp xếp
        assert extensions == sorted(extensions)

    def test_get_processor_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="không được hỗ trợ"):
            ProcessorFactory.get_processor("file.mp3")

    def test_get_processor_txt(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "txt_processor"
            result = ProcessorFactory.get_processor("file.txt")
            mock.assert_called_once_with("txt")
            assert result == "txt_processor"

    def test_get_processor_excel(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "excel_processor"
            result = ProcessorFactory.get_processor("report.xlsx")
            mock.assert_called_once_with("excel")

    def test_get_processor_word(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "word_processor"
            ProcessorFactory.get_processor("doc.docx")
            mock.assert_called_once_with("word")

    def test_get_processor_powerpoint(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "pptx_processor"
            ProcessorFactory.get_processor("slide.pptx")
            mock.assert_called_once_with("powerpoint")

    def test_get_processor_pdf_unsupported(self) -> None:
        with pytest.raises(ValueError, match="không được hỗ trợ"):
            ProcessorFactory.get_processor("document.pdf")

    def test_get_processor_image(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "image_processor"
            ProcessorFactory.get_processor("photo.png")
            mock.assert_called_once_with("image")

    def test_get_processor_csv(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "csv_processor"
            ProcessorFactory.get_processor("data.csv")
            mock.assert_called_once_with("csv")

    def test_get_processor_accepts_path_object(self) -> None:
        with patch("src.processors.factory.ProcessorFactory._create_processor") as mock:
            mock.return_value = "processor"
            ProcessorFactory.get_processor(Path("file.txt"))
            mock.assert_called_once_with("txt")

    def test_extension_map_built_once(self) -> None:
        """Extension map chỉ build 1 lần, các lần gọi sau tái sử dụng."""
        ProcessorFactory._build_extension_map()
        first_map = ProcessorFactory._extension_map.copy()
        ProcessorFactory._build_extension_map()
        assert ProcessorFactory._extension_map == first_map
