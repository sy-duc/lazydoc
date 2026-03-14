"""Toolbar — Thanh công cụ chính của ứng dụng."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.core.i18n import I18nManager


class Toolbar(QWidget):
    """Thanh công cụ: Xay, Dịch, Setting, Hướng dẫn, Thông tin."""

    grind_clicked = Signal()
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

        # Nút Xay (primary action)
        self._grind_btn = QPushButton(f"⚡ {self._i18n.t('main.btn_grind')}")
        self._grind_btn.setObjectName("grindBtn")
        self._grind_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._grind_btn.clicked.connect(self.grind_clicked.emit)
        layout.addWidget(self._grind_btn)

        # Nút Dịch
        self._translate_btn = QPushButton(f"🌐 {self._i18n.t('main.btn_translate')}")
        self._translate_btn.setObjectName("translateBtn")
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._translate_btn.clicked.connect(self.translate_clicked.emit)
        layout.addWidget(self._translate_btn)

        layout.addStretch()

        # Nút Setting (icon)
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.setToolTip(self._i18n.t("main.btn_settings"))
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_btn)

        # Nút Hướng dẫn
        self._guide_btn = QPushButton(f"📖 {self._i18n.t('main.btn_guide')}")
        self._guide_btn.setObjectName("guideBtn")
        self._guide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._guide_btn.clicked.connect(self.guide_clicked.emit)
        layout.addWidget(self._guide_btn)

        # Nút Thông tin
        self._about_btn = QPushButton(f"ℹ {self._i18n.t('main.btn_about')}")
        self._about_btn.setObjectName("aboutBtn")
        self._about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._about_btn.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self._about_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho thanh công cụ."""
        self.setStyleSheet("""
            #toolbar {
                background-color: transparent;
            }
            #grindBtn {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            #grindBtn:hover {
                background-color: #94e2d5;
            }
            #grindBtn:pressed {
                background-color: #74c7ec;
            }
            #translateBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            #translateBtn:hover {
                background-color: #74c7ec;
            }
            #settingsBtn {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 18px;
                font-size: 18px;
            }
            #settingsBtn:hover {
                background-color: #585b70;
            }
            #guideBtn, #aboutBtn {
                background-color: #313244;
                color: #a6adc8;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
            }
            #guideBtn:hover, #aboutBtn:hover {
                background-color: #45475a;
                color: #cdd6f4;
            }
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt nút khi đang xử lý.

        Args:
            processing: True để disable các nút khi đang xử lý.
        """
        self._grind_btn.setEnabled(not processing)
        self._translate_btn.setEnabled(not processing)
