"""MainWindow — Màn hình chính của ứng dụng LazyDoc."""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.core.logging_config import safe_file_label, sanitize_error
from src.ui import theme
from src.ui.dialogs.message_dialog import MessageDialog
from src.modules.extract import ExtractModule
from src.modules.summarizer import SummaryModule, QAModule, _md_to_html
from src.modules.translator import TranslateModule
from src.processors.base import ExtractedContent
from src.processors.factory import ProcessorFactory
from src.providers.provider_manager import ProviderManager
from src.ui.dialogs.about_dialog import AboutDialog
from src.ui.dialogs.guide_dialog import GuideDialog
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.translate_dialog import TranslateDialog
from src.ui.widgets.file_table import FileTable
from src.ui.widgets.blender_area import BlenderArea
from src.ui.widgets.summary_area import SummaryArea
from src.ui.widgets.cost_tracker import CostTracker
from src.ui.widgets.toolbar import Toolbar
from src.ui.widgets.title_bar import TitleBar

logger = logging.getLogger(__name__)

# Lấy danh sách extension hỗ trợ từ ProcessorFactory
SUPPORTED_EXTENSIONS = set(ProcessorFactory.get_supported_extensions())


class MainWindow(QWidget):
    """Cửa sổ chính của ứng dụng LazyDoc."""

    # Signal khi có file được thêm vào
    files_added = Signal(list)

    def __init__(self, provider_manager: ProviderManager | None = None) -> None:
        """Khởi tạo MainWindow.

        Args:
            provider_manager: ProviderManager instance từ main.py.
        """
        super().__init__()
        self._i18n = I18nManager()
        self._provider_manager = provider_manager or ProviderManager()
        self._drag_start_pos = None
        self._grind_files: list[Path] = []
        self._grind_cancelled = False
        self._pending_summary = False
        self._extract_errors: dict[Path, str] = {}
        self._detail_report_path: str = ""
        self._summary_context: str = ""
        self._qa_history: list[tuple[str, str]] = []
        self._qa_current_answer: str = ""
        self._qa_pending_question: str = ""
        self._setup_window()
        self._setup_ui()
        self._setup_extract_module()
        self._setup_summary_module()
        self._setup_translate_module()
        self._setup_provider_connections()
        self._setup_style()
        self.setAcceptDrops(True)

    def _setup_window(self) -> None:
        """Cấu hình cửa sổ chính."""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(self._i18n.t("app.title"))
        self.setMinimumSize(900, 650)
        self.resize(960, 700)

    def _setup_ui(self) -> None:
        """Thiết lập layout và các widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Thanh tiêu đề tùy chỉnh
        self._title_bar = TitleBar(self)
        self._title_bar.close_clicked.connect(self.close)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        main_layout.addWidget(self._title_bar)

        # Vùng nội dung chính
        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 12)
        content_layout.setSpacing(10)

        # Hàng trên: máy xay (trái) + bảng danh sách file (phải)
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self._blender = BlenderArea()
        top_row.addWidget(self._blender, stretch=1)

        self._file_table = FileTable()
        self._file_table.setVisible(False)
        top_row.addWidget(self._file_table, stretch=2)

        content_layout.addLayout(top_row, stretch=2)

        # Vùng tóm tắt kết quả (chiếm nhiều không gian hơn)
        self._summary_area = SummaryArea()
        content_layout.addWidget(self._summary_area, stretch=5)

        # Vùng theo dõi chi phí
        self._cost_tracker = CostTracker()
        content_layout.addWidget(self._cost_tracker)

        # Thanh công cụ
        self._toolbar = Toolbar()
        self._toolbar.settings_clicked.connect(self._open_settings)
        self._toolbar.summary_clicked.connect(self._on_summary)
        self._toolbar.translate_clicked.connect(self._open_translate)
        self._toolbar.guide_clicked.connect(self._open_guide)
        self._toolbar.about_clicked.connect(self._open_about)
        # Click vào vùng drop = mở file picker
        self._blender.body_clicked.connect(self._on_open_file_dialog)
        content_layout.addWidget(self._toolbar)

        main_layout.addWidget(content, stretch=1)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho cửa sổ."""
        self.setStyleSheet(f"""
            MainWindow {{
                background-color: {theme.BG_BASE};
                border: 1px solid {theme.SURFACE_1};
                border-radius: 10px;
            }}
            #content {{
                background-color: {theme.BG_BASE};
            }}
            #content QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
            }}
            QPushButton {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: none;
                border-radius: {theme.RADIUS_SM}px;
                padding: 8px 16px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.SURFACE_2};
            }}
            QPushButton:pressed {{
                background-color: {theme.SURFACE_0};
            }}
        """)

    def _setup_provider_connections(self) -> None:
        """Kết nối ProviderManager với UI."""
        pass

    # --- Drag & Drop ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Xử lý khi file được kéo vào cửa sổ."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._blender.set_drag_hover(True)

    def dragLeaveEvent(self, event: Any) -> None:
        """Xử lý khi file rời khỏi cửa sổ."""
        self._blender.set_drag_hover(False)

    def dropEvent(self, event: QDropEvent) -> None:
        """Xử lý khi file được thả vào cửa sổ."""
        self._blender.set_drag_hover(False)
        files: list[Path] = []
        unsupported: list[str] = []

        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
            elif path.is_file():
                unsupported.append(path.name)

        # Thông báo file không hỗ trợ
        if unsupported:
            supported_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            file_list = "\n".join(f"• {n}" for n in unsupported)
            MessageDialog.warning(
                self,
                "File không hỗ trợ",
                f"Các file sau không được hỗ trợ:\n{file_list}\n\nĐịnh dạng hỗ trợ: {supported_list}",
            )

        if files:
            self._file_table.add_files(files, checked=True)
            self._file_table.setVisible(True)
            self._blender.play_file_drop()
            self.files_added.emit(files)
            logger.info("Đã thêm %d file.", len(files))

    # --- Window dragging (frameless) ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Ghi nhận vị trí chuột khi bắt đầu kéo cửa sổ."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Di chuyển cửa sổ khi kéo."""
        if self._drag_start_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Kết thúc kéo cửa sổ."""
        self._drag_start_pos = None

    def _setup_extract_module(self) -> None:
        """Khởi tạo ExtractModule và kết nối signal."""
        self._extract_module = ExtractModule(self)

        # Kết nối signal từ ExtractModule đến UI
        self._extract_module.file_started.connect(self._on_extract_file_started)
        self._extract_module.file_completed.connect(self._on_extract_file_completed)
        self._extract_module.file_failed.connect(self._on_extract_file_failed)
        self._extract_module.extract_completed.connect(self._on_extract_completed)

        # Kết nối nút Stop từ CostTracker
        self._cost_tracker.stop_clicked.connect(self._on_stop_clicked)

        # Xóa cache khi file bị xóa khỏi bảng
        self._file_table.file_removed.connect(self._extract_module.invalidate)
        self._file_table.file_removed.connect(self._on_file_removed)

    def _setup_summary_module(self) -> None:
        """Khởi tạo SummaryModule, QAModule và kết nối signal."""
        self._summary_module = SummaryModule(self)
        self._summary_module.set_provider_manager(self._provider_manager)

        # Báo cáo hoàn chỉnh → trích xuất tổng quan hiển thị UI
        self._summary_module.report_ready.connect(self._on_report_ready)
        # Trạng thái → cập nhật blender animation
        self._summary_module.status_updated.connect(self._on_summary_status)
        # File .md chi tiết → lưu đường dẫn cho nút "Chi tiết"
        self._summary_module.detail_file_ready.connect(self._on_summary_detail_ready)
        # Hoàn tất → reset UI
        self._summary_module.summary_completed.connect(self._on_summary_completed)

        # Nút "Chi tiết" → mở file .md
        self._summary_area.detail_clicked.connect(self._on_detail_clicked)

        # Q&A module
        self._qa_module = QAModule(self)
        self._qa_module.set_provider_manager(self._provider_manager)
        self._qa_module.streaming_text.connect(self._on_qa_streaming)
        self._qa_module.completed.connect(self._on_qa_completed)

        # Q&A input → bắt đầu Q&A
        self._summary_area.qa_submitted.connect(self._on_qa_submitted)

    def _setup_translate_module(self) -> None:
        """Khởi tạo TranslateModule."""
        self._translate_module = TranslateModule(self)
        self._translate_module.set_provider_manager(self._provider_manager)

    # --- Slots ---

    def _create_overlay(self, target: QWidget | None = None) -> QWidget:
        """Tạo lớp phủ tối mờ lên widget chỉ định (hoặc cửa sổ chính nếu None)."""
        parent: QWidget = target if target is not None else self
        overlay = QWidget(parent)
        overlay.setObjectName("dialogOverlay")
        overlay.setStyleSheet(
            "#dialogOverlay { background-color: rgba(0, 0, 0, 120); }"
        )
        overlay.setGeometry(parent.rect())
        overlay.show()
        overlay.raise_()
        return overlay

    def _open_settings(self) -> None:
        """Mở dialog cài đặt API Key."""
        overlay = self._create_overlay()
        dialog = SettingsDialog(self, provider_manager=self._provider_manager)
        dialog.exec()
        overlay.deleteLater()

    def _open_guide(self) -> None:
        """Mở dialog hướng dẫn sử dụng."""
        overlay = self._create_overlay()
        GuideDialog(self).exec()
        overlay.deleteLater()

    def _open_about(self) -> None:
        """Mở dialog thông tin ứng dụng."""
        overlay = self._create_overlay()
        provider = self._provider_manager.provider
        active_name = provider.name if provider else ""
        AboutDialog(self, active_provider=active_name).exec()
        overlay.deleteLater()

    def _on_open_file_dialog(self) -> None:
        """Mở hộp thoại chọn file khi click vào vùng kéo thả."""
        if self._extract_module.is_running or self._summary_module.is_running:
            return
        ext_str = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTENSIONS))
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn tài liệu",
            str(Path.home()),
            f"Tài liệu hỗ trợ ({ext_str})",
        )
        if files:
            paths = [Path(f) for f in files]
            self._file_table.add_files(paths, checked=True)
            self._file_table.setVisible(True)
            self._blender.play_file_drop()
            self.files_added.emit(paths)

    def _on_summary(self) -> None:
        """Bấm Tổng hợp → tự động extract (nếu cần) rồi gọi AI tổng hợp."""
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            MessageDialog.warning(
                self, "Chưa chọn file",
                "Chưa có file nào được chọn. Hãy tick chọn file trong bảng.",
            )
            return

        if not self._provider_manager.provider:
            MessageDialog.warning(
                self, "Chưa cấu hình AI",
                "Chưa cấu hình AI Provider. Vào Cài đặt để thêm API key.",
            )
            return

        if self._extract_module.is_running or self._summary_module.is_running:
            return

        self._grind_files = list(checked_files)
        self._grind_cancelled = False
        self._extract_errors.clear()
        self._detail_report_path = ""
        self._summary_context = ""
        self._qa_history = []
        self._qa_current_answer = ""

        self._summary_area.clear()
        self._provider_manager.token_counter.reset()

        for f in checked_files:
            self._file_table.update_file_status(f, "processing")

        # Nếu còn file chưa extract → extract trước (hiện processing ngay), sau đó summary
        uncached = [f for f in checked_files if self._extract_module.get_cached(f) is None]
        if uncached:
            self._blender.set_status("Đang xử lý...")
            self._toolbar.set_processing(True)
            self._cost_tracker.set_processing(True)
            self._pending_summary = True
            self._extract_module.start_extract(checked_files)
        else:
            # Tất cả đã cache → hiển thị dialog xác nhận trước, chưa set processing
            self._pending_summary = False
            contents: dict[Path, ExtractedContent] = {
                f: self._extract_module.get_cached(f)
                for f in checked_files
            }
            self._confirm_and_run_summary(contents)

    def _on_extract_file_started(self, file_path: Path) -> None:
        """Cập nhật UI khi bắt đầu extract một file."""
        self._file_table.update_file_status(file_path, "processing")

    def _on_extract_file_completed(
        self, file_path: Path, content: ExtractedContent
    ) -> None:
        """Extract một file thành công — giữ trạng thái processing cho đến khi summary xong."""

    def _on_extract_file_failed(self, file_path: Path, error_msg: str) -> None:
        """Cập nhật UI khi extract một file thất bại."""
        self._extract_errors[file_path] = error_msg
        self._file_table.update_file_status(file_path, "error")
        logger.error("Extract thất bại: %s - %s", safe_file_label(file_path), sanitize_error(error_msg))

    def _on_extract_completed(self, success_count: int, fail_count: int) -> None:
        """Toàn bộ extract hoàn tất — tự động bắt đầu summary nếu đang pending."""
        if self._grind_cancelled:
            self._reset_processing_ui()
            return

        if self._pending_summary:
            self._pending_summary = False
            contents: dict[Path, ExtractedContent] = {}
            for f in self._grind_files:
                cached = self._extract_module.get_cached(f)
                if cached:
                    contents[f] = cached

            if not contents:
                self._reset_processing_ui()
                for f in self._grind_files:
                    self._file_table.update_file_status(f, "error")
                error_details = list(dict.fromkeys(self._extract_errors.values()))
                message = (
                    "\n".join(error_details)
                    if error_details
                    else "Extract thất bại. Không thể tổng hợp."
                )
                self._summary_area.set_summary(
                    message, typing_effect=False
                )
                return

            self._confirm_and_run_summary(contents)

    def _on_file_removed(self, path: Path) -> None:
        """Ẩn bảng file khi không còn file nào."""
        if self._file_table.file_count == 0:
            self._file_table.setVisible(False)

    def _on_stop_clicked(self) -> None:
        """Xử lý khi người dùng bấm Stop — hủy extract hoặc summary đang chạy."""
        self._grind_cancelled = True

        if self._extract_module.is_running:
            self._extract_module.cancel()

        if self._summary_module.is_running:
            self._summary_module.cancel()

        if self._qa_module.is_running:
            self._qa_module.cancel()

        self._reset_processing_ui()

    # --- Summary signal handlers ---

    def _on_report_ready(self, full_report: str) -> None:
        """Nhận báo cáo đầy đủ → lưu context, trích xuất tổng quan cho UI."""
        self._summary_context = full_report
        overview = self._extract_overview(full_report)
        self._summary_area.set_summary(overview, typing_effect=False)

    def _extract_overview(self, report: str) -> str:
        """Trích xuất phần tổng quan chung từ báo cáo để hiển thị trên UI.

        Args:
            report: Báo cáo Markdown đầy đủ.

        Returns:
            Nội dung phần tổng quan, kèm gợi ý tải file chi tiết.
        """
        marker = "## 1. Tổng quan chung"
        start_idx = report.find(marker)
        if start_idx == -1:
            # Fallback: 600 ký tự đầu
            overview = report[:600].strip()
        else:
            content_start = report.find("\n", start_idx) + 1
            end_idx = report.find("\n---", content_start)
            if end_idx == -1:
                overview = report[content_start:content_start + 800].strip()
            else:
                overview = report[content_start:end_idx].strip()

        return overview + "\n\n─────────────────────────\n💡 Bấm 'Chi tiết ↓' để tải đầy đủ báo cáo phân tích."

    def _on_summary_status(self, status: str) -> None:
        """Cập nhật trạng thái blender animation khi summary đang chạy."""
        self._blender.set_status(status)

    def _on_summary_detail_ready(self, report_path: str) -> None:
        """Lưu đường dẫn file HTML chi tiết và hiển thị nút 'Chi tiết'."""
        self._detail_report_path = report_path
        self._summary_area.show_detail_button()
        logger.info("Báo cáo chi tiết đã sẵn sàng: %s", safe_file_label(report_path))

    def _on_summary_completed(self, success: bool, error_msg: str) -> None:
        """Xử lý khi tổng hợp hoàn tất hoặc thất bại."""
        self._reset_processing_ui()

        if not success and error_msg and error_msg != "Đã hủy":
            self._summary_area.set_summary(
                f"[LỖI] {error_msg}", typing_effect=False,
            )
            for f in self._grind_files:
                self._file_table.update_file_status(f, "error")
            logger.error("Tổng hợp thất bại: %s", sanitize_error(error_msg))
        else:
            self._blender.play_done()
            if success:
                for f in self._grind_files:
                    status = "done" if self._extract_module.get_cached(f) else "error"
                    self._file_table.update_file_status(f, status)
                self._summary_area.show_qa_input()

    def _on_detail_clicked(self) -> None:
        """Tạo file HTML báo cáo (kèm Q&A nếu có) và lưu vào Downloads."""
        if not self._summary_context:
            return

        downloads = self._summary_module.output_dir
        downloads.mkdir(parents=True, exist_ok=True)

        # Lấy tên file gốc từ temp path nếu có, không thì tạo mới
        from datetime import datetime
        if self._detail_report_path:
            stem = Path(self._detail_report_path).stem
        else:
            stem = f"lazydoc_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        dest_path = downloads / f"{stem}.html"
        counter = 1
        while dest_path.exists():
            dest_path = downloads / f"{stem} ({counter}).html"
            counter += 1

        # Sinh HTML từ report gốc + Q&A hiện tại
        html_content = _md_to_html(
            self._summary_context,
            qa_history=self._qa_history or None,
        )
        dest_path.write_text(html_content, encoding="utf-8")
        logger.info("Đã tải báo cáo về: %s", safe_file_label(dest_path))

        MessageDialog.information(
            self,
            "Đã tải về",
            f"File báo cáo đã được lưu tại:\n{dest_path}",
        )

    # --- Q&A signal handlers ---

    def _on_qa_submitted(self, question: str) -> None:
        """Xử lý khi người dùng gửi câu hỏi Q&A."""
        if not self._summary_context:
            return
        if self._qa_module.is_running:
            return

        self._qa_current_answer = ""
        self._summary_area.append_qa_question(question)
        self._summary_area.show_disclaimer()

        self._qa_module.start_qa(
            summary_context=self._summary_context,
            qa_history=self._qa_history,
            question=question,
        )
        # Lưu câu hỏi để ghép với câu trả lời sau khi hoàn tất
        self._qa_pending_question = question

    def _on_qa_streaming(self, text: str) -> None:
        """Nhận text streaming từ Q&A → ẩn disclaimer, hiển thị câu trả lời."""
        self._summary_area.hide_disclaimer()
        self._summary_area.append_text(text)
        self._qa_current_answer += text

    def _on_qa_completed(self, success: bool, error_msg: str) -> None:
        """Xử lý khi Q&A hoàn tất."""
        self._summary_area.hide_disclaimer()
        self._summary_area.set_qa_processing(False)

        if success and self._qa_current_answer:
            self._qa_history.append(
                (self._qa_pending_question, self._qa_current_answer)
            )
            self._qa_current_answer = ""
        elif not success and error_msg and error_msg != "Đã hủy":
            self._summary_area.append_text(f"\n[Lỗi Q&A: {error_msg}]")
            logger.error("Q&A thất bại: %s", sanitize_error(error_msg))

    def _confirm_and_run_summary(self, contents: dict[Path, ExtractedContent]) -> None:
        """Hiển thị dialog xác nhận (nếu nhiều API call) rồi chạy summary."""
        from src.core.cost_estimator import estimate_from_contents
        from src.ui.dialogs.confirmation_dialog import ConfirmationDialog
        from PySide6.QtWidgets import QDialog

        estimate = estimate_from_contents(contents, "summary")
        if not ConfirmationDialog.should_skip(estimate):
            overlay = self._create_overlay()
            dlg = ConfirmationDialog(estimate, mode="summary", parent=self)
            result = dlg.exec()
            overlay.deleteLater()
            if result != QDialog.DialogCode.Accepted:
                self._reset_processing_ui()
                for f in contents:
                    self._file_table.update_file_status(f, "ready")
                return

        # Bắt đầu processing chỉ sau khi người dùng xác nhận
        self._blender.set_status("Đang tổng hợp...")
        self._toolbar.set_processing(True)
        self._cost_tracker.set_processing(True)

        self._summary_module.start_summary(contents)

    def _reset_processing_ui(self) -> None:
        """Reset trạng thái UI về chế độ bình thường (không đang xử lý)."""
        self._blender.set_status("")
        self._toolbar.set_processing(False)
        self._cost_tracker.set_processing(False)

    def _open_translate(self) -> None:
        """Mở dialog dịch thuật với các file đã checked."""
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            MessageDialog.warning(
                self, "Chưa chọn file",
                "Chưa có file nào được chọn. Hãy tick chọn file trong bảng.",
            )
            return

        overlay = self._create_overlay()
        dialog = TranslateDialog(checked_files, self)  # type: ignore[arg-type]

        # Kết nối Dialog → TranslateModule, kèm summary context nếu đã có
        context = self._summary_context.strip() or None
        translate_errors: list[str] = []

        def _on_translate_requested(config: dict) -> None:
            translate_errors.clear()
            if config.get("mode") == "smart" and self._provider_manager.provider:
                from src.core.cost_estimator import estimate_from_contents, estimate_from_files
                from src.ui.dialogs.confirmation_dialog import ConfirmationDialog
                from PySide6.QtWidgets import QDialog

                files: list[Path] = config["files"]
                cached = {
                    f: self._extract_module.get_cached(f)
                    for f in files
                    if self._extract_module.get_cached(f) is not None
                }
                if cached:
                    estimate = estimate_from_contents(cached, "translate")
                else:
                    estimate = estimate_from_files(files, "translate")

                if not ConfirmationDialog.should_skip(estimate):
                    overlay = self._create_overlay(dialog)
                    conf = ConfirmationDialog(estimate, mode="translate", parent=dialog)
                    result = conf.exec()
                    overlay.deleteLater()
                    if result != QDialog.DialogCode.Accepted:
                        dialog.on_translate_done()
                        return

            # Bắt đầu processing chỉ sau khi xác nhận (hoặc skip confirmation)
            dialog.set_translating()
            self._translate_module.start_translate({**config, "context": context})

        dialog.translate_requested.connect(_on_translate_requested)
        dialog.stop_requested.connect(self._translate_module.cancel)

        def _on_file_failed(_file_path: Path, error_msg: str) -> None:
            translate_errors.append(error_msg)

        def _on_completed(s, f, _):
            dialog.on_translate_done(
                s,
                f,
                str(self._translate_module.output_dir),
                translate_errors,
            )

        def _on_error(msg):
            self._on_translate_error(dialog, msg)

        self._translate_module.status_updated.connect(dialog.update_status)
        self._translate_module.file_failed.connect(_on_file_failed)
        self._translate_module.translate_completed.connect(_on_completed)
        self._translate_module.error_occurred.connect(_on_error)

        dialog.exec()

        # Ngắt toàn bộ kết nối khi đóng dialog
        self._translate_module.status_updated.disconnect(dialog.update_status)
        self._translate_module.file_failed.disconnect(_on_file_failed)
        self._translate_module.translate_completed.disconnect(_on_completed)
        self._translate_module.error_occurred.disconnect(_on_error)
        overlay.deleteLater()

    def _on_translate_error(self, dialog: TranslateDialog, msg: str) -> None:
        """Xử lý lỗi từ TranslateModule — reset dialog và hiển thị lỗi."""
        dialog.on_translate_done()
        MessageDialog.critical(dialog, "Lỗi dịch thuật", msg)
        self._summary_area.set_summary(f"[LỖI] {msg}", typing_effect=False)
        logger.error("Lỗi dịch thuật: %s", sanitize_error(msg))

    # --- Public API ---

    @property
    def provider_manager(self) -> ProviderManager:
        """Truy cập ProviderManager."""
        return self._provider_manager

    @property
    def extract_module(self) -> ExtractModule:
        """Truy cập module extract."""
        return self._extract_module

    @property
    def file_table(self) -> FileTable:
        """Truy cập bảng file."""
        return self._file_table

    @property
    def toolbar(self) -> "Toolbar":
        """Truy cập thanh công cụ."""
        return self._toolbar

    @property
    def summary_area(self) -> SummaryArea:
        """Truy cập vùng tóm tắt."""
        return self._summary_area

    @property
    def cost_tracker(self) -> CostTracker:
        """Truy cập vùng chi phí."""
        return self._cost_tracker

    @property
    def blender(self) -> BlenderArea:
        """Truy cập vùng máy xay."""
        return self._blender
