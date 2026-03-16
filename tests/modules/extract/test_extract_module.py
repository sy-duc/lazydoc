"""Test cho ExtractModule — điều phối extract, cache, worker."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from src.modules.extract.extract_module import ExtractModule
from src.processors.base import ExtractedContent


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Tạo QCoreApplication cho test."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def extract_module() -> ExtractModule:
    """Tạo ExtractModule instance."""
    return ExtractModule()


@pytest.fixture
def sample_content(tmp_path: Path) -> ExtractedContent:
    """Tạo ExtractedContent mẫu."""
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Test")
    return ExtractedContent(
        file_path=file_path,
        file_name="sample.txt",
        file_size=4,
        text_content={"content": "Test"},
    )


class TestExtractModuleCache:
    """Test quản lý cache của ExtractModule."""

    def test_cache_initially_empty(self, extract_module: ExtractModule) -> None:
        """Test cache rỗng khi khởi tạo."""
        assert extract_module.get_all_cached() == {}

    def test_get_cached_returns_none_for_uncached(
        self, extract_module: ExtractModule, tmp_path: Path
    ) -> None:
        """Test get_cached trả None khi file chưa cache."""
        assert extract_module.get_cached(tmp_path / "nonexist.txt") is None

    def test_invalidate_cached_file(
        self, extract_module: ExtractModule, sample_content: ExtractedContent
    ) -> None:
        """Test xóa cache của một file cụ thể."""
        # Trực tiếp đặt cache thông qua _cache (internal)
        extract_module._cache[sample_content.file_path] = sample_content
        assert extract_module.get_cached(sample_content.file_path) is not None

        extract_module.invalidate(sample_content.file_path)
        assert extract_module.get_cached(sample_content.file_path) is None

    def test_invalidate_nonexist_file(
        self, extract_module: ExtractModule, tmp_path: Path
    ) -> None:
        """Test invalidate file không có trong cache không gây lỗi."""
        extract_module.invalidate(tmp_path / "nofile.txt")

    def test_clear_cache(
        self, extract_module: ExtractModule, sample_content: ExtractedContent
    ) -> None:
        """Test xóa toàn bộ cache."""
        extract_module._cache[sample_content.file_path] = sample_content
        extract_module.clear_cache()
        assert extract_module.get_all_cached() == {}

    def test_get_all_cached_returns_copy(
        self, extract_module: ExtractModule, sample_content: ExtractedContent
    ) -> None:
        """Test get_all_cached trả bản copy, không phải reference."""
        extract_module._cache[sample_content.file_path] = sample_content
        cached = extract_module.get_all_cached()
        cached.clear()
        # Cache gốc không bị ảnh hưởng
        assert len(extract_module.get_all_cached()) == 1


class TestExtractModuleState:
    """Test trạng thái của ExtractModule."""

    def test_not_running_initially(self, extract_module: ExtractModule) -> None:
        """Test module không chạy khi khởi tạo."""
        assert extract_module.is_running is False

    def test_cancel_when_not_running(self, extract_module: ExtractModule) -> None:
        """Test cancel khi không có worker chạy không gây lỗi."""
        extract_module.cancel()


class TestExtractModuleCacheHit:
    """Test ExtractModule trả kết quả từ cache mà không tạo worker."""

    def test_all_cached_no_worker_created(
        self, extract_module: ExtractModule, sample_content: ExtractedContent
    ) -> None:
        """Test khi tất cả file đã cache thì không tạo worker."""
        file_path = sample_content.file_path
        extract_module._cache[file_path] = sample_content

        completed_signals: list[tuple[int, int]] = []
        file_completed_signals: list[Path] = []

        extract_module.extract_completed.connect(
            lambda s, f: completed_signals.append((s, f))
        )
        extract_module.file_completed.connect(
            lambda p, c: file_completed_signals.append(p)
        )

        extract_module.start_extract([file_path])

        # File cached được emit ngay lập tức
        assert file_path in file_completed_signals
        # Extract hoàn tất ngay với 1 thành công, 0 thất bại
        assert completed_signals == [(1, 0)]
        # Không có worker
        assert extract_module._worker is None
