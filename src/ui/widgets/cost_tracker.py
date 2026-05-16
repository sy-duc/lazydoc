"""CostTracker — Vùng chứa nút Stop khi đang xử lý."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from src.core.i18n import I18nManager


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
        layout.setSpacing(16)

        layout.addStretch()

        # Nút Stop
        self._stop_btn = QPushButton(self._i18n.t("main.btn_stop"))
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self._stop_btn.hide()
        layout.addWidget(self._stop_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet."""
        self.setStyleSheet("""
            #costTracker {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 6px;
            }
            #stopBtn {
                background-color: #f38ba8;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            #stopBtn:hover {
                background-color: #eba0ac;
            }
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt trạng thái đang xử lý (hiện/ẩn nút Stop).

        Args:
            processing: True nếu đang xử lý.
        """
        self._stop_btn.setVisible(processing)

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._stop_btn.hide()
