"""GlossaryDialog — Dialog quản lý bảng thuật ngữ."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.core.logging_config import sanitize_error
from src.modules.glossary.glossary_manager import GlossaryManager
from src.ui import theme
from src.ui.dialogs.message_dialog import MessageDialog

logger = logging.getLogger(__name__)

# Ngôn ngữ hỗ trợ
LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
    ("ja", "日本語"),
]

# Thứ tự cột trong bảng
COL_TERM_FROM = 0
COL_TERM_TO = 1
COL_ACTIONS = 2


class GlossaryDialog(QDialog):
    """Dialog quản lý bảng thuật ngữ — thêm, sửa, xóa, import/export CSV."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo GlossaryDialog.

        Args:
            parent: Widget cha.
        """
        super().__init__(parent)
        self._i18n = I18nManager()
        self._glossary = GlossaryManager()
        self._editing_id: int | None = None
        self._setup_window()
        self._setup_ui()
        self._setup_style()
        self._load_entries()

    def _setup_window(self) -> None:
        """Cấu hình dialog."""
        self.setWindowTitle(self._i18n.t("glossary.title"))
        self.setMinimumSize(560, 560)
        self.resize(600, 640)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)

    def _setup_ui(self) -> None:
        """Thiết lập layout và các widget."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(20, 20, 20, 20)

        self._panel = QWidget()
        self._panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self._panel.setGraphicsEffect(shadow)
        outer_layout.addWidget(self._panel)

        layout = QVBoxLayout(self._panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Tiêu đề
        title_label = QLabel(self._i18n.t("glossary.title"))
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # --- Cặp ngôn ngữ (nằm ngang) ---
        lang_row = QHBoxLayout()
        lang_row.setSpacing(12)

        lang_from_lbl = QLabel(self._i18n.t("glossary.lang_from"))
        lang_from_lbl.setObjectName("sectionLabel")
        lang_row.addWidget(lang_from_lbl)

        self._lang_from_combo = QComboBox()
        self._lang_from_combo.setObjectName("langCombo")
        self._lang_from_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in LANGUAGES:
            self._lang_from_combo.addItem(name, code)
        self._lang_from_combo.currentIndexChanged.connect(self._load_entries)
        lang_row.addWidget(self._lang_from_combo, stretch=1)

        arrow_lbl = QLabel("→")
        arrow_lbl.setObjectName("arrowLabel")
        lang_row.addWidget(arrow_lbl)

        self._lang_to_combo = QComboBox()
        self._lang_to_combo.setObjectName("langCombo")
        self._lang_to_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in LANGUAGES:
            self._lang_to_combo.addItem(name, code)
        self._lang_to_combo.setCurrentIndex(1)
        self._lang_to_combo.currentIndexChanged.connect(self._load_entries)
        lang_row.addWidget(self._lang_to_combo, stretch=1)

        layout.addLayout(lang_row)

        # --- Separator ---
        sep = QWidget()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # --- Form thêm/sửa thuật ngữ ---
        form_label = QLabel("Thêm / Sửa thuật ngữ")
        form_label.setObjectName("sectionLabel")
        layout.addWidget(form_label)

        term_from_row = QHBoxLayout()
        term_from_row.setSpacing(10)
        term_from_lbl = QLabel(self._i18n.t("glossary.term_from"))
        term_from_lbl.setFixedWidth(100)
        self._term_from_input = QLineEdit()
        self._term_from_input.setObjectName("termInput")
        self._term_from_input.setPlaceholderText(self._i18n.t("glossary.term_from_hint"))
        term_from_row.addWidget(term_from_lbl)
        term_from_row.addWidget(self._term_from_input, stretch=1)
        layout.addLayout(term_from_row)

        term_to_row = QHBoxLayout()
        term_to_row.setSpacing(10)
        term_to_lbl = QLabel(self._i18n.t("glossary.term_to"))
        term_to_lbl.setFixedWidth(100)
        self._term_to_input = QLineEdit()
        self._term_to_input.setObjectName("termInput")
        self._term_to_input.setPlaceholderText(self._i18n.t("glossary.term_to_hint"))
        term_to_row.addWidget(term_to_lbl)
        term_to_row.addWidget(self._term_to_input, stretch=1)
        layout.addLayout(term_to_row)

        save_row = QHBoxLayout()
        save_row.addStretch()

        self._cancel_edit_btn = QPushButton("Hủy sửa")
        self._cancel_edit_btn.setObjectName("cancelEditBtn")
        self._cancel_edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_edit_btn.clicked.connect(self._on_cancel_edit)
        self._cancel_edit_btn.hide()
        save_row.addWidget(self._cancel_edit_btn)

        self._save_btn = QPushButton(self._i18n.t("glossary.btn_save"))
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setIcon(theme.icon("content-save-outline", color=theme.BG_BASE))
        self._save_btn.setIconSize(QSize(14, 14))
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self._save_btn)

        layout.addLayout(save_row)

        # --- Separator ---
        sep2 = QWidget()
        sep2.setObjectName("separator")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # --- Tìm kiếm ---
        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText(self._i18n.t("glossary.search"))
        self._search_input.textChanged.connect(self._load_entries)
        layout.addWidget(self._search_input)

        # --- Bảng thuật ngữ ---
        self._table = QTableWidget(0, 3)
        self._table.setObjectName("glossaryTable")
        self._table.setHorizontalHeaderLabels([
            self._i18n.t("glossary.term_from"),
            self._i18n.t("glossary.term_to"),
            "",
        ])

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_TERM_FROM, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_TERM_TO, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_ACTIONS, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(COL_ACTIONS, 72)

        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)

        layout.addWidget(self._table, stretch=1)

        # --- Nút dưới: Import / Export / Đóng ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._import_btn = QPushButton(self._i18n.t("glossary.btn_import"))
        self._import_btn.setObjectName("importBtn")
        self._import_btn.setIcon(theme.icon("upload-outline", color=theme.SUBTEXT_0))
        self._import_btn.setIconSize(QSize(14, 14))
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self._import_btn)

        self._export_btn = QPushButton(self._i18n.t("glossary.btn_export"))
        self._export_btn.setObjectName("exportBtn")
        self._export_btn.setIcon(theme.icon("download-outline", color=theme.SUBTEXT_0))
        self._export_btn.setIconSize(QSize(14, 14))
        self._export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_btn.clicked.connect(self._on_export)
        btn_row.addWidget(self._export_btn)

        btn_row.addStretch()

        self._close_btn = QPushButton(self._i18n.t("settings.btn_cancel"))
        self._close_btn.setObjectName("cancelBtn")
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)

        layout.addLayout(btn_row)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho dialog."""
        arrow_icon = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "dropdown_arrow.svg"
        arrow_url = arrow_icon.as_posix()
        self.setStyleSheet(f"""
            GlossaryDialog {{
                background-color: {theme.BG_CRUST};
            }}
            #panel {{
                background-color: #262640;
                border: 1px solid {theme.SURFACE_2};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #dialogTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_LG}px;
                font-weight: bold;
            }}
            #sectionLabel {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            #arrowLabel {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_MD}px;
            }}
            #separator {{
                background-color: {theme.SURFACE_0};
            }}
            QLabel {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
            }}
            #langCombo {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                padding: 5px 10px;
                font-size: {theme.FONT_MD}px;
            }}
            #langCombo::drop-down {{ border: none; width: 24px; }}
            #langCombo::down-arrow {{
                image: url({arrow_url});
                width: 10px; height: 6px; margin-right: 8px;
            }}
            #langCombo QAbstractItemView {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                selection-background-color: {theme.SURFACE_1};
                outline: none;
            }}
            #termInput, #searchInput {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                padding: 6px 10px;
                font-size: {theme.FONT_MD}px;
            }}
            #termInput:focus, #searchInput:focus {{
                border-color: {theme.BLUE};
            }}
            #glossaryTable {{
                background-color: {theme.BG_MANTLE};
                alternate-background-color: {theme.BG_BASE};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                gridline-color: transparent;
                font-size: {theme.FONT_MD}px;
            }}
            #glossaryTable::item {{
                padding: 4px 10px;
                border-bottom: 1px solid {theme.SURFACE_0};
            }}
            #glossaryTable::item:selected {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
            }}
            #glossaryTable QHeaderView::section {{
                background-color: {theme.SURFACE_0};
                color: {theme.SUBTEXT_0};
                border: none;
                padding: 6px 10px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
            }}
            #editBtn {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM}px;
                padding: 4px;
                min-width: 28px; max-width: 28px;
                min-height: 28px; max-height: 28px;
            }}
            #editBtn:hover {{ background-color: {theme.SURFACE_0}; }}
            #deleteBtn {{
                background-color: transparent;
                border: none;
                border-radius: {theme.RADIUS_SM}px;
                padding: 4px;
                min-width: 28px; max-width: 28px;
                min-height: 28px; max-height: 28px;
            }}
            #deleteBtn:hover {{ background-color: {theme.SURFACE_0}; }}
            {theme.btn_success_qss("saveBtn")}
            #cancelEditBtn {{
                background-color: transparent;
                color: {theme.SUBTEXT_0};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 16px;
                font-size: {theme.FONT_MD}px;
            }}
            #cancelEditBtn:hover {{ background-color: {theme.SURFACE_0}; color: {theme.TEXT}; }}
            #importBtn, #exportBtn {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 14px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
                text-align: left;
            }}
            #importBtn:hover, #exportBtn:hover {{
                background-color: {theme.SURFACE_1};
            }}
            #cancelBtn {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #cancelBtn:hover {{ background-color: {theme.SURFACE_2}; }}
        """)

    # --- Helpers ---

    def _current_lang_from(self) -> str:
        """Trả về mã ngôn ngữ nguồn đang chọn."""
        return self._lang_from_combo.currentData()

    def _current_lang_to(self) -> str:
        """Trả về mã ngôn ngữ đích đang chọn."""
        return self._lang_to_combo.currentData()

    def _add_table_row(self, entry_id: int, term_from: str, term_to: str) -> None:
        """Thêm một hàng vào bảng thuật ngữ.

        Args:
            entry_id: ID bản ghi trong database.
            term_from: Thuật ngữ gốc.
            term_to: Thuật ngữ đích.
        """
        # Tắm sorting khi chèn để tránh index lộn xộn
        self._table.setSortingEnabled(False)

        row = self._table.rowCount()
        self._table.insertRow(row)

        from_item = QTableWidgetItem(term_from)
        from_item.setData(Qt.ItemDataRole.UserRole, entry_id)
        self._table.setItem(row, COL_TERM_FROM, from_item)

        to_item = QTableWidgetItem(term_to)
        self._table.setItem(row, COL_TERM_TO, to_item)

        # Widget chứa 2 nút action
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(4, 0, 4, 0)
        action_layout.setSpacing(2)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        edit_btn = QPushButton()
        edit_btn.setObjectName("editBtn")
        edit_btn.setIcon(theme.icon("pencil-outline", color=theme.BLUE))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setToolTip(self._i18n.t("glossary.tooltip_edit"))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(
            lambda _, eid=entry_id, tf=term_from, tt=term_to: self._on_edit(eid, tf, tt)
        )
        action_layout.addWidget(edit_btn)

        del_btn = QPushButton()
        del_btn.setObjectName("deleteBtn")
        del_btn.setIcon(theme.icon("delete-outline", color=theme.RED))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setToolTip(self._i18n.t("glossary.tooltip_delete"))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda _, eid=entry_id: self._on_delete(eid))
        action_layout.addWidget(del_btn)

        self._table.setCellWidget(row, COL_ACTIONS, action_widget)
        self._table.setRowHeight(row, 40)

        self._table.setSortingEnabled(True)

    # --- Data ---

    def _load_entries(self) -> None:
        """Tải danh sách thuật ngữ theo cặp ngôn ngữ và bộ lọc tìm kiếm."""
        self._table.setRowCount(0)

        lang_from = self._current_lang_from()
        lang_to = self._current_lang_to()
        search = self._search_input.text().strip() if hasattr(self, "_search_input") else ""

        entries = self._glossary.search(lang_from, lang_to, search)
        for entry in entries:
            self._add_table_row(entry["id"], entry["term_from"], entry["term_to"])

    # --- Slots ---

    def _on_cancel_edit(self) -> None:
        """Hủy chế độ sửa, reset form về trạng thái thêm mới."""
        self._editing_id = None
        self._term_from_input.clear()
        self._term_to_input.clear()
        self._cancel_edit_btn.hide()
        self._save_btn.setText(self._i18n.t("glossary.btn_save"))

    def _on_save(self) -> None:
        """Lưu thuật ngữ mới hoặc cập nhật thuật ngữ đang sửa."""
        term_from = self._term_from_input.text().strip()
        term_to = self._term_to_input.text().strip()

        if not term_from or not term_to:
            MessageDialog.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.validation_empty"),
            )
            return

        lang_from = self._current_lang_from()
        lang_to = self._current_lang_to()

        if lang_from == lang_to:
            MessageDialog.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.validation_same_lang"),
            )
            return

        try:
            if self._editing_id is not None:
                self._glossary.update(
                    self._editing_id, lang_from, term_from, lang_to, term_to
                )
                self._editing_id = None
            else:
                self._glossary.add(lang_from, term_from, lang_to, term_to)
        except ValueError as e:
            MessageDialog.warning(self, self._i18n.t("glossary.title"), str(e))
            return

        self._term_from_input.clear()
        self._term_to_input.clear()
        self._cancel_edit_btn.hide()
        self._save_btn.setText(self._i18n.t("glossary.btn_save"))
        self._term_from_input.setFocus()
        self._load_entries()

    def _on_edit(self, entry_id: int, term_from: str, term_to: str) -> None:
        """Đưa thuật ngữ vào form để sửa.

        Args:
            entry_id: ID bản ghi.
            term_from: Thuật ngữ gốc.
            term_to: Thuật ngữ đích.
        """
        self._editing_id = entry_id
        self._term_from_input.setText(term_from)
        self._term_to_input.setText(term_to)
        self._cancel_edit_btn.show()
        self._save_btn.setText("Cập nhật")
        self._term_from_input.setFocus()

    def _on_delete(self, entry_id: int) -> None:
        """Xóa thuật ngữ sau khi xác nhận.

        Args:
            entry_id: ID bản ghi cần xóa.
        """
        if MessageDialog.question(
            self,
            self._i18n.t("glossary.title"),
            self._i18n.t("glossary.confirm_delete"),
        ):
            self._glossary.delete(entry_id)
            if self._editing_id == entry_id:
                self._on_cancel_edit()
            self._load_entries()

    def _on_import(self) -> None:
        """Import thuật ngữ từ file CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._i18n.t("glossary.btn_import"),
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            count = self._glossary.import_csv(file_path)
        except Exception as e:
            logger.error("Lỗi import CSV: %s", sanitize_error(e))
            MessageDialog.warning(
                self, self._i18n.t("glossary.title"), self._i18n.t("glossary.import_error")
            )
            return

        MessageDialog.information(
            self,
            self._i18n.t("glossary.title"),
            self._i18n.t("glossary.import_success").replace("{count}", str(count)),
        )
        self._load_entries()

    def _on_export(self) -> None:
        """Export toàn bộ thuật ngữ ra file CSV."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self._i18n.t("glossary.btn_export"),
            "glossary.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            count = self._glossary.export_csv(file_path)
        except Exception as e:
            logger.error("Lỗi export CSV: %s", sanitize_error(e))
            MessageDialog.warning(
                self, self._i18n.t("glossary.title"), self._i18n.t("glossary.export_error")
            )
            return

        MessageDialog.information(
            self,
            self._i18n.t("glossary.title"),
            self._i18n.t("glossary.export_success").replace("{count}", str(count)),
        )
