"""TranslateDialog — Dialog dịch thuật tài liệu."""

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager

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
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    # Margin cho shadow effect
    _SHADOW_MARGIN = 20

    def _setup_window(self) -> None:
        """Cấu hình dialog."""
        self.setWindowTitle(self._i18n.t("translate.title"))
        m = self._SHADOW_MARGIN * 2
        self.setFixedSize(500 + m, 520 + m)
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
            file_label = QLabel(f"📄 {file_path.name}")
            file_label.setObjectName("fileItem")
            file_label.setToolTip(str(file_path))
            file_container_layout.addWidget(file_label)

        file_container_layout.addStretch()
        file_scroll.setWidget(file_container)
        layout.addWidget(file_scroll)

        # Selectbox ngôn ngữ đích
        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)
        lang_lbl = QLabel(self._i18n.t("translate.target_language"))
        lang_lbl.setFixedWidth(100)
        self._lang_combo = QComboBox()
        self._lang_combo.setObjectName("langCombo")
        self._lang_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for code, name in TARGET_LANGUAGES:
            self._lang_combo.addItem(name, code)
        lang_row.addWidget(lang_lbl)
        lang_row.addWidget(self._lang_combo, stretch=1)
        layout.addLayout(lang_row)

        # Hàng nút: Bảng thuật ngữ + Mở rộng
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self._glossary_btn = QPushButton(
            f"📖 {self._i18n.t('translate.btn_glossary')}"
        )
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

        # Chế độ dịch
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        mode_lbl = QLabel(self._i18n.t("translate.mode"))
        mode_lbl.setFixedWidth(100)
        self._mode_combo = QComboBox()
        self._mode_combo.setObjectName("modeCombo")
        self._mode_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_combo.addItem(
            self._i18n.t("translate.mode_default"), "default"
        )
        self._mode_combo.addItem(
            self._i18n.t("translate.mode_smart"), "smart"
        )
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode_combo, stretch=1)
        expand_layout.addLayout(mode_row)

        # Domain
        domain_row = QHBoxLayout()
        domain_row.setSpacing(10)
        domain_lbl = QLabel(self._i18n.t("translate.domain"))
        domain_lbl.setFixedWidth(100)
        self._domain_combo = QComboBox()
        self._domain_combo.setObjectName("domainCombo")
        self._domain_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for domain_key in DOMAINS:
            self._domain_combo.addItem(
                self._i18n.t(f"translate.domain_{domain_key}"), domain_key
            )
        domain_row.addWidget(domain_lbl)
        domain_row.addWidget(self._domain_combo, stretch=1)
        expand_layout.addLayout(domain_row)

        # Văn phong
        style_row = QHBoxLayout()
        style_row.setSpacing(10)
        style_lbl = QLabel(self._i18n.t("translate.style"))
        style_lbl.setFixedWidth(100)
        self._style_combo = QComboBox()
        self._style_combo.setObjectName("styleCombo")
        self._style_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        for style_key in STYLES:
            self._style_combo.addItem(
                self._i18n.t(f"translate.style_{style_key}"), style_key
            )
        style_row.addWidget(style_lbl)
        style_row.addWidget(self._style_combo, stretch=1)
        expand_layout.addLayout(style_row)

        layout.addWidget(self._expand_area)

        layout.addStretch()

        # Thanh tiến độ
        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName("progressBar")
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # Chi phí realtime
        self._cost_row = QWidget()
        self._cost_row.setObjectName("costRow")
        self._cost_row.setVisible(False)
        cost_layout = QHBoxLayout(self._cost_row)
        cost_layout.setContentsMargins(0, 0, 0, 0)
        cost_layout.setSpacing(16)

        self._token_label = QLabel(
            f"{self._i18n.t('main.token_label')}: 0"
        )
        self._token_label.setObjectName("costInfo")
        cost_layout.addWidget(self._token_label)

        self._cost_label = QLabel(
            f"{self._i18n.t('main.cost_label')}: $0.0000"
        )
        self._cost_label.setObjectName("costInfo")
        cost_layout.addWidget(self._cost_label)

        cost_layout.addStretch()
        layout.addWidget(self._cost_row)

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
            f"⏹ {self._i18n.t('translate.btn_stop')}"
        )
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._on_stop)
        btn_row.addWidget(self._stop_btn)

        self._translate_btn = QPushButton(
            f"🌐 {self._i18n.t('translate.btn_translate')}"
        )
        self._translate_btn.setObjectName("translateBtn")
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._translate_btn.clicked.connect(self._on_translate)
        btn_row.addWidget(self._translate_btn)

        layout.addLayout(btn_row)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho dialog."""
        arrow_icon = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "dropdown_arrow.svg"
        arrow_url = arrow_icon.as_posix()
        self.setStyleSheet("""
            TranslateDialog {
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
            #sectionLabel {
                color: #a6adc8;
                font-size: 12px;
                font-weight: bold;
            }
            #fileScroll {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
            }
            #fileScroll QWidget {
                background-color: #181825;
            }
            #fileItem {
                color: #cdd6f4;
                font-size: 12px;
                padding: 2px 0;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            #langCombo, #modeCombo, #domainCombo, #styleCombo {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #langCombo::drop-down, #modeCombo::drop-down,
            #domainCombo::drop-down, #styleCombo::drop-down {
                border: none;
                width: 24px;
            }
            #langCombo::down-arrow, #modeCombo::down-arrow,
            #domainCombo::down-arrow, #styleCombo::down-arrow {
                image: url(__ARROW_URL__);
                width: 10px;
                height: 6px;
                margin-right: 8px;
            }
            #langCombo QAbstractItemView, #modeCombo QAbstractItemView,
            #domainCombo QAbstractItemView, #styleCombo QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                selection-background-color: #45475a;
                outline: none;
            }
            #expandArea {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
            }
            #glossaryBtn {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            #glossaryBtn:hover {
                background-color: #45475a;
            }
            #expandBtn {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            #expandBtn:hover {
                background-color: #45475a;
            }
            #expandBtn:checked {
                background-color: #45475a;
            }
            #translateBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #translateBtn:hover {
                background-color: #74c7ec;
            }
            #translateBtn:pressed {
                background-color: #94e2d5;
            }
            #translateBtn:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            #stopBtn {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #stopBtn:hover {
                background-color: #eba0ac;
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
            #progressBar {
                background-color: #313244;
                border: none;
                border-radius: 4px;
                height: 8px;
                text-align: center;
                font-size: 10px;
                color: #a6adc8;
            }
            #progressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
            #costInfo {
                color: #a6adc8;
                font-size: 11px;
            }
            QMessageBox {
                background-color: #e0e0e0;
            }
            QMessageBox QLabel {
                color: #1e1e2e;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                min-width: 60px;
            }
        """.replace("__ARROW_URL__", arrow_url))

    # --- Slots ---

    def _toggle_expand(self) -> None:
        """Hiển thị/ẩn vùng tùy chọn mở rộng."""
        expanded = self._expand_btn.isChecked()
        self._expand_area.setVisible(expanded)
        arrow = "▲" if expanded else "▼"
        self._expand_btn.setText(
            f"{arrow} {self._i18n.t('translate.btn_expand')}"
        )
        # Điều chỉnh kích thước dialog (cộng thêm shadow margin)
        m = self._SHADOW_MARGIN * 2
        if expanded:
            self.setFixedHeight(640 + m)
        else:
            self.setFixedHeight(520 + m)

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
            "mode": self._mode_combo.currentData(),
            "domain": self._domain_combo.currentData(),
            "style": self._style_combo.currentData(),
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
        self._stop_btn.setVisible(processing)
        self._progress_bar.setVisible(processing)
        self._cost_row.setVisible(processing)

        if not processing:
            self._progress_bar.setValue(0)

    # --- Public API ---

    def update_progress(self, percent: int) -> None:
        """Cập nhật thanh tiến độ.

        Args:
            percent: Phần trăm hoàn thành (0-100).
        """
        self._progress_bar.setValue(percent)

    def update_cost(self, tokens: int, cost: float) -> None:
        """Cập nhật chi phí realtime.

        Args:
            tokens: Số token đã sử dụng.
            cost: Chi phí tính bằng USD.
        """
        self._token_label.setText(
            f"{self._i18n.t('main.token_label')}: {tokens:,}"
        )
        self._cost_label.setText(
            f"{self._i18n.t('main.cost_label')}: ${cost:.4f}"
        )

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
        self._progress_bar.setValue(100)
        self._progress_bar.setVisible(True)

        if success_count > 0:
            msg = f"Đã dịch thành công {success_count} file."
            if fail_count > 0:
                msg += f"\n{fail_count} file thất bại."
            msg += f"\n\nFile lưu tại:\n{output_dir}"
            QMessageBox.information(self, "Dịch hoàn tất", msg)
