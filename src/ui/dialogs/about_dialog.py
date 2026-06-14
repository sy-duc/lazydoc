"""AboutDialog — Thông tin ứng dụng LazyDoc."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui import theme

APP_VERSION = "1.0.0"
RELEASE_DATE = "13/06/2026"

_FORMATS = "DOCX · XLSX · PPTX · TXT · MD · CSV · PNG · JPG · BMP · GIF"
RELEASE_SUMMARY = (
    "Đây là phiên bản đầu tiên của LazyDoc. Các cải tiến, sửa lỗi "
    "và tính năng mới trong những phiên bản tiếp theo sẽ được mô tả "
    "tại đây."
)


class AboutDialog(QDialog):
    """Dialog thông tin ứng dụng."""

    def __init__(
        self,
        parent: QWidget | None = None,
        active_provider: str = "",
    ) -> None:
        super().__init__(parent)
        self._active_provider = active_provider or "Chưa cấu hình"
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setMinimumWidth(460)
        self.resize(480, 560)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        panel = QWidget()
        panel.setObjectName("aboutPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 130))
        panel.setGraphicsEffect(shadow)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        name_row = QHBoxLayout()
        name_lbl = QLabel("LazyDoc")
        name_lbl.setObjectName("aboutAppName")
        name_row.addWidget(name_lbl)
        name_row.addStretch()
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("aboutVersion")
        name_row.addWidget(ver_lbl)
        layout.addLayout(name_row)

        desc = QLabel("Tổng hợp và dịch thuật tài liệu thông minh bằng AI")
        desc.setObjectName("aboutDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("aboutTabs")
        self._tabs.addTab(self._build_info_tab(), "Thông tin")
        self._tabs.addTab(self._build_whats_new_tab(), "Có gì mới")
        layout.addWidget(self._tabs, stretch=1)

        footer_row = QHBoxLayout()
        copy_lbl = QLabel("© 2026 LazyDoc")
        copy_lbl.setObjectName("aboutCopy")
        footer_row.addWidget(copy_lbl)
        footer_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("aboutOkBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        footer_row.addWidget(ok_btn)
        layout.addLayout(footer_row)

    def _build_info_tab(self) -> QScrollArea:
        scroll = self._make_scroll_area()
        content = QWidget()
        content.setObjectName("aboutTabContent")
        tab_layout = QVBoxLayout(content)
        tab_layout.setContentsMargins(4, 14, 8, 8)
        tab_layout.setSpacing(8)

        tab_layout.addWidget(self._section_title(
            "file-document-multiple-outline", theme.MAUVE, "Tổng hợp tài liệu"
        ))
        for text in (
            "Phân tích đa định dạng trong cùng một lần xử lý",
            "Trích xuất thông tin quan trọng, tóm tắt có cấu trúc",
            "Báo cáo chi tiết dạng HTML trực quan",
        ):
            tab_layout.addWidget(self._feature_row("check", theme.GREEN, text))

        tab_layout.addSpacing(8)
        tab_layout.addWidget(self._sep())
        tab_layout.addSpacing(8)
        tab_layout.addWidget(self._section_title(
            "translate", theme.BLUE, "Dịch thuật linh hoạt"
        ))
        for text in (
            "Tùy chọn offline (miễn phí) hoặc AI (có ngữ cảnh)",
            "Giữ nguyên định dạng file gốc, dịch xong dùng luôn",
            "Bảng thuật ngữ tùy chỉnh, hỗ trợ import/export dễ dàng chia sẻ",
        ):
            tab_layout.addWidget(self._feature_row("check", theme.GREEN, text))

        tab_layout.addSpacing(8)
        tab_layout.addWidget(self._sep())
        tab_layout.addSpacing(8)
        provider_row = QHBoxLayout()
        provider_icon = QLabel()
        provider_icon.setPixmap(theme.pixmap("lightning-bolt", theme.YELLOW, 14))
        provider_row.addWidget(provider_icon)
        provider_lbl = QLabel("AI đề xuất sử dụng:")
        provider_lbl.setObjectName("aboutMeta")
        provider_row.addWidget(provider_lbl)
        provider_val = QLabel(self._active_provider.capitalize())
        provider_val.setObjectName("aboutMetaVal")
        provider_row.addWidget(provider_val)
        provider_row.addStretch()
        tab_layout.addLayout(provider_row)

        fmt_lbl = QLabel(_FORMATS)
        fmt_lbl.setObjectName("aboutFormats")
        fmt_lbl.setWordWrap(True)
        tab_layout.addWidget(fmt_lbl)
        tab_layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _build_whats_new_tab(self) -> QScrollArea:
        scroll = self._make_scroll_area()
        content = QWidget()
        content.setObjectName("aboutTabContent")
        tab_layout = QVBoxLayout(content)
        tab_layout.setContentsMargins(4, 14, 8, 8)
        tab_layout.setSpacing(8)

        release_title = QLabel(f"Phiên bản v{APP_VERSION}")
        release_title.setObjectName("releaseTitle")
        tab_layout.addWidget(release_title)
        release_date = QLabel(f"Ngày phát hành: {RELEASE_DATE}")
        release_date.setObjectName("releaseDate")
        tab_layout.addWidget(release_date)
        tab_layout.addSpacing(8)

        release_summary = QLabel(RELEASE_SUMMARY)
        release_summary.setObjectName("releaseSummary")
        release_summary.setWordWrap(True)
        tab_layout.addWidget(release_summary)

        tab_layout.addStretch()
        scroll.setWidget(content)
        return scroll

    @staticmethod
    def _make_scroll_area() -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("aboutScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        return scroll

    def _sep(self) -> QWidget:
        w = QWidget()
        w.setObjectName("aboutSep")
        w.setFixedHeight(1)
        return w

    def _section_title(self, icon_name: str, color: str, text: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(theme.pixmap(icon_name, color, 16))
        row_layout.addWidget(icon_lbl)
        text_lbl = QLabel(text)
        text_lbl.setObjectName("aboutSectionTitle")
        row_layout.addWidget(text_lbl)
        row_layout.addStretch()
        return row

    def _feature_row(self, icon_name: str, color: str, text: str) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(4, 1, 0, 1)
        row_layout.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(theme.pixmap(icon_name, color, 13))
        row_layout.addWidget(icon_lbl)
        text_lbl = QLabel(text)
        text_lbl.setObjectName("aboutFeature")
        text_lbl.setWordWrap(True)
        row_layout.addWidget(text_lbl, stretch=1)
        return row

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            AboutDialog {{
                background-color: transparent;
            }}
            #aboutPanel {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #aboutAppName {{
                color: {theme.MAUVE};
                font-size: 22px;
                font-weight: bold;
            }}
            #aboutVersion {{
                color: {theme.SURFACE_2};
                font-size: {theme.FONT_SM}px;
                background-color: {theme.SURFACE_0};
                border-radius: {theme.RADIUS_SM}px;
                padding: 2px 8px;
            }}
            #aboutDesc {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
                margin-top: 4px;
            }}
            #aboutTabs {{
                background: transparent;
                border: none;
            }}
            #aboutTabs::pane {{
                border: none;
                border-top: 1px solid {theme.SURFACE_0};
                background: transparent;
            }}
            #aboutTabs QTabBar::tab {{
                background: transparent;
                color: {theme.SUBTEXT_0};
                padding: 8px 18px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            #aboutTabs QTabBar::tab:selected {{
                color: {theme.MAUVE};
                border-bottom-color: {theme.MAUVE};
                font-weight: bold;
            }}
            #aboutTabs QTabBar::tab:hover:!selected {{ color: {theme.TEXT}; }}
            #aboutScroll, #aboutTabContent {{
                background: transparent;
                border: none;
            }}
            #releaseTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #releaseDate {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
            }}
            #releaseSummary {{
                color: {theme.SUBTEXT_1};
                font-size: {theme.FONT_SM}px;
            }}
            #aboutSep {{
                background-color: {theme.SURFACE_0};
            }}
            #aboutSectionTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
            }}
            #aboutFeature {{
                color: {theme.SUBTEXT_1};
                font-size: {theme.FONT_SM}px;
            }}
            #aboutMeta {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
            }}
            #aboutMetaVal {{
                color: {theme.TEXT};
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
            }}
            #aboutFormats {{
                color: {theme.MUTED};
                font-size: 11px;
            }}
            #aboutCopy {{
                color: {theme.MUTED};
                font-size: 11px;
            }}
            #aboutOkBtn {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_2};
                border-radius: {theme.RADIUS_MD}px;
                padding: 6px 24px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
            }}
            #aboutOkBtn:hover {{ background-color: {theme.SURFACE_2}; }}
        """)
