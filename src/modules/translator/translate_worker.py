"""TranslateWorker — Worker thread cho việc dịch file."""

import logging
import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThread, Signal

from src.core.logging_config import safe_file_label, sanitize_error
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
        context: str | None = None,
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
            context: Ngữ cảnh từ kết quả tổng hợp (tuỳ chọn, chỉ cho smart mode).
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
        self._context = context
        self._cancelled = False

    def run(self) -> None:
        """Thực thi toàn bộ pipeline dịch trên worker thread."""
        if self._mode == "smart":
            self._run_smart()
        else:
            self._run_default()

    def _run_default(self) -> None:
        """Pipeline dịch offline bằng Argos.

        Pipeline: infer ngôn ngữ nguồn → tải model → dịch từng file → ghi output.
        ArgosEngine được tạo tại đây (trên worker thread) để tránh lỗi
        SQLite cross-thread — Argos cache SQLite connection nội bộ.
        """
        # Tạo ArgosEngine trên worker thread để tránh lỗi SQLite cross-thread
        self._argos = ArgosEngine()

        # Bước 1: Infer ngôn ngữ nguồn từ ngôn ngữ đích
        source_lang = self._infer_source_lang(self._target_lang)
        logger.info("Ngôn ngữ nguồn (inferred): %s → %s", source_lang, self._target_lang)

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

        Pipeline: tra glossary → tạo AI engine
        → dịch từng file theo 2 pha (collect → batch translate → write).
        """
        from src.modules.translator.ai_engine import AIEngine

        if not self._provider:
            self.error_occurred.emit("Không có AI Provider. Vui lòng cấu hình API key trong Cài đặt.")
            return

        if self._cancelled:
            return

        # Bước 1: Tra glossary hai chiều (infer source lang để tra bảng thuật ngữ)
        source_lang_for_glossary = self._infer_source_lang(self._target_lang)
        glossary: dict[str, str] | None = None
        if self._glossary:
            glossary = self._glossary.lookup(source_lang_for_glossary, self._target_lang)
            if glossary:
                logger.info("Áp dụng %d thuật ngữ từ bảng thuật ngữ.", len(glossary))

        if self._cancelled:
            return

        # Bước 2: Tạo AI Engine (source_lang=None → AI tự nhận diện ngôn ngữ)
        self.status_updated.emit("Đang kết nối AI Provider...")
        context = self._context
        if context:
            logger.info("Dùng summary context (%d ký tự) làm ngữ cảnh dịch.", len(context))
        ai_engine = AIEngine(
            provider=self._provider,
            target_lang=self._target_lang,
            source_lang=None,
            domain=self._domain,
            style=self._style,
            context=context,
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
                self.status_updated.emit(f"Đang dịch...")
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
                logger.info(
                    "Dịch thành công: input=(%s), output=(%s)",
                    safe_file_label(file_path),
                    safe_file_label(actual_output),
                )

            except Exception as e:
                error_msg = self._format_error(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error(
                    "Dịch thất bại: %s - %s",
                    safe_file_label(file_path),
                    sanitize_error(e),
                )

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
                logger.info(
                    "Dịch thành công: input=(%s), output=(%s)",
                    safe_file_label(file_path),
                    safe_file_label(actual_output),
                )

            except Exception as e:
                error_msg = self._format_error(e)
                self.file_failed.emit(file_path, error_msg)
                fail_count += 1
                logger.error(
                    "Dịch thất bại: %s - %s",
                    safe_file_label(file_path),
                    sanitize_error(e),
                )

            percent = int((idx + 1) / total * 100)
            self.progress_updated.emit(percent)

        self.all_completed.emit(success_count, fail_count, output_files)

    @staticmethod
    def _format_error(e: Exception) -> str:
        """Tạo thông báo lỗi thân thiện cho người dùng.

        Args:
            e: Exception gốc.

        Returns:
            Chuỗi thông báo dễ hiểu.
        """
        s = str(e).lower()
        if isinstance(e, MemoryError) or "memory" in s:
            return "File quá lớn, không đủ bộ nhớ để xử lý."
        if isinstance(e, UnicodeDecodeError):
            return "Không thể đọc file — encoding không được hỗ trợ."
        if "timeout" in s or "timed out" in s:
            return "API timeout sau nhiều lần thử. Vui lòng thử lại sau."
        if "rate limit" in s or "429" in s or "too many requests" in s:
            return "Vượt giới hạn API. Vui lòng chờ vài phút rồi thử lại."
        if "quota" in s or "billing" in s:
            return "Hết quota API. Vui lòng kiểm tra tài khoản của bạn."
        if "invalid" in s or "corrupt" in s or "malformed" in s:
            return f"File bị hỏng hoặc định dạng không hợp lệ: {e}"
        return str(e)

    def cancel(self) -> None:
        """Yêu cầu hủy dịch. Worker sẽ dừng sau file đang xử lý."""
        self._cancelled = True
        logger.info("Đã yêu cầu hủy dịch.")

    @property
    def is_cancelled(self) -> bool:
        """Kiểm tra worker đã bị hủy chưa."""
        return self._cancelled

    @staticmethod
    def _infer_source_lang(target_lang: str) -> str:
        """Infer ngôn ngữ nguồn từ ngôn ngữ đích.

        Argos chỉ hỗ trợ en↔vi, en↔ja, vi↔ja (pivot qua en).
        Mặc định giả sử tài liệu gốc là tiếng Anh nếu đích là vi/ja,
        hoặc tiếng Việt nếu đích là en.

        Args:
            target_lang: Mã ngôn ngữ đích.

        Returns:
            Mã ngôn ngữ nguồn.
        """
        defaults = {"vi": "en", "en": "vi", "ja": "en"}
        return defaults.get(target_lang, "en")

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
