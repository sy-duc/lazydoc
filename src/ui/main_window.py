"""MainWindow — Màn hình chính của ứng dụng LazyDoc."""

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.modules.extract import ExtractModule
from src.processors.base import ExtractedContent
from src.processors.factory import ProcessorFactory
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

    def __init__(self) -> None:
        """Khởi tạo MainWindow."""
        super().__init__()
        self._i18n = I18nManager()
        self._drag_start_pos = None
        self._extract_results: list[str] = []
        self._setup_window()
        self._setup_ui()
        self._setup_extract_module()
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

        # Vùng hoạt ảnh máy xay + drag & drop (phía trên)
        self._blender = BlenderArea()
        content_layout.addWidget(self._blender, stretch=2)

        # Bảng danh sách file (full width bên dưới — cột Ý nghĩa cần nhiều không gian)
        self._file_table = FileTable()
        content_layout.addWidget(self._file_table, stretch=3)

        # Vùng tóm tắt kết quả
        self._summary_area = SummaryArea()
        content_layout.addWidget(self._summary_area, stretch=2)

        # Vùng theo dõi chi phí
        self._cost_tracker = CostTracker()
        content_layout.addWidget(self._cost_tracker)

        # Thanh công cụ
        self._toolbar = Toolbar()
        self._toolbar.settings_clicked.connect(self._open_settings)
        self._toolbar.translate_clicked.connect(self._open_translate)
        self._toolbar.grind_clicked.connect(self._on_grind)
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
            QLabel {
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
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
            elif path.is_file():
                logger.warning("File không được hỗ trợ: %s", path.name)

        if files:
            self._file_table.add_files(files)
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
        self._cost_tracker.stop_clicked.connect(self._on_extract_cancel)

        # Xóa cache khi file bị xóa khỏi bảng
        self._file_table.file_removed.connect(self._extract_module.invalidate)

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
        dialog = SettingsDialog(self)
        dialog.exec()
        overlay.deleteLater()

    def _on_grind(self) -> None:
        """Bấm Xay → trigger Extract Module → cập nhật UI async."""
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            self._summary_area.set_summary(
                self._i18n.t("main.no_file_selected"),
                typing_effect=False,
            )
            return

        if self._extract_module.is_running:
            logger.warning("Extract đang chạy, bỏ qua.")
            return

        # Chuẩn bị UI cho quá trình extract
        self._extract_results.clear()
        self._blender.set_status("Extracting...")
        self._toolbar.set_processing(True)
        self._cost_tracker.set_processing(True)
        self._summary_area.clear()

        # Cập nhật trạng thái "đang chờ" cho các file checked
        for file_path in checked_files:
            self._file_table.update_file_status(file_path, "⏳")

        # Bắt đầu extract qua module (async trên QThread)
        self._extract_module.start_extract(checked_files)

    def _on_extract_file_started(self, file_path: Path) -> None:
        """Cập nhật UI khi bắt đầu extract một file."""
        self._file_table.update_file_status(file_path, "⏳")
        self._blender.set_status(f"Extracting: {file_path.name}")

    def _on_extract_file_completed(
        self, file_path: Path, content: ExtractedContent
    ) -> None:
        """Cập nhật UI khi extract một file thành công."""
        self._file_table.update_file_status(file_path, "✓")

        # Hiển thị metadata trên cột Ý nghĩa
        meta_parts = [f"{k}: {v}" for k, v in content.metadata.items()]
        meta_str = ", ".join(meta_parts) if meta_parts else "OK"
        self._file_table.update_file_purpose(file_path, meta_str)

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
        self._file_table.update_file_status(file_path, "✗")
        self._file_table.update_file_purpose(file_path, error_msg[:80])
        self._extract_results.append(
            f"--- {file_path.name} ---\n[LỖI] {error_msg}"
        )
        logger.error("Extract thất bại: %s — %s", file_path.name, error_msg)

    def _on_extract_completed(self, success_count: int, fail_count: int) -> None:
        """Cập nhật UI khi toàn bộ extract hoàn tất."""
        header = f"Extract hoàn tất: {success_count} thành công, {fail_count} thất bại\n\n"
        summary_text = header + "\n\n".join(self._extract_results)
        self._summary_area.set_summary(summary_text, typing_effect=True)

        self._blender.play_done()
        self._toolbar.set_processing(False)
        self._cost_tracker.set_processing(False)

    def _on_extract_cancel(self) -> None:
        """Xử lý khi người dùng bấm Stop trong lúc extract."""
        if self._extract_module.is_running:
            self._extract_module.cancel()
            self._blender.set_status("")
            self._toolbar.set_processing(False)
            self._cost_tracker.set_processing(False)

    def _open_translate(self) -> None:
        """Mở dialog dịch thuật với các file đã checked.

        Nếu file chưa được extract, sẽ trigger extract trước khi mở dialog.
        """
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            self._summary_area.set_summary(
                self._i18n.t("main.no_file_selected"),
                typing_effect=False,
            )
            return

        # Kiểm tra nếu có file chưa extract → trigger extract trước
        uncached = [
            f for f in checked_files
            if self._extract_module.get_cached(f) is None
        ]
        if uncached:
            self._summary_area.set_summary(
                self._i18n.t("main.extract_before_translate"),
                typing_effect=False,
            )
            return

        overlay = self._create_overlay()
        dialog = TranslateDialog(checked_files, self)
        dialog.exec()
        overlay.deleteLater()

    # --- Public API ---

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
