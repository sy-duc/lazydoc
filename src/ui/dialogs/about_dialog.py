"""AboutDialog — Thông tin ứng dụng LazyDoc."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui import theme

APP_VERSION = "1.0.0"

_FORMATS = "DOCX · XLSX · PPTX · TXT · MD · CSV · PNG · JPG · BMP · GIF"


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
        layout.setSpacing(0)

        # --- App name + version ---
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
        layout.addSpacing(20)

        # --- Separator ---
        layout.addWidget(self._sep())

        # --- Tính năng: Tổng hợp ---
        layout.addSpacing(16)
        layout.addWidget(self._section_title(
            "file-document-multiple-outline", theme.MAUVE, "Tổng hợp thông minh"
        ))
        layout.addSpacing(8)
        features_summary = [
            ("check", "Phân tích đa định dạng trong cùng một lần xử lý"),
            ("check", "Trích xuất thông tin quan trọng, tóm tắt có cấu trúc"),
            ("check", "Báo cáo chi tiết dạng HTML có thể tải về"),
            ("check", "Hỏi đáp (Q&A) ngay trên nội dung vừa tổng hợp"),
        ]
        for icon_name, text in features_summary:
            layout.addWidget(self._feature_row(icon_name, theme.GREEN, text))
        layout.addSpacing(16)

        # --- Separator ---
        layout.addWidget(self._sep())

        # --- Tính năng: Dịch thuật ---
        layout.addSpacing(16)
        layout.addWidget(self._section_title(
            "translate", theme.BLUE, "Dịch thuật linh hoạt"
        ))
        layout.addSpacing(8)
        features_translate = [
            ("check", "Offline (miễn phí) hoặc AI (chất lượng cao) — tuỳ chọn"),
            ("check", "Giữ nguyên định dạng file gốc sau khi dịch"),
            ("check", "Tự động dùng ngữ cảnh từ kết quả tổng hợp"),
            ("check", "Bảng thuật ngữ tùy chỉnh, import/export CSV"),
        ]
        for icon_name, text in features_translate:
            layout.addWidget(self._feature_row(icon_name, theme.GREEN, text))
        layout.addSpacing(20)

        # --- Separator ---
        layout.addWidget(self._sep())
        layout.addSpacing(14)

        # --- Provider + formats ---
        provider_row = QHBoxLayout()
        provider_row.setSpacing(8)
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
        layout.addLayout(provider_row)

        layout.addSpacing(6)
        formats_row = QHBoxLayout()
        formats_row.setSpacing(8)
        fmt_icon = QLabel()
        fmt_icon.setPixmap(theme.pixmap("file-multiple-outline", theme.SUBTEXT_0, 14))
        formats_row.addWidget(fmt_icon)
        fmt_lbl = QLabel(_FORMATS)
        fmt_lbl.setObjectName("aboutFormats")
        fmt_lbl.setWordWrap(True)
        formats_row.addWidget(fmt_lbl, stretch=1)
        layout.addLayout(formats_row)

        layout.addStretch()
        layout.addSpacing(14)

        # --- Footer ---
        footer_row = QHBoxLayout()
        copy_lbl = QLabel("© 2025 LazyDoc")
        copy_lbl.setObjectName("aboutCopy")
        footer_row.addWidget(copy_lbl)
        footer_row.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("aboutOkBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        footer_row.addWidget(ok_btn)
        layout.addLayout(footer_row)

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
                background-color: {theme.BG_CRUST};
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
