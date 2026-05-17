"""Toolbar — Thanh công cụ chính của ứng dụng."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.core.i18n import I18nManager
from src.ui import theme


class Toolbar(QWidget):
    """Thanh công cụ: Tổng hợp, Dịch, Settings, Hướng dẫn, Thông tin."""

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
        self.setFixedHeight(52)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout thanh công cụ."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(8)

        # --- Nút Tổng hợp (primary CTA) ---
        self._summary_btn = QPushButton(f"  {self._i18n.t('main.btn_summary')}")
        self._summary_btn.setObjectName("summaryBtn")
        self._summary_btn.setIcon(theme.icon("file-document-outline", color=theme.BG_BASE))
        self._summary_btn.setIconSize(QSize(16, 16))
        self._summary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._summary_btn.clicked.connect(self.summary_clicked.emit)
        layout.addWidget(self._summary_btn)

        # --- Nút Dịch (secondary) ---
        self._translate_btn = QPushButton(f"  {self._i18n.t('main.btn_translate')}")
        self._translate_btn.setObjectName("translateBtn")
        self._translate_btn.setIcon(theme.icon("translate", color=theme.BLUE))
        self._translate_btn.setIconSize(QSize(16, 16))
        self._translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._translate_btn.clicked.connect(self.translate_clicked.emit)
        layout.addWidget(self._translate_btn)

        layout.addStretch()

        # --- Separator mỏng ---
        sep = QWidget()
        sep.setObjectName("toolbarSep")
        sep.setFixedSize(1, 24)
        layout.addWidget(sep)

        layout.addSpacing(4)

        # --- Nút Settings (icon-only) ---
        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("settingsBtn")
        self._settings_btn.setIcon(theme.icon("cog-outline", color=theme.SUBTEXT_0))
        self._settings_btn.setIconSize(QSize(18, 18))
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.setToolTip(self._i18n.t("main.btn_settings"))
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_btn)

        # --- Nút Hướng dẫn (icon-only) ---
        self._guide_btn = QPushButton()
        self._guide_btn.setObjectName("guideBtn")
        self._guide_btn.setIcon(theme.icon("help-circle-outline", color=theme.SUBTEXT_0))
        self._guide_btn.setIconSize(QSize(18, 18))
        self._guide_btn.setFixedSize(36, 36)
        self._guide_btn.setToolTip(self._i18n.t("main.btn_guide"))
        self._guide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._guide_btn.clicked.connect(self.guide_clicked.emit)
        layout.addWidget(self._guide_btn)

        # --- Nút Thông tin (icon-only) ---
        self._about_btn = QPushButton()
        self._about_btn.setObjectName("aboutBtn")
        self._about_btn.setIcon(theme.icon("information-outline", color=theme.SUBTEXT_0))
        self._about_btn.setIconSize(QSize(18, 18))
        self._about_btn.setFixedSize(36, 36)
        self._about_btn.setToolTip(self._i18n.t("main.btn_about"))
        self._about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._about_btn.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self._about_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho thanh công cụ."""
        self.setStyleSheet(f"""
            #toolbar {{
                background-color: transparent;
            }}
            #toolbarSep {{
                background-color: {theme.SURFACE_1};
            }}
            #summaryBtn {{
                background-color: {theme.MAUVE};
                color: {theme.BG_BASE};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 20px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
                text-align: left;
            }}
            #summaryBtn:hover {{ background-color: {theme.LAVENDER}; }}
            #summaryBtn:pressed {{ background-color: {theme.BLUE}; }}
            #summaryBtn:disabled {{
                background-color: {theme.SURFACE_0};
                color: {theme.MUTED};
            }}
            #translateBtn {{
                background-color: {theme.SURFACE_1};
                color: {theme.BLUE};
                border: 1px solid {theme.SURFACE_2};
                border-radius: {theme.RADIUS_MD}px;
                padding: 7px 20px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
                text-align: left;
            }}
            #translateBtn:hover {{
                background-color: {theme.SURFACE_2};
                color: {theme.SAPPHIRE};
            }}
            #translateBtn:pressed {{ background-color: {theme.SURFACE_0}; }}
            #translateBtn:disabled {{ color: {theme.MUTED}; border-color: {theme.SURFACE_1}; }}
            {theme.btn_icon_qss("settingsBtn", "guideBtn", "aboutBtn")}
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt nút khi đang xử lý.

        Args:
            processing: True để disable các nút khi đang xử lý.
        """
        self._summary_btn.setEnabled(not processing)
        self._translate_btn.setEnabled(not processing)
