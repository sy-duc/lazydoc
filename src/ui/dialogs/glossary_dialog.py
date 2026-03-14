"""GlossaryDialog — Dialog quản lý bảng thuật ngữ."""

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.database import DatabaseManager
from src.core.i18n import I18nManager

logger = logging.getLogger(__name__)

# Ngôn ngữ hỗ trợ
LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
    ("ja", "日本語"),
]


class GlossaryDialog(QDialog):
    """Dialog quản lý bảng thuật ngữ — thêm, sửa, xóa, import/export CSV."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo GlossaryDialog.

        Args:
            parent: Widget cha.
        """
        super().__init__(parent)
        self._i18n = I18nManager()
        self._db = DatabaseManager()
        self._editing_id: int | None = None
        self._setup_window()
        self._setup_ui()
        self._setup_style()
        self._load_entries()

    def _setup_window(self) -> None:
        """Cấu hình dialog."""
        self.setWindowTitle(self._i18n.t("glossary.title"))
        self.setFixedSize(560, 560)
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

        # Chọn ngôn ngữ nguồn
        lang_from_row = QHBoxLayout()
        lang_from_row.setSpacing(10)
        lang_from_lbl = QLabel(self._i18n.t("glossary.lang_from"))
        lang_from_lbl.setFixedWidth(110)
        self._lang_from_combo = QComboBox()
        self._lang_from_combo.setObjectName("langCombo")
        self._lang_from_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in LANGUAGES:
            self._lang_from_combo.addItem(name, code)
        self._lang_from_combo.currentIndexChanged.connect(self._load_entries)
        lang_from_row.addWidget(lang_from_lbl)
        lang_from_row.addWidget(self._lang_from_combo, stretch=1)
        layout.addLayout(lang_from_row)

        # Chọn ngôn ngữ đích
        lang_to_row = QHBoxLayout()
        lang_to_row.setSpacing(10)
        lang_to_lbl = QLabel(self._i18n.t("glossary.lang_to"))
        lang_to_lbl.setFixedWidth(110)
        self._lang_to_combo = QComboBox()
        self._lang_to_combo.setObjectName("langCombo")
        self._lang_to_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in LANGUAGES:
            self._lang_to_combo.addItem(name, code)
        # Mặc định chọn ngôn ngữ đích khác ngôn ngữ nguồn
        self._lang_to_combo.setCurrentIndex(1)
        self._lang_to_combo.currentIndexChanged.connect(self._load_entries)
        lang_to_row.addWidget(lang_to_lbl)
        lang_to_row.addWidget(self._lang_to_combo, stretch=1)
        layout.addLayout(lang_to_row)

        # Nhập thuật ngữ gốc
        term_from_row = QHBoxLayout()
        term_from_row.setSpacing(10)
        term_from_lbl = QLabel(self._i18n.t("glossary.term_from"))
        term_from_lbl.setFixedWidth(110)
        self._term_from_input = QLineEdit()
        self._term_from_input.setObjectName("termInput")
        self._term_from_input.setPlaceholderText(
            self._i18n.t("glossary.term_from_hint")
        )
        term_from_row.addWidget(term_from_lbl)
        term_from_row.addWidget(self._term_from_input, stretch=1)
        layout.addLayout(term_from_row)

        # Nhập thuật ngữ đích
        term_to_row = QHBoxLayout()
        term_to_row.setSpacing(10)
        term_to_lbl = QLabel(self._i18n.t("glossary.term_to"))
        term_to_lbl.setFixedWidth(110)
        self._term_to_input = QLineEdit()
        self._term_to_input.setObjectName("termInput")
        self._term_to_input.setPlaceholderText(
            self._i18n.t("glossary.term_to_hint")
        )
        term_to_row.addWidget(term_to_lbl)
        term_to_row.addWidget(self._term_to_input, stretch=1)
        layout.addLayout(term_to_row)

        # Nút Lưu
        save_row = QHBoxLayout()
        save_row.setSpacing(10)
        save_row.addStretch()

        self._save_btn = QPushButton(
            f"{self._i18n.t('glossary.btn_save')}"
        )
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        save_row.addWidget(self._save_btn)

        layout.addLayout(save_row)

        # Ô tìm kiếm
        self._search_input = QLineEdit()
        self._search_input.setObjectName("searchInput")
        self._search_input.setPlaceholderText(
            self._i18n.t("glossary.search")
        )
        self._search_input.textChanged.connect(self._load_entries)
        layout.addWidget(self._search_input)

        # Danh sách thuật ngữ
        self._scroll = QScrollArea()
        self._scroll.setObjectName("entryScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._entry_container = QWidget()
        self._entry_layout = QVBoxLayout(self._entry_container)
        self._entry_layout.setContentsMargins(4, 4, 4, 4)
        self._entry_layout.setSpacing(4)
        self._entry_layout.addStretch()
        self._scroll.setWidget(self._entry_container)
        layout.addWidget(self._scroll, stretch=1)

        # Hàng nút dưới: Import CSV + Export CSV + Đóng
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._import_btn = QPushButton(
            f"{self._i18n.t('glossary.btn_import')}"
        )
        self._import_btn.setObjectName("importBtn")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(self._import_btn)

        self._export_btn = QPushButton(
            f"{self._i18n.t('glossary.btn_export')}"
        )
        self._export_btn.setObjectName("exportBtn")
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
        self.setStyleSheet("""
            GlossaryDialog {
                background-color: #11111b;
            }
            #panel {
                background-color: #262640;
                border: 1px solid #585b70;
                border-radius: 10px;
            }
            #dialogTitle {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            #langCombo {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #langCombo::drop-down {
                border: none;
                width: 24px;
            }
            #langCombo::down-arrow {
                image: url(__ARROW_URL__);
                width: 10px;
                height: 6px;
                margin-right: 8px;
            }
            #langCombo QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                selection-background-color: #45475a;
                outline: none;
            }
            #termInput, #searchInput {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #termInput:focus, #searchInput:focus {
                border: 1px solid #89b4fa;
            }
            #entryScroll {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
            }
            #entryRow {
                background-color: transparent;
            }
            #entryText {
                color: #cdd6f4;
                font-size: 12px;
            }
            #editBtn {
                background-color: transparent;
                color: #89b4fa;
                border: none;
                font-size: 14px;
                padding: 2px 6px;
            }
            #editBtn:hover {
                color: #74c7ec;
            }
            #deleteBtn {
                background-color: transparent;
                color: #f38ba8;
                border: none;
                font-size: 14px;
                padding: 2px 6px;
            }
            #deleteBtn:hover {
                color: #eba0ac;
            }
            #saveBtn {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #saveBtn:hover {
                background-color: #94e2d5;
            }
            #saveBtn:pressed {
                background-color: #74c7ec;
            }
            #importBtn, #exportBtn {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            #importBtn:hover, #exportBtn:hover {
                background-color: #45475a;
            }
            #cancelBtn {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #cancelBtn:hover {
                background-color: #585b70;
            }
        """.replace("__ARROW_URL__", arrow_url))

    # --- Helpers ---

    def _current_lang_from(self) -> str:
        """Trả về mã ngôn ngữ nguồn đang chọn."""
        return self._lang_from_combo.currentData()

    def _current_lang_to(self) -> str:
        """Trả về mã ngôn ngữ đích đang chọn."""
        return self._lang_to_combo.currentData()

    def _clear_entries(self) -> None:
        """Xóa toàn bộ entry trong danh sách hiển thị."""
        while self._entry_layout.count() > 1:
            item = self._entry_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _add_entry_row(self, entry_id: int, term_from: str, term_to: str) -> None:
        """Thêm một hàng thuật ngữ vào danh sách.

        Args:
            entry_id: ID bản ghi trong database.
            term_from: Thuật ngữ gốc.
            term_to: Thuật ngữ đích.
        """
        row = QWidget()
        row.setObjectName("entryRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(8)

        text_label = QLabel(f"{term_from}  →  {term_to}")
        text_label.setObjectName("entryText")
        row_layout.addWidget(text_label, stretch=1)

        edit_btn = QPushButton("✏")
        edit_btn.setObjectName("editBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip(self._i18n.t("glossary.tooltip_edit"))
        edit_btn.clicked.connect(
            lambda _, eid=entry_id, tf=term_from, tt=term_to: self._on_edit(
                eid, tf, tt
            )
        )
        row_layout.addWidget(edit_btn)

        del_btn = QPushButton("✕")
        del_btn.setObjectName("deleteBtn")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setToolTip(self._i18n.t("glossary.tooltip_delete"))
        del_btn.clicked.connect(
            lambda _, eid=entry_id: self._on_delete(eid)
        )
        row_layout.addWidget(del_btn)

        # Chèn trước stretch
        self._entry_layout.insertWidget(
            self._entry_layout.count() - 1, row
        )

    # --- Data ---

    def _load_entries(self) -> None:
        """Tải danh sách thuật ngữ theo cặp ngôn ngữ và bộ lọc tìm kiếm."""
        self._clear_entries()

        lang_from = self._current_lang_from()
        lang_to = self._current_lang_to()
        search = self._search_input.text().strip() if hasattr(self, "_search_input") else ""

        conn = self._db.connection
        if search:
            pattern = f"%{search}%"
            cursor = conn.execute(
                """SELECT id, term_from, term_to FROM glossary
                   WHERE lang_from = ? AND lang_to = ?
                     AND (term_from LIKE ? OR term_to LIKE ?)
                   ORDER BY term_from COLLATE NOCASE""",
                (lang_from, lang_to, pattern, pattern),
            )
        else:
            cursor = conn.execute(
                """SELECT id, term_from, term_to FROM glossary
                   WHERE lang_from = ? AND lang_to = ?
                   ORDER BY term_from COLLATE NOCASE""",
                (lang_from, lang_to),
            )

        for row in cursor.fetchall():
            self._add_entry_row(row["id"], row["term_from"], row["term_to"])

    # --- Slots ---

    def _on_save(self) -> None:
        """Lưu thuật ngữ mới hoặc cập nhật thuật ngữ đang sửa."""
        term_from = self._term_from_input.text().strip()
        term_to = self._term_to_input.text().strip()

        if not term_from or not term_to:
            QMessageBox.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.validation_empty"),
            )
            return

        lang_from = self._current_lang_from()
        lang_to = self._current_lang_to()

        if lang_from == lang_to:
            QMessageBox.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.validation_same_lang"),
            )
            return

        now = datetime.now(timezone.utc).isoformat()
        conn = self._db.connection

        if self._editing_id is not None:
            # Cập nhật bản ghi đang sửa
            conn.execute(
                """UPDATE glossary
                   SET term_from = ?, term_to = ?, lang_from = ?, lang_to = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (term_from, term_to, lang_from, lang_to, now, self._editing_id),
            )
            conn.commit()
            self._editing_id = None
            logger.info("Đã cập nhật thuật ngữ: %s → %s", term_from, term_to)
        else:
            # Thêm mới hoặc cập nhật nếu trùng
            try:
                conn.execute(
                    """INSERT INTO glossary
                       (lang_from, term_from, lang_to, term_to, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (lang_from, term_from, lang_to, term_to, now, now),
                )
                conn.commit()
                logger.info("Đã thêm thuật ngữ: %s → %s", term_from, term_to)
            except Exception:
                # UNIQUE constraint — cập nhật bản ghi cũ
                conn.execute(
                    """UPDATE glossary
                       SET term_to = ?, updated_at = ?
                       WHERE lang_from = ? AND term_from = ? AND lang_to = ?""",
                    (term_to, now, lang_from, term_from, lang_to),
                )
                conn.commit()
                logger.info(
                    "Đã cập nhật thuật ngữ trùng: %s → %s", term_from, term_to
                )

        # Reset form
        self._term_from_input.clear()
        self._term_to_input.clear()
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
        self._term_from_input.setFocus()

    def _on_delete(self, entry_id: int) -> None:
        """Xóa thuật ngữ sau khi xác nhận.

        Args:
            entry_id: ID bản ghi cần xóa.
        """
        reply = QMessageBox.question(
            self,
            self._i18n.t("glossary.title"),
            self._i18n.t("glossary.confirm_delete"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            conn = self._db.connection
            conn.execute("DELETE FROM glossary WHERE id = ?", (entry_id,))
            conn.commit()
            logger.info("Đã xóa thuật ngữ id=%d.", entry_id)
            # Nếu đang sửa entry này thì reset form
            if self._editing_id == entry_id:
                self._editing_id = None
                self._term_from_input.clear()
                self._term_to_input.clear()
            self._load_entries()

    def _on_import(self) -> None:
        """Import thuật ngữ từ file CSV.

        Format CSV: lang_from, term_from, lang_to, term_to
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self._i18n.t("glossary.btn_import"),
            "",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        count = 0
        now = datetime.now(timezone.utc).isoformat()
        conn = self._db.connection

        try:
            with open(file_path, encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 4:
                        continue
                    lang_from, term_from, lang_to, term_to = (
                        row[0].strip(),
                        row[1].strip(),
                        row[2].strip(),
                        row[3].strip(),
                    )
                    if not all([lang_from, term_from, lang_to, term_to]):
                        continue
                    conn.execute(
                        """INSERT OR REPLACE INTO glossary
                           (lang_from, term_from, lang_to, term_to, created_at, updated_at)
                           VALUES (?, ?, ?, ?,
                                   COALESCE(
                                       (SELECT created_at FROM glossary
                                        WHERE lang_from=? AND term_from=? AND lang_to=?),
                                       ?),
                                   ?)""",
                        (
                            lang_from, term_from, lang_to, term_to,
                            lang_from, term_from, lang_to, now, now,
                        ),
                    )
                    count += 1
            conn.commit()
        except Exception as e:
            logger.error("Lỗi import CSV: %s", e)
            QMessageBox.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.import_error"),
            )
            return

        logger.info("Import thành công %d thuật ngữ từ %s.", count, file_path)
        QMessageBox.information(
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

        conn = self._db.connection
        cursor = conn.execute(
            """SELECT lang_from, term_from, lang_to, term_to
               FROM glossary ORDER BY lang_from, lang_to, term_from"""
        )

        count = 0
        try:
            with open(file_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                for row in cursor.fetchall():
                    writer.writerow([
                        row["lang_from"],
                        row["term_from"],
                        row["lang_to"],
                        row["term_to"],
                    ])
                    count += 1
        except Exception as e:
            logger.error("Lỗi export CSV: %s", e)
            QMessageBox.warning(
                self,
                self._i18n.t("glossary.title"),
                self._i18n.t("glossary.export_error"),
            )
            return

        logger.info("Export thành công %d thuật ngữ ra %s.", count, file_path)
        QMessageBox.information(
            self,
            self._i18n.t("glossary.title"),
            self._i18n.t("glossary.export_success").replace("{count}", str(count)),
        )
