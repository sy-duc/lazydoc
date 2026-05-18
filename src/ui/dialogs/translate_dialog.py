"""TranslateDialog — Dialog dịch thuật tài liệu."""

import logging
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.ui import theme
from src.ui.dialogs.message_dialog import MessageDialog

logger = logging.getLogger(__name__)

# Ngôn ngữ đích hỗ trợ
TARGET_LANGUAGES = [
    ("vi", "Tiếng Việt"),
    ("en", "English"),
    ("ja", "日本語"),
]

# Lĩnh vực dịch thuật
DOMAINS = [
    "default",
    "it",
    "medical",
    "legal",
    "financial",
    "engineering",
]

# Văn phong dịch thuật
STYLES = [
    "default",
    "report",
    "concise",
    "literary",
]


class FlowLayout(QLayout):
    """Layout tự động xuống dòng khi không đủ chiều rộng."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 6) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            size = item.sizeHint()
            next_x = x + size.width() + self._spacing
            if next_x - self._spacing > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + self._spacing
                next_x = x + size.width() + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, size.width(), size.height()))
            x = next_x
            line_height = max(line_height, size.height())

        return y + line_height - rect.y() + m.bottom()


class TranslateDialog(QDialog):
    """Dialog dịch thuật — cho phép cấu hình và bắt đầu dịch file."""

    # Signal khi người dùng bấm Dịch
    translate_requested = Signal(dict)
    # Signal khi người dùng bấm Dừng
    stop_requested = Signal()

    def __init__(
        self,
        files: list[Path],
        parent: QWidget | None = None,
    ) -> None:
        """Khởi tạo TranslateDialog.

        Args:
            files: Danh sách file cần dịch.
            parent: Widget cha.
        """
        super().__init__(parent)
        self._i18n = I18nManager()
        self._files = files
        self._is_processing = False
        self._fun_timers: list[QTimer] = []
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    # Margin cho shadow effect
    _SHADOW_MARGIN = 20

    def _setup_window(self) -> None:
        """Cấu hình dialog."""
        self.setWindowTitle(self._i18n.t("translate.title"))
        m = self._SHADOW_MARGIN * 2
        self.setMinimumSize(500 + m, 520 + m)
        self.resize(500 + m, 560 + m)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)

    def _setup_ui(self) -> None:
        """Thiết lập layout và các widget."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(
            self._SHADOW_MARGIN, self._SHADOW_MARGIN,
            self._SHADOW_MARGIN, self._SHADOW_MARGIN,
        )

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
        layout.setSpacing(12)

        # Tiêu đề dialog
        title_label = QLabel(self._i18n.t("translate.title"))
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Danh sách file cần dịch
        file_list_label = QLabel(self._i18n.t("translate.file_list"))
        file_list_label.setObjectName("sectionLabel")
        layout.addWidget(file_list_label)

        file_scroll = QScrollArea()
        file_scroll.setObjectName("fileScroll")
        file_scroll.setWidgetResizable(True)
        file_scroll.setMaximumHeight(100)
        file_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        file_container = QWidget()
        file_container_layout = QVBoxLayout(file_container)
        file_container_layout.setContentsMargins(8, 4, 8, 4)
        file_container_layout.setSpacing(2)

        for file_path in self._files:
            file_label = QLabel(f"  {file_path.name}")
            file_label.setObjectName("fileItem")
            file_label.setToolTip(str(file_path))
            file_container_layout.addWidget(file_label)

        file_container_layout.addStretch()
        file_scroll.setWidget(file_container)
        layout.addWidget(file_scroll)

        # Separator
        sep1 = QWidget()
        sep1.setObjectName("separator")
        sep1.setFixedHeight(1)
        layout.addWidget(sep1)

        # Ngôn ngữ đích
        lang_section_lbl = QLabel(self._i18n.t("translate.target_language"))
        lang_section_lbl.setObjectName("sectionLabel")
        layout.addWidget(lang_section_lbl)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("langCombo")
        self._lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in TARGET_LANGUAGES:
            self._lang_combo.addItem(name, code)
        lang_row.addWidget(self._lang_combo, stretch=1)
        layout.addLayout(lang_row)

        # Separator
        sep2 = QWidget()
        sep2.setObjectName("separator")
        sep2.setFixedHeight(1)
        layout.addWidget(sep2)

        # Tùy chọn nâng cao
        adv_section_lbl = QLabel("Tùy chọn")
        adv_section_lbl.setObjectName("sectionLabel")
        layout.addWidget(adv_section_lbl)

        # Hàng nút: Bảng thuật ngữ + Mở rộng
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self._glossary_btn = QPushButton(
            f"  {self._i18n.t('translate.btn_glossary')}"
        )
        self._glossary_btn.setIcon(theme.icon("book-open-outline", color=theme.SUBTEXT_0))
        self._glossary_btn.setIconSize(QSize(14, 14))
        self._glossary_btn.setObjectName("glossaryBtn")
        self._glossary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._glossary_btn.clicked.connect(self._on_glossary)
        action_row.addWidget(self._glossary_btn)

        self._expand_btn = QPushButton(
            f"▼ {self._i18n.t('translate.btn_expand')}"
        )
        self._expand_btn.setObjectName("expandBtn")
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn.setCheckable(True)
        self._expand_btn.clicked.connect(self._toggle_expand)
        action_row.addWidget(self._expand_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

        # Vùng mở rộng (ẩn mặc định)
        self._expand_area = QWidget()
        self._expand_area.setObjectName("expandArea")
        self._expand_area.setVisible(False)
        expand_layout = QVBoxLayout(self._expand_area)
        expand_layout.setContentsMargins(0, 4, 0, 4)
        expand_layout.setSpacing(8)

        # Chế độ dịch (radio buttons)
        mode_lbl = QLabel(self._i18n.t("translate.mode"))
        mode_lbl.setObjectName("sectionLabel")
        expand_layout.addWidget(mode_lbl)

        self._mode_group = QButtonGroup(self)
        mode_container = QWidget()
        mode_flow = FlowLayout(mode_container, spacing=8)
        mode_options = [
            ("default", self._i18n.t("translate.mode_default")),
            ("smart", self._i18n.t("translate.mode_smart")),
        ]
        for i, (key, label) in enumerate(mode_options):
            radio = QRadioButton(label)
            radio.setObjectName("optionRadio")
            radio.setProperty("option_value", key)
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                radio.setChecked(True)
            self._mode_group.addButton(radio, i)
            mode_flow.addWidget(radio)
        expand_layout.addWidget(mode_container)

        # Lĩnh vực (radio buttons)
        domain_lbl = QLabel(self._i18n.t("translate.domain"))
        domain_lbl.setObjectName("sectionLabel")
        expand_layout.addWidget(domain_lbl)

        self._domain_group = QButtonGroup(self)
        domain_container = QWidget()
        domain_flow = FlowLayout(domain_container, spacing=8)
        for i, domain_key in enumerate(DOMAINS):
            radio = QRadioButton(self._i18n.t(f"translate.domain_{domain_key}"))
            radio.setObjectName("optionRadio")
            radio.setProperty("option_value", domain_key)
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                radio.setChecked(True)
            self._domain_group.addButton(radio, i)
            domain_flow.addWidget(radio)
        expand_layout.addWidget(domain_container)

        # Văn phong (radio buttons)
        style_lbl = QLabel(self._i18n.t("translate.style"))
        style_lbl.setObjectName("sectionLabel")
        expand_layout.addWidget(style_lbl)

        self._style_group = QButtonGroup(self)
        style_container = QWidget()
        style_flow = FlowLayout(style_container, spacing=8)
        for i, style_key in enumerate(STYLES):
            radio = QRadioButton(self._i18n.t(f"translate.style_{style_key}"))
            radio.setObjectName("optionRadio")
            radio.setProperty("option_value", style_key)
            radio.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                radio.setChecked(True)
            self._style_group.addButton(radio, i)
            style_flow.addWidget(radio)
        expand_layout.addWidget(style_container)

        layout.addWidget(self._expand_area)

        layout.addStretch()

        # Label trạng thái vui nhộn (thay thế progress bar)
        self._status_label = QLabel("Đang dịch...")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # Hàng nút dưới cùng: Dịch + Dừng + Hủy
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self._cancel_btn = QPushButton(self._i18n.t("settings.btn_cancel"))
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        self._stop_btn = QPushButton(
            f"  {self._i18n.t('translate.btn_stop')}"
        )
        self._stop_btn.setIcon(theme.icon("stop-circle-outline", color=theme.BG_BASE))
        self._stop_btn.setIconSize(QSize(14, 14))
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)

        self._translate_btn = QPushButton(
            f"  {self._i18n.t('translate.btn_translate')}"
        )
        self._translate_btn.setIcon(theme.icon("translate", color=theme.BG_BASE))
        self._translate_btn.setIconSize(QSize(14, 14))
        self._translate_btn.setObjectName("translateBtn")
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._translate_btn.clicked.connect(self._on_translate)
        btn_row.addWidget(self._translate_btn)

        layout.addLayout(btn_row)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho dialog."""
        arrow_icon = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "dropdown_arrow.svg"
        arrow_url = arrow_icon.as_posix()
        self.setStyleSheet(f"""
            TranslateDialog {{
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
            }}
            #separator {{
                background-color: {theme.SURFACE_0};
            }}
            #fileScroll {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_0};
                border-radius: {theme.RADIUS_SM}px;
            }}
            #fileScroll QWidget {{
                background-color: {theme.BG_MANTLE};
            }}
            #fileItem {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SM}px;
                padding: 2px 0;
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
                padding: 6px 10px;
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
            #optionRadio {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SM}px;
                spacing: 6px;
                padding: 4px 8px;
            }}
            #optionRadio::indicator {{
                width: 14px; height: 14px;
                border: 2px solid {theme.SURFACE_2};
                border-radius: 9px;
                background-color: transparent;
            }}
            #optionRadio::indicator:checked {{
                background-color: {theme.BLUE};
                border-color: {theme.BLUE};
            }}
            #optionRadio:disabled {{ color: {theme.MUTED}; }}
            #expandArea {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_0};
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px;
            }}
            #glossaryBtn, #expandBtn {{
                background-color: {theme.SURFACE_0};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 14px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
                text-align: left;
            }}
            #glossaryBtn:hover, #expandBtn:hover {{
                background-color: {theme.SURFACE_1};
            }}
            #expandBtn:checked {{
                background-color: {theme.SURFACE_1};
                border-color: {theme.SURFACE_2};
            }}
            #translateBtn {{
                background-color: {theme.BLUE};
                color: {theme.BG_BASE};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
                text-align: left;
            }}
            #translateBtn:hover {{ background-color: {theme.SAPPHIRE}; }}
            #translateBtn:pressed {{ background-color: {theme.TEAL}; }}
            #translateBtn:disabled {{
                background-color: {theme.SURFACE_1};
                color: {theme.MUTED};
            }}
            #stopBtn {{
                background-color: {theme.RED};
                color: {theme.BG_BASE};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
                text-align: left;
            }}
            #stopBtn:hover {{ background-color: {theme.MAROON}; }}
            #cancelBtn {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #cancelBtn:hover {{ background-color: {theme.SURFACE_2}; }}
            #statusLabel {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
                font-style: italic;
                padding: 4px 0;
            }}
        """)

    # --- Slots ---

    def _toggle_expand(self) -> None:
        """Hiển thị/ẩn vùng tùy chọn mở rộng."""
        expanded = self._expand_btn.isChecked()
        self._expand_area.setVisible(expanded)
        arrow = "▲" if expanded else "▼"
        self._expand_btn.setText(
            f"{arrow} {self._i18n.t('translate.btn_expand')}"
        )

        # Resize theo sizeHint thực tế của layout. Không hard-code chiều cao,
        # vì Windows/Qt có thể tính minimum geometry lớn hơn khi radio options wrap.
        if self.layout():
            self.layout().activate()
        target_height = max(self.minimumHeight(), self.sizeHint().height())
        self.setFixedHeight(target_height)

    def _on_glossary(self) -> None:
        """Mở dialog bảng thuật ngữ."""
        from src.ui.dialogs.glossary_dialog import GlossaryDialog

        overlay = QWidget(self)
        overlay.setObjectName("glossaryOverlay")
        overlay.setStyleSheet(
            "#glossaryOverlay { background-color: rgba(0, 0, 0, 120); }"
        )
        overlay.setGeometry(self.rect())
        overlay.show()
        overlay.raise_()

        dialog = GlossaryDialog(self)
        dialog.exec()

        overlay.deleteLater()
        logger.info("Đã đóng dialog bảng thuật ngữ.")

    def _on_translate(self) -> None:
        """Xử lý khi người dùng bấm nút Dịch."""
        config = {
            "files": self._files,
            "target_language": self._lang_combo.currentData(),
            "mode": self._mode_group.checkedButton().property("option_value"),
            "domain": self._domain_group.checkedButton().property("option_value"),
            "style": self._style_group.checkedButton().property("option_value"),
        }
        self._set_processing(True)
        self.translate_requested.emit(config)
        logger.info(
            "Yêu cầu dịch %d file sang %s (chế độ: %s).",
            len(self._files),
            config["target_language"],
            config["mode"],
        )

    def _on_stop(self) -> None:
        """Xử lý khi người dùng bấm nút Dừng."""
        self._set_processing(False)
        self.stop_requested.emit()
        logger.info("Người dùng yêu cầu dừng dịch.")

    def _set_processing(self, processing: bool) -> None:
        """Chuyển đổi trạng thái xử lý.

        Args:
            processing: True khi đang dịch, False khi dừng/hoàn tất.
        """
        self._is_processing = processing
        self._translate_btn.setEnabled(not processing)
        self._cancel_btn.setEnabled(not processing)
        self._glossary_btn.setEnabled(not processing)
        self._expand_btn.setEnabled(not processing)
        self._lang_combo.setEnabled(not processing)
        # Disable/enable radio buttons
        for group in (self._mode_group, self._domain_group, self._style_group):
            for btn in group.buttons():
                btn.setEnabled(not processing)
        self._stop_btn.setVisible(processing)
        self._status_label.setVisible(processing)

        if processing:
            self._status_label.setText("Đang dịch...")
            self._start_fun_timers()
        else:
            self._stop_fun_timers()

    def _start_fun_timers(self) -> None:
        """Bắt đầu chuỗi thông báo vui nhộn theo thời gian."""
        self._stop_fun_timers()
        messages = [
            (10_000, "Sắp xong, chờ chút nhé..."),
            (30_000, "File hơi lớn nên dịch hơi lâu, đợi chút nha!"),
            (60_000, "Cảm ơn bạn đã kiên nhẫn! Gần xong rồi..."),
            (120_000, "Vẫn đang cố gắng hết sức, bạn ơi..."),
        ]
        for delay_ms, msg in messages:
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(delay_ms)
            timer.timeout.connect(lambda m=msg: self._status_label.setText(m))
            self._fun_timers.append(timer)
            timer.start()

    def _stop_fun_timers(self) -> None:
        """Dừng tất cả timer thông báo."""
        for timer in self._fun_timers:
            timer.stop()
        self._fun_timers.clear()

    # --- Public API ---

    def update_status(self, msg: str) -> None:
        """Cập nhật thông báo trạng thái dịch.

        Args:
            msg: Thông báo trạng thái từ worker.
        """
        if self._is_processing:
            self._status_label.setText(msg)

    def on_translate_done(
        self,
        success_count: int = 0,
        fail_count: int = 0,
        output_dir: str = "",
    ) -> None:
        """Xử lý khi dịch hoàn tất.

        Args:
            success_count: Số file dịch thành công.
            fail_count: Số file dịch thất bại.
            output_dir: Đường dẫn thư mục chứa file output.
        """
        self._set_processing(False)

        if success_count > 0 and fail_count == 0:
            msg = f"Đã dịch thành công {success_count} file.\n\nFile lưu tại:\n{output_dir}"
            MessageDialog.information(self, "Dịch hoàn tất", msg)
        elif success_count > 0 and fail_count > 0:
            msg = f"Đã dịch thành công {success_count} file.\n{fail_count} file thất bại.\n\nFile lưu tại:\n{output_dir}"
            MessageDialog.warning(self, "Dịch hoàn tất", msg)
        elif fail_count > 0:
            MessageDialog.critical(self, "Dịch thất bại", f"Dịch thất bại {fail_count} file.")
