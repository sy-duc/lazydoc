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
from src.ui.dialogs.settings_dialog import SettingsDialog
from src.ui.dialogs.translate_dialog import TranslateDialog
from src.ui.widgets.file_table import FileTable
from src.ui.widgets.blender_area import BlenderArea
from src.ui.widgets.summary_area import SummaryArea
from src.ui.widgets.cost_tracker import CostTracker
from src.ui.widgets.toolbar import Toolbar
from src.ui.widgets.title_bar import TitleBar

logger = logging.getLogger(__name__)

# Định dạng file được hỗ trợ
SUPPORTED_EXTENSIONS = {
    ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".ppt",
    ".pdf", ".txt", ".csv",
    ".png", ".jpg", ".jpeg", ".bmp", ".gif",
}


class MainWindow(QWidget):
    """Cửa sổ chính của ứng dụng LazyDoc."""

    # Signal khi có file được thêm vào
    files_added = Signal(list)

    def __init__(self) -> None:
        """Khởi tạo MainWindow."""
        super().__init__()
        self._i18n = I18nManager()
        self._drag_start_pos = None
        self._setup_window()
        self._setup_ui()
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

    # --- Slots ---

    def _open_settings(self) -> None:
        """Mở dialog cài đặt API Key."""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _open_translate(self) -> None:
        """Mở dialog dịch thuật với các file đã checked."""
        checked_files = self._file_table.get_checked_files()
        if not checked_files:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                self._i18n.t("translate.title"),
                self._i18n.t("translate.no_files"),
            )
            return
        dialog = TranslateDialog(checked_files, self)
        dialog.exec()

    # --- Public API ---

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
