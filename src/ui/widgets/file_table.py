"""FileTable — Bảng danh sách file đã kéo thả vào ứng dụng."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager

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

        # Thiết lập header — bỏ label cho cột checkbox và xóa
        headers = [
            "",
            self._i18n.t("main.col_filename"),
            self._i18n.t("main.col_size"),
            self._i18n.t("main.col_status"),
            "",
        ]
        self._table.setHorizontalHeaderLabels(headers)

        # Cấu hình header
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_SELECT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_FILENAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_DELETE, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(COL_SELECT, 50)
        self._table.setColumnWidth(COL_SIZE, 70)
        self._table.setColumnWidth(COL_STATUS, 120)
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

        # Checkbox chọn
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox_layout.addWidget(checkbox)
        self._table.setCellWidget(row, COL_SELECT, checkbox_widget)

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

        # Trạng thái ban đầu (căn giữa)
        status_item = QTableWidgetItem("Chưa extract")
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, COL_STATUS, status_item)

        # Nút xóa
        delete_widget = QWidget()
        delete_layout = QHBoxLayout(delete_widget)
        delete_layout.setContentsMargins(0, 0, 0, 0)
        delete_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        delete_btn = QPushButton("🗑")
        delete_btn.setObjectName("deleteBtn")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda checked, r=row, p=path: self._remove_file(p))
        delete_layout.addWidget(delete_btn)
        self._table.setCellWidget(row, COL_DELETE, delete_widget)

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
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    checked.append(self._file_paths[row])
        return checked

    def update_file_status(self, path: Path, status: str) -> None:
        """Cập nhật trạng thái của file trong bảng.

        Args:
            path: Đường dẫn file.
            status: Trạng thái mới (ví dụ: '✓', '✗', 'Đã dừng').
        """
        if path in self._file_paths:
            row = self._file_paths.index(path)
            item = self._table.item(row, COL_STATUS)
            if item:
                item.setText(status)

    def clear_all(self) -> None:
        """Xóa toàn bộ file trong bảng."""
        self._table.setRowCount(0)
        self._file_paths.clear()

    @property
    def file_count(self) -> int:
        """Số lượng file trong bảng."""
        return len(self._file_paths)
