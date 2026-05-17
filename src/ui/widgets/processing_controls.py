"""ProcessingControls — Minimal controls shown while work is running."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from src.core.i18n import I18nManager
from src.ui.components import StopButton
from src.ui.design import COLORS, RADIUS


class ProcessingControls(QWidget):
    """Show the stop action while extract, summary, or Q&A is running."""

    stop_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo ProcessingControls."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self.setObjectName("processingControls")
        self.setFixedHeight(40)
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(16)

        layout.addStretch()

        self._stop_btn = StopButton(self._i18n.t("main.btn_stop"))
        self._stop_btn.clicked.connect(self.stop_clicked.emit)
        self._stop_btn.hide()
        layout.addWidget(self._stop_btn)

    def _setup_style(self) -> None:
        """Áp dụng style cục bộ cho container."""
        self.setStyleSheet(f"""
            #processingControls {{
                background-color: {COLORS["surface_subtle"]};
                border: 1px solid {COLORS["border"]};
                border-radius: {RADIUS["md"]}px;
            }}
        """)

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt trạng thái đang xử lý.

        Args:
            processing: True nếu đang xử lý.
        """
        self._stop_btn.setVisible(processing)

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._stop_btn.hide()
