"""CostTracker — Vùng chứa nút Stop và label trạng thái khi đang xử lý."""

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.i18n import I18nManager
from src.ui import theme


class CostTracker(QWidget):
    """Vùng hiển thị nút Stop khi đang xử lý."""

    stop_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo CostTracker."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self.setObjectName("costTracker")
        self.setFixedHeight(40)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)

        # Label trạng thái (ẩn khi idle)
        self._status_label = QLabel("Đang xử lý...")
        self._status_label.setObjectName("processingLabel")
        self._status_label.hide()
        layout.addWidget(self._status_label)

        layout.addStretch()

        # Nút Stop (icon + text)
        self._stop_btn = QPushButton(f"  {self._i18n.t('main.btn_stop')}")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setIcon(theme.icon("stop-circle-outline", color=theme.BG_BASE))
        self._stop_btn.setIconSize(QSize(14, 14))
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self._stop_btn.hide()
        layout.addWidget(self._stop_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet."""
        self.setStyleSheet(f"""
            #costTracker {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_0};
                border-radius: {theme.RADIUS_SM}px;
            }}
            #processingLabel {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
                font-style: italic;
                background: transparent;
            }}
            {theme.btn_danger_qss("stopBtn")}
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt trạng thái đang xử lý (hiện/ẩn nút Stop và label).

        Args:
            processing: True nếu đang xử lý.
        """
        self._stop_btn.setVisible(processing)
        self._status_label.setVisible(processing)

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._stop_btn.hide()
        self._status_label.hide()
