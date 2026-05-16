"""MainWindow — Màn hình chính của ứng dụng LazyDoc."""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.modules.extract import ExtractModule
from src.modules.summarizer import SummaryModule, QAModule, _md_to_html
from src.modules.translator import TranslateModule
from src.processors.base import ExtractedContent
from src.processors.factory import ProcessorFactory
from src.providers.provider_manager import ProviderManager
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
        self._extract_results: list[str] = []
        self._grind_files: list[Path] = []
        self._grind_cancelled = False
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
        # Click vào máy xay = Extract (đọc file thô)
        self._blender.body_clicked.connect(self._on_grind)
        content_layout.addWidget(self._toolbar)

        main_layout.addWidget(content, stretch=1)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho cửa sổ."""
        self.setStyleSheet("""
            MainWindow {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 10px;
            }
            #content {
                background-color: #1e1e2e;
            }
            #content QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #585b70;
            }
            QPushButton:pressed {
                background-color: #313244;
            }
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
            QMessageBox.warning(
                self,
                "File không hỗ trợ",
                f"Các file sau không được hỗ trợ:\n{file_list}\n\n"
                f"Định dạng hỗ trợ: {supported_list}",
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

    def _create_overlay(self) -> QWidget:
        """Tạo lớp phủ tối mờ lên cửa sổ chính khi mở dialog."""
        overlay = QWidget(self)
        overlay.setObjectName("dialogOverlay")
        overlay.setStyleSheet(
            "#dialogOverlay { background-color: rgba(0, 0, 0, 120); }"
        )
        overlay.setGeometry(self.rect())
        overlay.show()
        overlay.raise_()
        return overlay

    def _open_settings(self) -> None:
        """Mở dialog cài đặt API Key."""
        overlay = self._create_overlay()
        dialog = SettingsDialog(self, provider_manager=self._provider_manager)
        dialog.exec()
        overlay.deleteLater()

    def _on_grind(self) -> None:
        """Bấm Xay → Extract only (đọc file thô, chưa gọi AI).

        Chuyển đổi nội dung file sang dạng trung gian. Sau khi extract xong,
        người dùng có thể chọn Tổng hợp hoặc Dịch.
        """
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            self._summary_area.set_summary(
                self._i18n.t("main.no_file_selected"),
                typing_effect=False,
            )
            return

        if self._extract_module.is_running or self._summary_module.is_running:
            logger.warning("Đang xử lý, bỏ qua.")
            return

        # Lưu danh sách file
        self._grind_files = list(checked_files)
        self._grind_cancelled = False

        # Chuẩn bị UI
        self._extract_results.clear()
        self._blender.set_status("Extracting...")
        self._toolbar.set_processing(True)
        self._cost_tracker.set_processing(True)
        self._summary_area.clear()

        # Cập nhật trạng thái
        for file_path in checked_files:
            self._file_table.update_file_status(file_path, "Extracting...")

        # Bắt đầu extract (async trên QThread)
        self._extract_module.start_extract(checked_files)

    def _on_summary(self) -> None:
        """Bấm Tổng hợp → gọi AI tổng hợp thông tin (yêu cầu đã extract).

        Kiểm tra file đã được extract chưa. Nếu chưa → thông báo.
        Nếu rồi → gọi AI Provider tổng hợp.
        """
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self, "Chưa chọn file",
                "Chưa có file nào được chọn. Hãy tick chọn file trong bảng.",
            )
            return

        # Kiểm tra file đã extract chưa
        uncached = [
            f for f in checked_files
            if self._extract_module.get_cached(f) is None
        ]
        if uncached:
            file_lines = "\n".join(f"  • {f.name}" for f in uncached)
            QMessageBox.warning(
                self,
                "Chưa extract",
                f"Các file sau chưa được extract:\n{file_lines}\n\n"
                "Hãy click vào máy xay để extract trước.",
            )
            return

        # Kiểm tra provider
        if not self._provider_manager.provider:
            QMessageBox.warning(
                self, "Chưa cấu hình AI",
                "Chưa cấu hình AI Provider. Vào Cài đặt để thêm API key.",
            )
            return

        if self._summary_module.is_running:
            logger.warning("Tổng hợp đang chạy, bỏ qua.")
            return

        # Thu thập nội dung đã extract
        self._grind_files = list(checked_files)
        self._grind_cancelled = False
        self._detail_report_path = ""
        self._summary_context = ""
        contents: dict[Path, ExtractedContent] = {}
        for f in checked_files:
            cached = self._extract_module.get_cached(f)
            if cached:
                contents[f] = cached

        # Reset Q&A session
        self._qa_history = []
        self._qa_current_answer = ""

        # Chuẩn bị UI
        self._blender.set_status("Analysing...")
        self._toolbar.set_processing(True)
        self._cost_tracker.set_processing(True)
        self._summary_area.clear()
        self._provider_manager.token_counter.reset()

        # Bắt đầu tổng hợp
        self._summary_module.start_summary(contents)

    def _on_extract_file_started(self, file_path: Path) -> None:
        """Cập nhật UI khi bắt đầu extract một file."""
        self._file_table.update_file_status(file_path, "Extracting...")

    def _on_extract_file_completed(
        self, file_path: Path, content: ExtractedContent
    ) -> None:
        """Cập nhật UI khi extract một file thành công."""
        self._file_table.update_file_status(file_path, "Đã extract")

        # Chuẩn bị text tóm tắt cho file này
        parts: list[str] = []

        full_text = content.get_full_text()
        if full_text:
            preview = full_text[:200] + "..." if len(full_text) > 200 else full_text
            parts.append(preview)

        if content.shapes_text:
            total_shapes = sum(len(v) for v in content.shapes_text.values())
            parts.append(f"[Shapes ({total_shapes})]")
            for section, texts in content.shapes_text.items():
                for t in texts[:3]:
                    parts.append(f"  [{section}] {t[:80]}")

        if content.images:
            keys_preview = ", ".join(list(content.images.keys())[:3])
            parts.append(f"[Images: {len(content.images)} file(s): {keys_preview}]")

        self._extract_results.append(
            f"--- {content.file_name} ---\n" + "\n".join(parts)
        )

    def _on_extract_file_failed(self, file_path: Path, error_msg: str) -> None:
        """Cập nhật UI khi extract một file thất bại."""
        self._file_table.update_file_status(file_path, "Lỗi extract")
        self._extract_results.append(
            f"--- {file_path.name} ---\n[LỖI] {error_msg}"
        )
        logger.error("Extract thất bại: %s — %s", file_path.name, error_msg)

    def _on_extract_completed(self, success_count: int, fail_count: int) -> None:
        """Cập nhật UI khi toàn bộ extract hoàn tất.

        Hiển thị thông báo kết quả và hướng dẫn bước tiếp theo.
        """
        if self._grind_cancelled:
            return

        self._reset_processing_ui()
        self._blender.play_done()

        # Thông báo kết quả extract
        if success_count == 0:
            msg = f"Extract thất bại toàn bộ {fail_count} file."
            self._summary_area.set_summary(msg, typing_effect=False)
            return

        # Liệt kê từng file đã extract
        file_lines = "\n".join(
            f"  • {f.name}" for f in self._grind_files
            if self._extract_module.get_cached(f) is not None
        )
        msg = f"Đã extract {success_count} file:\n{file_lines}"
        if fail_count > 0:
            msg += f"\n({fail_count} file lỗi)"
        self._summary_area.set_summary(msg, typing_effect=False)

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
        logger.info("Báo cáo chi tiết đã sẵn sàng: %s", report_path)

    def _on_summary_completed(self, success: bool, error_msg: str) -> None:
        """Xử lý khi tổng hợp hoàn tất hoặc thất bại."""
        self._reset_processing_ui()

        if not success and error_msg and error_msg != "Đã hủy":
            self._summary_area.set_summary(
                f"[LỖI] {error_msg}", typing_effect=False,
            )
            logger.error("Tổng hợp thất bại: %s", error_msg)
        else:
            self._blender.play_done()
            if success:
                for f in self._grind_files:
                    self._file_table.update_file_status(f, "Đã summary")
                # Hiển thị Q&A input sau khi tổng hợp thành công
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
        logger.info("Đã tải báo cáo về: %s", dest_path)

        QMessageBox.information(
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
            logger.error("Q&A thất bại: %s", error_msg)

    def _reset_processing_ui(self) -> None:
        """Reset trạng thái UI về chế độ bình thường (không đang xử lý)."""
        self._blender.set_status("")
        self._toolbar.set_processing(False)
        self._cost_tracker.set_processing(False)

    def _open_translate(self) -> None:
        """Mở dialog dịch thuật với các file đã checked."""
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            QMessageBox.warning(
                self, "Chưa chọn file",
                "Chưa có file nào được chọn. Hãy tick chọn file trong bảng.",
            )
            return

        overlay = self._create_overlay()
        dialog = TranslateDialog(checked_files, self)

        # Kết nối Dialog → TranslateModule, kèm summary context nếu đã có
        context = self._summary_context.strip() or None
        dialog.translate_requested.connect(
            lambda config: self._translate_module.start_translate(
                {**config, "context": context}
            )
        )
        dialog.stop_requested.connect(self._translate_module.cancel)

        # Kết nối TranslateModule → Dialog (lưu ref để ngắt sau)
        def _on_completed(s, f, _):
            dialog.on_translate_done(s, f, str(self._translate_module.output_dir))

        def _on_error(msg):
            self._on_translate_error(dialog, msg)

        self._translate_module.status_updated.connect(dialog.update_status)
        self._translate_module.translate_completed.connect(_on_completed)
        self._translate_module.error_occurred.connect(_on_error)

        dialog.exec()

        # Ngắt toàn bộ kết nối khi đóng dialog
        self._translate_module.status_updated.disconnect(dialog.update_status)
        self._translate_module.translate_completed.disconnect(_on_completed)
        self._translate_module.error_occurred.disconnect(_on_error)
        overlay.deleteLater()

    def _on_translate_error(self, dialog: TranslateDialog, msg: str) -> None:
        """Xử lý lỗi từ TranslateModule — reset dialog và hiển thị lỗi."""
        dialog.on_translate_done()
        QMessageBox.critical(dialog, "Lỗi dịch thuật", msg)
        self._summary_area.set_summary(f"[LỖI] {msg}", typing_effect=False)
        logger.error("Lỗi dịch thuật: %s", msg)

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
