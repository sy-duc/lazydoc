"""Toolbar — Thanh công cụ chính của ứng dụng."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.core.i18n import I18nManager
from src.ui.components import IconButton, PrimaryButton, SecondaryButton
from src.ui.design import IconName


class Toolbar(QWidget):
    """Thanh công cụ: Tổng hợp, Dịch, Setting, Hướng dẫn, Thông tin."""

    summary_clicked = Signal()
    translate_clicked = Signal()
    settings_clicked = Signal()
    guide_clicked = Signal()
    about_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo Toolbar."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self.setObjectName("toolbar")
        self.setFixedHeight(50)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout thanh công cụ."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        self._summary_btn = PrimaryButton(
            self._i18n.t("main.btn_summary"),
            IconName.SUMMARY,
        )
        self._summary_btn.clicked.connect(self.summary_clicked.emit)
        layout.addWidget(self._summary_btn)

        self._translate_btn = SecondaryButton(
            self._i18n.t("main.btn_translate"),
            IconName.LANGUAGE,
        )
        self._translate_btn.clicked.connect(self.translate_clicked.emit)
        layout.addWidget(self._translate_btn)

        layout.addStretch()

        self._settings_btn = IconButton(
            IconName.SETTINGS,
            self._i18n.t("main.btn_settings"),
        )
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_btn)

        self._guide_btn = IconButton(
            IconName.GUIDE,
            self._i18n.t("main.btn_guide"),
        )
        self._guide_btn.clicked.connect(self.guide_clicked.emit)
        layout.addWidget(self._guide_btn)

        self._about_btn = IconButton(
            IconName.ABOUT,
            self._i18n.t("main.btn_about"),
        )
        self._about_btn.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self._about_btn)

    def _setup_style(self) -> None:
        """Áp dụng style cục bộ tối thiểu cho container."""
        self.setStyleSheet("""
            #toolbar {
                background-color: transparent;
            }
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt nút khi đang xử lý.

        Args:
            processing: True để disable các nút khi đang xử lý.
        """
        self._summary_btn.setEnabled(not processing)
        self._translate_btn.setEnabled(not processing)
