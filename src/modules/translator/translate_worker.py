"""TranslateWorker — Worker thread cho việc dịch file."""

import logging
import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal

from src.modules.translator.argos_engine import ArgosEngine

logger = logging.getLogger(__name__)


class TranslateWorker(QThread):
    """Worker chạy trên thread riêng để dịch file không block UI.

    Toàn bộ công việc nặng (detect ngôn ngữ, tải model, dịch file)
    đều chạy trên thread này, không block UI.

    Signals:
        status_updated: Phát khi cập nhật trạng thái (str thông báo).
        file_started: Phát khi bắt đầu dịch một file (Path).
        file_completed: Phát khi dịch xong một file (Path, Path output).
        file_failed: Phát khi dịch thất bại (Path, str lỗi).
        progress_updated: Phát khi cập nhật tiến độ (int phần trăm).
        all_completed: Phát khi toàn bộ file đã xử lý xong
            (int thành công, int thất bại, list[Path] output).
        error_occurred: Phát khi có lỗi nghiêm trọng (str thông báo).
        cost_updated: Phát khi cập nhật chi phí (int input_tokens, int output_tokens).
    """

    status_updated = Signal(str)
    file_started = Signal(Path)
    file_completed = Signal(Path, Path)
    file_failed = Signal(Path, str)
    progress_updated = Signal(int)
    all_completed = Signal(int, int, list)
    error_occurred = Signal(str)
    cost_updated = Signal(int, int)

    def __init__(
        self,
        files: list[Path],
        output_dir: Path,
        target_lang: str,
        mode: str = "default",
        glossary_manager: object | None = None,
        provider: object | None = None,
        domain: str | None = None,
        style: str | None = None,
        parent: object = None,
    ) -> None:
        """Khởi tạo TranslateWorker.

        Args:
            files: Danh sách file cần dịch.
            output_dir: Thư mục đầu ra (Downloads).
            target_lang: Mã ngôn ngữ đích.
            mode: Chế độ dịch ("default" hoặc "smart").
            glossary_manager: GlossaryManager instance (tuỳ chọn).
            provider: BaseProvider instance cho chế độ smart (tuỳ chọn).
            domain: Lĩnh vực dịch thuật (tuỳ chọn, chỉ cho smart mode).
            style: Văn phong dịch thuật (tuỳ chọn, chỉ cho smart mode).
            parent: QObject cha.
        """
        super().__init__(parent)
        self._files = files
        self._output_dir = output_dir
        self._target_lang = target_lang
        self._mode = mode
        self._argos: ArgosEngine | None = None
        self._glossary = glossary_manager
        self._provider = provider
        self._domain = domain
        self._style = style
        self._cancelled = False

    def run(self) -> None:
        """Thực thi toàn bộ pipeline dịch trên worker thread."""
        if self._mode == "smart":
            self._run_smart()
        else:
            self._run_default()

    def _run_default(self) -> None:
        """Pipeline dịch offline bằng Argos.

        Pipeline: detect ngôn ngữ → tải model → dịch từng file → ghi output.
        ArgosEngine được tạo tại đây (trên worker thread) để tránh lỗi
        SQLite cross-thread — Argos cache SQLite connection nội bộ.
        """
        # Tạo ArgosEngine trên worker thread để tránh lỗi SQLite cross-thread
        self._argos = ArgosEngine()

        # Bước 1: Phát hiện ngôn ngữ nguồn
        self.status_updated.emit("Đang phát hiện ngôn ngữ...")
        source_lang = self._detect_source_lang(self._files[0], self._target_lang)
        logger.info("Phát hiện ngôn ngữ nguồn: %s", source_lang)

        if self._cancelled:
            return

        # Bước 2: Đảm bảo model Argos đã cài đặt
        self.status_updated.emit("Đang chuẩn bị model dịch...")
        try:
            self._argos.ensure_models(source_lang, self._target_lang)
        except RuntimeError as e:
            self.error_occurred.emit(str(e))
            return

        if self._cancelled:
            return

        # Bước 3: Tạo hàm dịch (không dùng glossary cho dịch offline)
        translate_fn = self._argos.create_translate_fn(
            source_lang, self._target_lang
        )

        # Bước 4: Dịch từng file
        self._translate_files(translate_fn)

    def _run_smart(self) -> None:
        """Pipeline dịch thông minh bằng AI Provider.

        Pipeline: detect ngôn ngữ → tra glossary → tạo AI engine
        → dịch từng file theo 2 pha (collect → batch translate → write).
        """
        from src.modules.translator.ai_engine import AIEngine

        if not self._provider:
            self.error_occurred.emit("Không có AI Provider. Vui lòng cấu hình API key trong Cài đặt.")
            return

        # Bước 1: Phát hiện ngôn ngữ nguồn (dùng Argos detect)
        self.status_updated.emit("Đang phát hiện ngôn ngữ...")
        self._argos = ArgosEngine()
        source_lang = self._detect_source_lang(self._files[0], self._target_lang)
        logger.info("Phát hiện ngôn ngữ nguồn: %s", source_lang)

        if self._cancelled:
            return

        # Bước 2: Tra glossary hai chiều
        glossary: dict[str, str] | None = None
        if self._glossary:
            glossary = self._glossary.lookup(source_lang, self._target_lang)
            if glossary:
                logger.info("Áp dụng %d thuật ngữ từ bảng thuật ngữ.", len(glossary))

        if self._cancelled:
            return

        # Bước 3: Tạo AI Engine
        self.status_updated.emit("Đang kết nối AI Provider...")
        ai_engine = AIEngine(
            provider=self._provider,
            target_lang=self._target_lang,
            source_lang=source_lang,
            domain=self._domain,
            style=self._style,
            glossary=glossary,
        )
        ai_engine.set_usage_callback(self._on_ai_usage)

        # Bước 4: Dịch từng file theo 2 pha
        self._translate_files_smart(ai_engine)

    def _on_ai_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Callback khi AI engine cập nhật token usage."""
        self.cost_updated.emit(input_tokens, output_tokens)

    def _translate_files_smart(self, ai_engine: "AIEngine") -> None:
        """Dịch từng file bằng AI với batch optimization (2 pha).

        Mỗi file:
        1. Pha collect: writer chạy với collector fn → thu thập text, output tạm bỏ.
        2. Pha batch: gom text thành batch, gửi AI (1 request/batch).
        3. Pha write: writer chạy lại với lookup fn → ghi file output thật.

        Args:
            ai_engine: AIEngine instance đã cấu hình.
        """
        import tempfile
        from src.writers.factory import WriterFactory

        success_count = 0
        fail_count = 0
        output_files: list[Path] = []
        total = len(self._files)
        translate_fn = ai_engine.create_translate_fn()

        for idx, file_path in enumerate(self._files):
            if self._cancelled:
                logger.info("Dịch bị hủy bởi người dùng.")
                break

            self.file_started.emit(file_path)

            try:
                writer = WriterFactory.get_writer(file_path)

                # Pha 1: Collect — writer chạy dry-run, thu thập text
                self.status_updated.emit(f"Đang phân tích: {file_path.name}")
                ai_engine.start_collecting()
                # Thu thập tên file để dịch cùng batch
                translate_fn(file_path.stem)
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_output = Path(tmp_dir) / f"collect{file_path.suffix}"
                    writer.write_translated(file_path, tmp_output, translate_fn)
                # tmp file tự xóa khi thoát context manager

                if self._cancelled:
                    break

                # Pha 2: Batch translate
                self.status_updated.emit(f"Đang dịch AI: {file_path.name}")
                ai_engine.flush_and_translate()

                if self._cancelled:
                    break

                # Pha 3: Write — writer chạy lại với lookup fn
                self.status_updated.emit(f"Đang ghi file: {file_path.name}")
                output_path = self._make_output_path(file_path, translate_fn)
                writer.write_translated(file_path, output_path, translate_fn)

                actual_output = self._find_actual_output(output_path)
                self.file_completed.emit(file_path, actual_output)
                output_files.append(actual_output)
                success_count += 1
                logger.info("Dịch thành công: %s → %s", file_path.name, actual_output.name)

            except Exception as e:
                error_msg = str(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error("Dịch thất bại: %s — %s", file_path.name, e)

            percent = int((idx + 1) / total * 100)
            self.progress_updated.emit(percent)

        self.all_completed.emit(success_count, fail_count, output_files)

    def _translate_files(self, translate_fn: Callable[[str], str]) -> None:
        """Dịch từng file và ghi output."""
        from src.writers.factory import WriterFactory

        success_count = 0
        fail_count = 0
        output_files: list[Path] = []
        total = len(self._files)

        for idx, file_path in enumerate(self._files):
            if self._cancelled:
                logger.info("Dịch bị hủy bởi người dùng.")
                break

            self.file_started.emit(file_path)
            self.status_updated.emit(f"Đang dịch: {file_path.name}")

            try:
                writer = WriterFactory.get_writer(file_path)
                output_path = self._make_output_path(file_path, translate_fn)
                writer.write_translated(file_path, output_path, translate_fn)

                actual_output = self._find_actual_output(output_path)
                self.file_completed.emit(file_path, actual_output)
                output_files.append(actual_output)
                success_count += 1
                logger.info("Dịch thành công: %s → %s", file_path.name, actual_output.name)

            except Exception as e:
                error_msg = str(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error("Dịch thất bại: %s — %s", file_path.name, e)

            percent = int((idx + 1) / total * 100)
            self.progress_updated.emit(percent)

        self.all_completed.emit(success_count, fail_count, output_files)

    def cancel(self) -> None:
        """Yêu cầu hủy dịch. Worker sẽ dừng sau file đang xử lý."""
        self._cancelled = True
        logger.info("Đã yêu cầu hủy dịch.")

    @property
    def is_cancelled(self) -> bool:
        """Kiểm tra worker đã bị hủy chưa."""
        return self._cancelled

    def _detect_source_lang(self, file_path: Path, target_lang: str) -> str:
        """Phát hiện ngôn ngữ nguồn từ nội dung file (chạy trên worker thread).

        Args:
            file_path: File mẫu.
            target_lang: Ngôn ngữ đích (loại trừ).

        Returns:
            Mã ngôn ngữ phát hiện được.
        """
        sample_text = ""

        try:
            ext = file_path.suffix.lower()

            if ext in (".txt", ".csv"):
                try:
                    sample_text = file_path.read_text(encoding="utf-8")[:2000]
                except UnicodeDecodeError:
                    sample_text = file_path.read_text(encoding="latin-1")[:2000]

            elif ext in (".xlsx", ".xls", ".docx", ".doc", ".pptx", ".ppt"):
                from src.processors.factory import ProcessorFactory
                processor = ProcessorFactory.get_processor(file_path)
                content = processor.extract(file_path)
                sample_text = content.get_full_text()[:2000]

            elif ext == ".pdf":
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    if pdf.pages:
                        sample_text = pdf.pages[0].extract_text() or ""

        except Exception as e:
            logger.warning("Không thể đọc mẫu để phát hiện ngôn ngữ: %s", e)

        detected = self._argos.detect_language(sample_text, exclude_lang=target_lang)
        logger.info("Phát hiện ngôn ngữ nguồn: %s (từ %s)", detected, file_path.name)
        return detected

    def _make_output_path(
        self, source_path: Path, translate_fn: Callable[[str], str]
    ) -> Path:
        """Tạo đường dẫn output — dịch tên file.

        Args:
            source_path: Đường dẫn file gốc.
            translate_fn: Hàm dịch.

        Returns:
            Đường dẫn file output trong thư mục Downloads.
        """
        stem = source_path.stem
        ext = source_path.suffix

        translated_name = translate_fn(stem)
        translated_name = self._sanitize_filename(translated_name)

        output_path = self._output_dir / f"{translated_name}{ext}"

        counter = 1
        while output_path.exists():
            output_path = self._output_dir / f"{translated_name} ({counter}){ext}"
            counter += 1

        return output_path

    def _find_actual_output(self, expected_path: Path) -> Path:
        """Tìm file output thực tế (extension có thể thay đổi)."""
        if expected_path.exists():
            return expected_path

        alternatives = [".xlsx", ".docx", ".pptx", ".txt"]
        for alt_ext in alternatives:
            alt_path = expected_path.with_suffix(alt_ext)
            if alt_path.exists():
                return alt_path

        return expected_path

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Loại bỏ ký tự không hợp lệ trong tên file."""
        sanitized = re.sub(r'[<>:"/\\|?*]', '', name)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "translated"
        return sanitized
