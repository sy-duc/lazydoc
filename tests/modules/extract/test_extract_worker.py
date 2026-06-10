"""Test cho ExtractWorker — worker thread trích xuất file."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from src.core.error_messages import FILE_ACCESS_ERROR_MESSAGE
from src.modules.extract.extract_worker import ExtractWorker
from src.processors.base import ExtractedContent


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Tạo QCoreApplication cho test (cần cho QThread)."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def sample_txt_file(tmp_path: Path) -> Path:
    """Tạo file .txt mẫu để test."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("Nội dung test", encoding="utf-8")
    return file_path


@pytest.fixture
def mock_extracted_content(sample_txt_file: Path) -> ExtractedContent:
    """Tạo ExtractedContent mẫu."""
    return ExtractedContent(
        file_path=sample_txt_file,
        file_name="test.txt",
        file_size=100,
        text_content={"content": "Nội dung test"},
        metadata={"encoding": "utf-8"},
    )


class TestExtractWorker:
    """Test suite cho ExtractWorker."""

    def test_worker_extract_success(
        self, qapp: QCoreApplication, sample_txt_file: Path, mock_extracted_content: ExtractedContent
    ) -> None:
        """Test worker extract file thành công."""
        completed_files: list[Path] = []
        completed_contents: list[ExtractedContent] = []
        final_results: list[tuple[int, int]] = []

        worker = ExtractWorker([sample_txt_file])

        worker.file_completed.connect(
            lambda p, c: (completed_files.append(p), completed_contents.append(c))
        )
        worker.all_completed.connect(lambda s, f: final_results.append((s, f)))

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor"
        ) as mock_factory:
            mock_processor = MagicMock()
            mock_processor.extract.return_value = mock_extracted_content
            mock_factory.return_value = mock_processor

            worker.run()

        assert len(completed_files) == 1
        assert completed_files[0] == sample_txt_file
        assert final_results == [(1, 0)]

    def test_worker_extract_failure(
        self, qapp: QCoreApplication, sample_txt_file: Path
    ) -> None:
        """Test worker xử lý lỗi khi extract thất bại."""
        failed_files: list[Path] = []
        error_msgs: list[str] = []
        final_results: list[tuple[int, int]] = []

        worker = ExtractWorker([sample_txt_file])

        worker.file_failed.connect(
            lambda p, e: (failed_files.append(p), error_msgs.append(e))
        )
        worker.all_completed.connect(lambda s, f: final_results.append((s, f)))

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor"
        ) as mock_factory:
            mock_factory.side_effect = ValueError("File lỗi")
            worker.run()

        assert len(failed_files) == 1
        assert "File lỗi" in error_msgs[0]
        assert final_results == [(0, 1)]

    def test_worker_formats_permission_error(
        self, qapp: QCoreApplication, sample_txt_file: Path
    ) -> None:
        """File bị khóa được báo bằng nội dung thân thiện."""
        error_msgs: list[str] = []
        worker = ExtractWorker([sample_txt_file])
        worker.file_failed.connect(lambda _path, error: error_msgs.append(error))

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor"
        ) as mock_factory:
            mock_processor = MagicMock()
            mock_processor.extract.side_effect = PermissionError("Permission denied")
            mock_factory.return_value = mock_processor
            worker.run()

        assert error_msgs == [FILE_ACCESS_ERROR_MESSAGE]

    def test_worker_cancel(
        self, qapp: QCoreApplication, tmp_path: Path
    ) -> None:
        """Test worker dừng khi bị cancel."""
        files = []
        for i in range(5):
            f = tmp_path / f"test_{i}.txt"
            f.write_text(f"Nội dung {i}")
            files.append(f)

        started_files: list[Path] = []
        worker = ExtractWorker(files)
        worker.file_started.connect(started_files.append)

        # Cancel ngay khi bắt đầu
        worker.cancel()

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor"
        ):
            worker.run()

        # Không file nào được bắt đầu vì đã cancel trước
        assert len(started_files) == 0

    def test_worker_cancel_property(self, qapp: QCoreApplication) -> None:
        """Test thuộc tính is_cancelled."""
        worker = ExtractWorker([])
        assert worker.is_cancelled is False
        worker.cancel()
        assert worker.is_cancelled is True

    def test_worker_multiple_files(
        self, qapp: QCoreApplication, tmp_path: Path
    ) -> None:
        """Test worker xử lý nhiều file (mix thành công/thất bại)."""
        file_ok = tmp_path / "ok.txt"
        file_ok.write_text("OK")
        file_fail = tmp_path / "fail.txt"
        file_fail.write_text("FAIL")

        completed_files: list[Path] = []
        failed_files: list[Path] = []
        final_results: list[tuple[int, int]] = []

        worker = ExtractWorker([file_ok, file_fail])
        worker.file_completed.connect(lambda p, c: completed_files.append(p))
        worker.file_failed.connect(lambda p, e: failed_files.append(p))
        worker.all_completed.connect(lambda s, f: final_results.append((s, f)))

        content_ok = ExtractedContent(
            file_path=file_ok, file_name="ok.txt", file_size=2,
            text_content={"content": "OK"},
        )

        def side_effect(path: Path) -> MagicMock:
            mock = MagicMock()
            if path == file_ok:
                mock.extract.return_value = content_ok
            else:
                mock.extract.side_effect = RuntimeError("Lỗi đọc file")
            return mock

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor",
            side_effect=side_effect,
        ):
            worker.run()

        assert len(completed_files) == 1
        assert len(failed_files) == 1
        assert final_results == [(1, 1)]

    def test_worker_emits_file_started(
        self, qapp: QCoreApplication, sample_txt_file: Path, mock_extracted_content: ExtractedContent
    ) -> None:
        """Test worker phát signal file_started."""
        started_files: list[Path] = []
        worker = ExtractWorker([sample_txt_file])
        worker.file_started.connect(started_files.append)

        with patch(
            "src.modules.extract.extract_worker.ProcessorFactory.get_processor"
        ) as mock_factory:
            mock_processor = MagicMock()
            mock_processor.extract.return_value = mock_extracted_content
            mock_factory.return_value = mock_processor
            worker.run()

        assert started_files == [sample_txt_file]
