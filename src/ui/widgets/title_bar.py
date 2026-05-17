"""TitleBar — Thanh tiêu đề tùy chỉnh."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.core.i18n import I18nManager
from src.ui import theme


class _TitleButton(QPushButton):
    """Nút tiêu đề vẽ bằng QPainter — base class."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False

    def enterEvent(self, event: object) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event: object) -> None:
        self._hovered = False
        self.update()

    def _draw_hover_bg(self, painter: QPainter, color: str) -> None:
        if self._hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(0, 0, 32, 32, 16, 16)


class CloseButton(_TitleButton):
    """Nút đóng — vẽ dấu X, hover đỏ."""

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_hover_bg(painter, theme.RED)
        line_color = QColor(theme.BG_BASE) if self._hovered else QColor(theme.TEXT)
        painter.setPen(QPen(line_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        m = 10
        painter.drawLine(m, m, 32 - m, 32 - m)
        painter.drawLine(32 - m, m, m, 32 - m)
        painter.end()


class MinimizeButton(_TitleButton):
    """Nút thu nhỏ — vẽ dấu gạch ngang, hover surface."""

    def paintEvent(self, event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_hover_bg(painter, theme.SURFACE_1)
        line_color = QColor(theme.SUBTEXT_0) if not self._hovered else QColor(theme.TEXT)
        painter.setPen(QPen(line_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(8, 16, 24, 16)
        painter.end()


class TitleBar(QWidget):
    """Thanh tiêu đề tùy chỉnh — tên app, nút thu nhỏ và nút đóng."""

    close_clicked = Signal()
    minimize_clicked = Signal()

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

        self._minimize_btn = MinimizeButton()
        self._minimize_btn.setToolTip("Thu nhỏ")
        self._minimize_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self._minimize_btn)

        self._close_btn = CloseButton()
        self._close_btn.setToolTip("Đóng")
        self._close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self._close_btn)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho thanh tiêu đề."""
        self.setStyleSheet(f"""
            #titleBar {{
                background-color: {theme.BG_MANTLE};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            #titleLabel {{
                color: {theme.TEXT};
                font-size: 14px;
                font-weight: bold;
            }}
        """)
