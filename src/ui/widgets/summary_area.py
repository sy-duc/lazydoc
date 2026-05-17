"""SummaryArea — Vùng hiển thị tóm tắt kết quả và Q&A."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import I18nManager
from src.ui.components import PrimaryButton, SecondaryButton
from src.ui.design import COLORS, IconName, RADIUS, TYPOGRAPHY


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
        header_label = QLabel(self._i18n.t("summary.title"))
        header_label.setObjectName("summaryHeader")
        header.addWidget(header_label)
        header.addStretch()

        self._detail_btn = SecondaryButton(
            self._i18n.t("summary.detail"),
            IconName.DOWNLOAD,
        )
        self._detail_btn.clicked.connect(self.detail_clicked.emit)
        self._detail_btn.hide()
        header.addWidget(self._detail_btn)

        layout.addLayout(header)

        # Vùng tổng quan (luôn hiển thị sau summary)
        self._overview_area = QTextEdit()
        self._overview_area.setObjectName("overviewText")
        self._overview_area.setReadOnly(True)
        self._overview_area.setPlaceholderText(self._i18n.t("summary.placeholder"))
        layout.addWidget(self._overview_area, stretch=2)

        # Vùng Q&A (ẩn đến khi user bắt đầu hỏi)
        self._qa_area = QTextEdit()
        self._qa_area.setObjectName("qaText")
        self._qa_area.setReadOnly(True)
        self._qa_area.hide()
        layout.addWidget(self._qa_area, stretch=3)

        # Disclaimer hiển thị khi chờ Q&A response
        self._disclaimer_label = QLabel(self._i18n.t("summary.disclaimer"))
        self._disclaimer_label.setObjectName("disclaimerLabel")
        self._disclaimer_label.hide()
        layout.addWidget(self._disclaimer_label)

        # Q&A input (ẩn đến khi summary hoàn tất)
        qa_row = QHBoxLayout()
        qa_row.setSpacing(6)
        self._qa_input = QLineEdit()
        self._qa_input.setObjectName("qaInput")
        self._qa_input.setPlaceholderText(self._i18n.t("summary.qa_placeholder"))
        self._qa_input.returnPressed.connect(self._on_send_clicked)
        qa_row.addWidget(self._qa_input)

        self._qa_send_btn = PrimaryButton(self._i18n.t("summary.send"))
        self._qa_send_btn.clicked.connect(self._on_send_clicked)
        qa_row.addWidget(self._qa_send_btn)

        self._qa_widget = QWidget()
        self._qa_widget.setLayout(qa_row)
        self._qa_widget.hide()
        layout.addWidget(self._qa_widget)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet."""
        section_type = TYPOGRAPHY["section"]
        body_type = TYPOGRAPHY["body"]
        caption_type = TYPOGRAPHY["caption"]
        self.setStyleSheet(f"""
            #summaryArea {{
                background-color: transparent;
            }}
            #summaryHeader {{
                color: {COLORS["text_muted"]};
                font-family: '{section_type.family}';
                font-size: {section_type.size}px;
                font-weight: {section_type.weight};
                background: transparent;
                border: none;
            }}
            #overviewText {{
                background-color: {COLORS["surface_subtle"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: {RADIUS["lg"]}px;
                padding: 10px;
                font-family: '{body_type.family}';
                font-size: {body_type.size}px;
            }}
            #qaText {{
                background-color: {COLORS["surface_subtle"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: {RADIUS["lg"]}px;
                padding: 10px;
                font-family: '{body_type.family}';
                font-size: {body_type.size}px;
            }}
            #disclaimerLabel {{
                color: {COLORS["text_subtle"]};
                font-family: '{caption_type.family}';
                font-size: {caption_type.size}px;
                font-style: italic;
                padding: 2px 0px;
            }}
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
        separator = "\n\n---\n" if current else ""
        prefix = self._i18n.t("summary.question_prefix")
        self._qa_area.insertPlainText(f"{separator}{prefix}: {question}\n\n")
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
