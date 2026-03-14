"""TitleBar — Thanh tiêu đề tùy chỉnh (chỉ có nút đóng)."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.i18n import I18nManager


class TitleBar(QWidget):
    """Thanh tiêu đề tùy chỉnh — chỉ hiển thị tên app và nút đóng."""

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

        # Tên ứng dụng
        self._title_label = QLabel(self._i18n.t("app.title"))
        self._title_label.setObjectName("titleLabel")
        layout.addWidget(self._title_label)

        layout.addStretch()

        # Nút đóng
        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("closeBtn")
        self._close_btn.setFixedSize(32, 32)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self._close_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho thanh tiêu đề."""
        self.setStyleSheet("""
            #titleBar {
                background-color: #181825;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            #titleLabel {
                color: #cdd6f4;
                font-size: 14px;
                font-weight: bold;
            }
            #closeBtn {
                background-color: transparent;
                color: #a6adc8;
                border: none;
                border-radius: 16px;
                font-size: 16px;
                font-weight: bold;
            }
            #closeBtn:hover {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
        """)
