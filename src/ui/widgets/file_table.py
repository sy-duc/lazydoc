"""FileTable — Bảng danh sách file đã kéo thả vào ứng dụng."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.ui import theme

logger = logging.getLogger(__name__)

# Thứ tự cột trong bảng
COL_SELECT = 0
COL_FILENAME = 1
COL_SIZE = 2
COL_STATUS = 3
COL_DELETE = 4

NUM_COLUMNS = 5


def _format_file_size(size_bytes: int) -> str:
    """Format kích thước file cho dễ đọc.

    Args:
        size_bytes: Kích thước tính bằng bytes.

    Returns:
        Chuỗi kích thước đã format (ví dụ: '1.5 MB').
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


class CheckIcon(QLabel):
    """Checkbox dạng icon toggle — thay thế QCheckBox mặc định."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent;")
        self._refresh()

    def _refresh(self) -> None:
        if self._checked:
            self.setPixmap(theme.pixmap("checkbox-marked", theme.BLUE, 18))
        else:
            self.setPixmap(theme.pixmap("checkbox-blank-outline", theme.SURFACE_2, 18))

    def mousePressEvent(self, event: object) -> None:
        self._checked = not self._checked
        self._refresh()
        self.toggled.emit(self._checked)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked != checked:
            self._checked = checked
            self._refresh()


class FileTable(QWidget):
    """Bảng hiển thị danh sách file đã kéo thả."""

    file_removed = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo FileTable."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self._file_paths: list[Path] = []
        self.setObjectName("fileTableContainer")
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập bảng file."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, NUM_COLUMNS)
        self._table.setObjectName("fileTable")

        # Thiết lập header — bỏ label cho cột checkbox, status và xóa
        headers = [
            "",
            self._i18n.t("main.col_filename"),
            self._i18n.t("main.col_size"),
            "",
            "",
        ]
        self._table.setHorizontalHeaderLabels(headers)

        # Căn trái header tên file
        fname_header = self._table.horizontalHeaderItem(COL_FILENAME)
        if fname_header:
            fname_header.setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )

        # Cấu hình header
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_SELECT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_FILENAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_DELETE, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(COL_SELECT, 50)
        self._table.setColumnWidth(COL_SIZE, 70)
        self._table.setColumnWidth(COL_STATUS, 52)
        self._table.setColumnWidth(COL_DELETE, 40)

        # Cấu hình bảng
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)

        layout.addWidget(self._table)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho bảng file."""
        self.setStyleSheet("""
            #fileTable {
                background-color: #1e1e2e;
                alternate-background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                gridline-color: transparent;
                font-size: 12px;
            }
            #fileTable::item {
                padding: 4px 8px;
                border-bottom: 1px solid #313244;
            }
            #fileTable QHeaderView::section {
                background-color: #313244;
                color: #a6adc8;
                border: none;
                padding: 6px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QCheckBox {
                margin-left: 10px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #585b70;
                border-radius: 4px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            #deleteBtn {
                background-color: transparent;
                color: #a6adc8;
                border: none;
                font-size: 14px;
                padding: 2px;
                min-width: 24px;
                max-width: 24px;
            }
            #deleteBtn:hover {
                color: #f38ba8;
            }
        """)

    def add_files(self, paths: list[Path], checked: bool = False) -> None:
        """Thêm danh sách file vào bảng.

        Args:
            paths: Danh sách đường dẫn file.
            checked: Tự động check file khi thêm vào.
        """
        for path in paths:
            if path in self._file_paths:
                logger.info("File đã tồn tại trong bảng: %s", path.name)
                continue
            self._file_paths.append(path)
            self._add_row(path, checked=checked)

    def _add_row(self, path: Path, checked: bool = False) -> None:
        """Thêm một hàng vào bảng cho file.

        Args:
            path: Đường dẫn file.
            checked: Tự động check checkbox.
        """
        row = self._table.rowCount()
        self._table.insertRow(row)

        # Checkbox dạng icon
        checkbox = CheckIcon(checked=checked)
        self._table.setCellWidget(row, COL_SELECT, checkbox)

        # Tên file (cắt ngắn nếu quá dài, tooltip hiển thị đầy đủ)
        display_name = path.name
        if len(display_name) > 20:
            stem = path.stem
            suffix = path.suffix
            display_name = stem[:16] + "..." + suffix
        name_item = QTableWidgetItem(display_name)
        name_item.setToolTip(str(path))
        self._table.setItem(row, COL_FILENAME, name_item)

        # Kích thước (căn giữa)
        size = path.stat().st_size
        size_item = QTableWidgetItem(_format_file_size(size))
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_SIZE, size_item)

        # Trạng thái ban đầu
        self._table.setCellWidget(row, COL_STATUS, self._make_status_widget("idle"))

        # Nút xóa (icon)
        delete_widget = QWidget()
        delete_layout = QHBoxLayout(delete_widget)
        delete_layout.setContentsMargins(0, 0, 0, 0)
        delete_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delete_btn = QPushButton()
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setIcon(theme.icon("delete-outline", color=theme.SUBTEXT_0))
        delete_btn.setIconSize(QSize(16, 16))
        delete_btn.setToolTip("Xóa file")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda checked, r=row, p=path: self._remove_file(p))
        delete_layout.addWidget(delete_btn)
        self._table.setCellWidget(row, COL_DELETE, delete_widget)

        self._table.setRowHeight(row, 40)

    def _remove_file(self, path: Path) -> None:
        """Xóa file khỏi bảng.

        Args:
            path: Đường dẫn file cần xóa.
        """
        if path in self._file_paths:
            idx = self._file_paths.index(path)
            self._file_paths.remove(path)
            self._table.removeRow(idx)
            self.file_removed.emit(path)
            # Cập nhật lại connect cho các nút xóa
            self._reconnect_delete_buttons()
            logger.info("Đã xóa file: %s", path.name)

    def _reconnect_delete_buttons(self) -> None:
        """Cập nhật lại callback cho các nút xóa sau khi xóa hàng."""
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, COL_DELETE)
            if widget:
                btn = widget.findChild(QPushButton)
                if btn:
                    btn.clicked.disconnect()
                    path = self._file_paths[row]
                    btn.clicked.connect(lambda checked, p=path: self._remove_file(p))

    def get_checked_files(self) -> list[Path]:
        """Lấy danh sách file đã được chọn (checked).

        Returns:
            Danh sách đường dẫn file đã checked.
        """
        checked: list[Path] = []
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, COL_SELECT)
            if isinstance(widget, CheckIcon) and widget.isChecked():
                checked.append(self._file_paths[row])
        return checked

    def _make_status_widget(self, status: str) -> QLabel:
        """Tạo widget icon cho cột trạng thái.

        Args:
            status: Khóa trạng thái ('idle', 'processing', 'done', 'error').

        Returns:
            QLabel với icon tương ứng, nền trong suốt.
        """
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background: transparent;")

        if status == "processing":
            label.setPixmap(theme.pixmap("progress-clock", theme.YELLOW, 16))
            label.setToolTip("Đang xử lý")
        elif status == "done":
            label.setPixmap(theme.pixmap("check-circle", theme.GREEN, 16))
            label.setToolTip("Đã xử lý")
        elif status == "error":
            label.setPixmap(theme.pixmap("close-circle", theme.RED, 16))
            label.setToolTip("Lỗi xử lý")
        else:
            label.setPixmap(theme.pixmap("clock-outline", theme.MUTED, 16))
            label.setToolTip("Chưa xử lý")

        return label

    def update_file_status(self, path: Path, status: str) -> None:
        """Cập nhật icon trạng thái của file trong bảng.

        Args:
            path: Đường dẫn file.
            status: Khóa trạng thái ('idle', 'processing', 'done', 'error').
        """
        if path in self._file_paths:
            row = self._file_paths.index(path)
            self._table.setCellWidget(row, COL_STATUS, self._make_status_widget(status))

    def clear_all(self) -> None:
        """Xóa toàn bộ file trong bảng."""
        self._table.setRowCount(0)
        self._file_paths.clear()

    @property
    def file_count(self) -> int:
        """Số lượng file trong bảng."""
        return len(self._file_paths)
