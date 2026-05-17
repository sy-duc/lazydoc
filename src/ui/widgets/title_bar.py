"""TitleBar — Thanh tiêu đề tùy chỉnh."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from src.core.i18n import I18nManager
from src.ui.components import IconButton
from src.ui.design import COLORS, IconName, RADIUS, TYPOGRAPHY


class TitleBar(QWidget):
    """Thanh tiêu đề tùy chỉnh — hiển thị tên app và nút đóng."""

    close_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo TitleBar."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self.setFixedHeight(40)
        self.setObjectName("titleBar")
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout thanh tiêu đề."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(0)

        self._title_label = QLabel(self._i18n.t("app.title"))
        self._title_label.setObjectName("titleLabel")
        layout.addWidget(self._title_label)

        layout.addStretch()

        self._close_btn = IconButton(
            IconName.CLOSE,
            self._i18n.t("main.btn_close"),
            size=32,
        )
        self._close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self._close_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho thanh tiêu đề."""
        title_type = TYPOGRAPHY["section"]
        self.setStyleSheet(f"""
            #titleBar {{
                background-color: {COLORS["surface_subtle"]};
                border-top-left-radius: {RADIUS["xl"]}px;
                border-top-right-radius: {RADIUS["xl"]}px;
            }}
            #titleLabel {{
                color: {COLORS["text"]};
                font-family: '{title_type.family}';
                font-size: {title_type.size}px;
                font-weight: {title_type.weight};
                background-color: transparent;
            }}
        """)
