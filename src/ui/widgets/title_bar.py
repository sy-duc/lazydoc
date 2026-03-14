"""TitleBar — Thanh tiêu đề tùy chỉnh (chỉ có nút đóng)."""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.i18n import I18nManager


class CloseButton(QPushButton):
    """Nút đóng vẽ bằng QPainter — hiển thị rõ trên nền tối."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo CloseButton."""
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False

    def enterEvent(self, event: object) -> None:
        """Bật trạng thái hover."""
        self._hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        """Tắt trạng thái hover."""
        self._hovered = False
        self.update()

    def paintEvent(self, event: object) -> None:
        """Vẽ icon X."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Nền khi hover
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#f38ba8"))
            painter.drawRoundedRect(0, 0, 32, 32, 16, 16)

        # Vẽ dấu X
        cross_color = QColor("#1e1e2e") if self._hovered else QColor("#cdd6f4")
        painter.setPen(QPen(cross_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        margin = 10
        painter.drawLine(margin, margin, 32 - margin, 32 - margin)
        painter.drawLine(32 - margin, margin, margin, 32 - margin)

        painter.end()


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

        # Nút đóng (vẽ bằng QPainter)
        self._close_btn = CloseButton()
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
        """)
