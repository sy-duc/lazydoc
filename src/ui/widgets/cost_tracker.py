"""CostTracker — Vùng theo dõi chi phí và token realtime."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.i18n import I18nManager


class CostTracker(QWidget):
    """Vùng hiển thị chi phí API realtime + nút Stop."""

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
        """Thiết lập layout vùng chi phí."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(16)

        # Label Token
        self._token_label = QLabel(f"{self._i18n.t('main.token_label')}: 0")
        self._token_label.setObjectName("tokenLabel")
        layout.addWidget(self._token_label)

        # Label Chi phí
        self._cost_label = QLabel(f"{self._i18n.t('main.cost_label')}: $0.00")
        self._cost_label.setObjectName("costLabel")
        layout.addWidget(self._cost_label)

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
            #tokenLabel, #costLabel {
                color: #a6adc8;
                font-size: 12px;
                font-family: monospace;
                background: transparent;
                border: none;
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

    def update_cost(self, tokens: int, cost: float) -> None:
        """Cập nhật hiển thị token và chi phí.

        Args:
            tokens: Số token đã sử dụng.
            cost: Chi phí tính bằng USD.
        """
        self._token_label.setText(f"{self._i18n.t('main.token_label')}: {tokens:,}")
        self._cost_label.setText(f"{self._i18n.t('main.cost_label')}: ${cost:.4f}")

    def set_processing(self, processing: bool) -> None:
        """Bật/tắt trạng thái đang xử lý (hiện/ẩn nút Stop).

        Args:
            processing: True nếu đang xử lý.
        """
        self._stop_btn.setVisible(processing)

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._token_label.setText(f"{self._i18n.t('main.token_label')}: 0")
        self._cost_label.setText(f"{self._i18n.t('main.cost_label')}: $0.00")
        self._stop_btn.hide()
