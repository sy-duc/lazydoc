"""SummaryArea — Vùng hiển thị tóm tắt kết quả và Q&A."""

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.ui import theme


class SummaryArea(QWidget):
    """Vùng hiển thị tóm tắt kết quả tổng hợp và Q&A.

    Layout:
        - overview_area: hiển thị tổng quan (luôn hiển thị sau summary).
        - qa_area: hiển thị lịch sử Q&A (ẩn đến khi user bắt đầu hỏi).
        - disclaimer: hiển thị khi đang chờ Q&A response.
        - input row: ô nhập câu hỏi (ẩn đến khi summary hoàn tất).
    """

    detail_clicked = Signal()
    qa_submitted = Signal(str)

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
        header.setSpacing(6)

        icon_label = QLabel()
        icon_label.setPixmap(theme.pixmap("text-box-outline", color=theme.SUBTEXT_0, size=14))
        header.addWidget(icon_label)

        header_label = QLabel("Tóm tắt")
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

        # Vùng tổng quan (luôn hiển thị sau summary)
        self._overview_area = QTextEdit()
        self._overview_area.setObjectName("overviewText")
        self._overview_area.setReadOnly(True)
        self._overview_area.setPlaceholderText("Kết quả tổng hợp sẽ hiển thị tại đây...")
        layout.addWidget(self._overview_area, stretch=2)

        # Vùng Q&A (ẩn đến khi user bắt đầu hỏi)
        self._qa_area = QTextEdit()
        self._qa_area.setObjectName("qaText")
        self._qa_area.setReadOnly(True)
        self._qa_area.hide()
        layout.addWidget(self._qa_area, stretch=3)

        # Disclaimer hiển thị khi chờ Q&A response
        self._disclaimer_label = QLabel(
            "Câu trả lời dựa trên báo cáo tổng hợp, không phải tài liệu gốc."
        )
        self._disclaimer_label.setObjectName("disclaimerLabel")
        self._disclaimer_label.hide()
        layout.addWidget(self._disclaimer_label)

        # Q&A input (ẩn đến khi summary hoàn tất)
        qa_row = QHBoxLayout()
        qa_row.setSpacing(6)
        self._qa_input = QLineEdit()
        self._qa_input.setObjectName("qaInput")
        self._qa_input.setPlaceholderText("Hỏi thêm hoặc yêu cầu focus vào chủ đề cần quan tâm...")
        self._qa_input.returnPressed.connect(self._on_send_clicked)
        qa_row.addWidget(self._qa_input)

        self._qa_send_btn = QPushButton("Gửi")
        self._qa_send_btn.setObjectName("qaSendBtn")
        self._qa_send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._qa_send_btn.clicked.connect(self._on_send_clicked)
        qa_row.addWidget(self._qa_send_btn)

        self._qa_widget = QWidget()
        self._qa_widget.setLayout(qa_row)
        self._qa_widget.hide()
        layout.addWidget(self._qa_widget)

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
            #overviewText {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 12px 14px;
                font-size: 13px;
                line-height: 1.5;
            }
            #qaText {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px 14px;
                font-size: 13px;
                line-height: 1.5;
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
            #disclaimerLabel {
                color: #6c7086;
                font-size: 11px;
                font-style: italic;
                padding: 2px 0px;
            }
            #qaInput {
                background-color: #181825;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #qaInput:focus {
                border-color: #89b4fa;
            }
            #qaSendBtn {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 60px;
            }
            #qaSendBtn:hover {
                background-color: #74c7ec;
            }
            #qaSendBtn:disabled {
                background-color: #313244;
                color: #6c7086;
            }
        """)

    def _on_send_clicked(self) -> None:
        """Xử lý khi người dùng bấm Gửi hoặc Enter."""
        question = self._qa_input.text().strip()
        if not question:
            return
        self._qa_input.clear()
        self.qa_submitted.emit(question)

    # --- Public API ---

    def set_summary(self, text: str, typing_effect: bool = True) -> None:
        """Hiển thị nội dung tóm tắt vào vùng tổng quan.

        Args:
            text: Nội dung tóm tắt.
            typing_effect: True để hiển thị với hiệu ứng typing.
        """
        self._stop_typing()
        if typing_effect:
            self._start_typing(text)
        else:
            self._overview_area.setPlainText(text)

    def _start_typing(self, text: str) -> None:
        """Bắt đầu hiệu ứng typing vào overview_area."""
        self._typing_text = text
        self._typing_index = 0
        self._overview_area.clear()
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(20)
        self._typing_timer.timeout.connect(self._type_next_char)
        self._typing_timer.start()

    def _type_next_char(self) -> None:
        """Hiển thị ký tự tiếp theo trong hiệu ứng typing."""
        if self._typing_index < len(self._typing_text):
            self._overview_area.insertPlainText(self._typing_text[self._typing_index])
            self._typing_index += 1
        else:
            self._stop_typing()

    def _stop_typing(self) -> None:
        """Dừng hiệu ứng typing."""
        if self._typing_timer and self._typing_timer.isActive():
            self._typing_timer.stop()
            self._typing_timer = None

    def append_text(self, text: str) -> None:
        """Thêm text vào cuối vùng Q&A (dùng cho streaming câu trả lời).

        Args:
            text: Đoạn text cần thêm.
        """
        self._qa_area.insertPlainText(text)
        scrollbar = self._qa_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def append_qa_question(self, question: str) -> None:
        """Thêm câu hỏi vào vùng Q&A, hiện vùng này nếu đang ẩn.

        Args:
            question: Câu hỏi của người dùng.
        """
        if not self._qa_area.isVisible():
            self._qa_area.show()

        current = self._qa_area.toPlainText()
        separator = "\n\n" + "─" * 40 + "\n" if current else ""
        self._qa_area.insertPlainText(f"{separator}▸ {question}\n\n")
        scrollbar = self._qa_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_detail_button(self) -> None:
        """Hiển thị nút Chi tiết (chỉ gọi sau khi summary hoàn tất)."""
        self._detail_btn.show()

    def show_qa_input(self) -> None:
        """Hiển thị ô Q&A input (chỉ gọi sau khi summary hoàn tất)."""
        self._qa_widget.show()
        self._qa_send_btn.setEnabled(True)
        self._qa_input.setEnabled(True)

    def show_disclaimer(self) -> None:
        """Hiển thị disclaimer khi chờ Q&A response."""
        self._disclaimer_label.show()
        self.set_qa_processing(True)

    def hide_disclaimer(self) -> None:
        """Ẩn disclaimer khi Q&A response bắt đầu stream."""
        self._disclaimer_label.hide()

    def set_qa_processing(self, processing: bool) -> None:
        """Bật/tắt trạng thái đang xử lý Q&A.

        Args:
            processing: True để disable input, False để re-enable.
        """
        self._qa_send_btn.setEnabled(not processing)
        self._qa_input.setEnabled(not processing)

    def clear(self) -> None:
        """Xóa toàn bộ nội dung (cả overview và Q&A)."""
        self._stop_typing()
        self._overview_area.clear()
        self._qa_area.clear()
        self._qa_area.hide()
        self._detail_btn.hide()
        self._qa_widget.hide()
        self._disclaimer_label.hide()
