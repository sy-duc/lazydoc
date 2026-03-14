"""SummaryArea — Vùng hiển thị tóm tắt kết quả (có hiệu ứng typing)."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.core.i18n import I18nManager


class SummaryArea(QWidget):
    """Vùng hiển thị tóm tắt kết quả tổng hợp."""

    detail_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo SummaryArea."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self.setObjectName("summaryArea")
        self._typing_timer: QTimer | None = None
        self._typing_text = ""
        self._typing_index = 0
        self._setup_ui()
        self._setup_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout vùng tóm tắt."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header với nút Chi tiết
        header = QHBoxLayout()
        header_label = QLabel("📋 Tóm tắt")
        header_label.setObjectName("summaryHeader")
        header.addWidget(header_label)
        header.addStretch()

        self._detail_btn = QPushButton("Chi tiết ↓")
        self._detail_btn.setObjectName("detailBtn")
        self._detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._detail_btn.clicked.connect(self.detail_clicked.emit)
        self._detail_btn.hide()
        header.addWidget(self._detail_btn)

        layout.addLayout(header)

        # Vùng hiển thị nội dung tóm tắt
        self._text_area = QTextEdit()
        self._text_area.setObjectName("summaryText")
        self._text_area.setReadOnly(True)
        self._text_area.setPlaceholderText("Kết quả tổng hợp sẽ hiển thị tại đây...")
        layout.addWidget(self._text_area)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet."""
        self.setStyleSheet("""
            #summaryArea {
                background-color: transparent;
            }
            #summaryHeader {
                color: #a6adc8;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
            #summaryText {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-family: monospace;
            }
            #detailBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            #detailBtn:hover {
                background-color: #74c7ec;
            }
        """)

    def set_summary(self, text: str, typing_effect: bool = True) -> None:
        """Hiển thị nội dung tóm tắt.

        Args:
            text: Nội dung tóm tắt.
            typing_effect: True để hiển thị với hiệu ứng typing.
        """
        self._stop_typing()
        if typing_effect:
            self._start_typing(text)
        else:
            self._text_area.setPlainText(text)
        self._detail_btn.show()

    def _start_typing(self, text: str) -> None:
        """Bắt đầu hiệu ứng typing.

        Args:
            text: Nội dung cần hiển thị từng ký tự.
        """
        self._typing_text = text
        self._typing_index = 0
        self._text_area.clear()
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(20)
        self._typing_timer.timeout.connect(self._type_next_char)
        self._typing_timer.start()

    def _type_next_char(self) -> None:
        """Hiển thị ký tự tiếp theo trong hiệu ứng typing."""
        if self._typing_index < len(self._typing_text):
            self._text_area.insertPlainText(self._typing_text[self._typing_index])
            self._typing_index += 1
        else:
            self._stop_typing()

    def _stop_typing(self) -> None:
        """Dừng hiệu ứng typing."""
        if self._typing_timer and self._typing_timer.isActive():
            self._typing_timer.stop()
            self._typing_timer = None

    def append_text(self, text: str) -> None:
        """Thêm text vào cuối vùng tóm tắt (dùng cho streaming).

        Args:
            text: Đoạn text cần thêm.
        """
        self._text_area.insertPlainText(text)
        self._detail_btn.show()

    def clear(self) -> None:
        """Xóa nội dung tóm tắt."""
        self._stop_typing()
        self._text_area.clear()
        self._detail_btn.hide()
