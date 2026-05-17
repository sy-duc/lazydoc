"""BlenderArea — Vùng dropzone kéo thả tài liệu.

Thay thế máy xay QPainter bằng dropzone tối giản:
- Idle: viền dashed, icon upload, text hướng dẫn, format chips
- Hover: viền solid xanh, icon highlight
- Processing: spinner xoay, text trạng thái
- Done: icon check, text hoàn thành (tự reset sau 2s)
"""

from PySide6.QtCore import (
    Property,
    QPropertyAnimation,
    QRectF,
    QPointF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.core.i18n import I18nManager
from src.ui import theme


class BlenderArea(QWidget):
    """Vùng dropzone — kéo thả file + trigger extract khi click."""

    body_clicked = Signal()

    STATE_IDLE = "idle"
    STATE_HOVER = "hover"
    STATE_PROCESSING = "processing"
    STATE_DONE = "done"

    _FORMATS = ["DOCX", "XLSX", "PPTX", "TXT", "MD"]

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo BlenderArea."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self._state = self.STATE_IDLE
        self._status_text = ""
        self._spin_angle = 0.0

        self.setObjectName("dropZone")
        self.setMinimumHeight(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_animations()

    # --- Qt Property cho spin animation ---

    def _get_spin(self) -> float:
        return self._spin_angle

    def _set_spin(self, value: float) -> None:
        self._spin_angle = value
        self.update()

    spin_prop = Property(float, _get_spin, _set_spin)

    def _setup_animations(self) -> None:
        """Tạo animation spinner."""
        self._spin_anim = QPropertyAnimation(self, b"spin_prop")
        self._spin_anim.setDuration(900)
        self._spin_anim.setStartValue(0.0)
        self._spin_anim.setEndValue(360.0)
        self._spin_anim.setLoopCount(-1)

    # --- Paint ---

    def paintEvent(self, event: object) -> None:
        """Vẽ dropzone theo trạng thái hiện tại."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        self._draw_background(painter, w, h)

        icon_r = max(20.0, min(w, h) * 0.12)
        icon_cx = w / 2.0
        icon_cy = h * 0.36

        if self._state == self.STATE_PROCESSING:
            self._draw_spinner(painter, icon_cx, icon_cy, icon_r)
        elif self._state == self.STATE_DONE:
            self._draw_check(painter, icon_cx, icon_cy, icon_r)
        else:
            hover = self._state == self.STATE_HOVER
            icon_color = QColor(theme.BLUE) if hover else QColor(theme.SURFACE_2)
            self._draw_upload_icon(painter, icon_cx, icon_cy, icon_r, icon_color)

        self._draw_texts(painter, w, h)

        painter.end()

    def _draw_background(self, painter: QPainter, w: int, h: int) -> None:
        """Vẽ nền và viền dropzone."""
        if self._state == self.STATE_HOVER:
            border_col = QColor(theme.BLUE)
            bg_col = QColor("#1e2140")
            pen_style = Qt.PenStyle.SolidLine
        else:
            border_col = QColor(theme.SURFACE_1)
            bg_col = QColor(theme.BG_BASE)
            pen_style = Qt.PenStyle.DashLine

        painter.setPen(QPen(border_col, 2, pen_style))
        painter.setBrush(QBrush(bg_col))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

    def _draw_upload_icon(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        r: float,
        color: QColor,
    ) -> None:
        """Vẽ icon upload: vòng tròn + mũi tên lên."""
        pen = QPen(color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        arrow_h = r * 0.65
        tip_y = cy - arrow_h * 0.45
        base_y = cy + arrow_h * 0.35
        wing = arrow_h * 0.35

        painter.drawLine(QPointF(cx, base_y), QPointF(cx, tip_y))
        painter.drawLine(QPointF(cx, tip_y), QPointF(cx - wing, tip_y + wing * 0.7))
        painter.drawLine(QPointF(cx, tip_y), QPointF(cx + wing, tip_y + wing * 0.7))

    def _draw_spinner(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        """Vẽ spinner xoay: ring mờ + arc xanh."""
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Ring nền mờ
        painter.setPen(QPen(QColor(theme.SURFACE_1), 2.5))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Arc xoay — clockwise
        arc_pen = QPen(QColor(theme.BLUE), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        qt_start = int((90.0 - self._spin_angle) * 16)
        qt_span = 100 * 16  # 100 độ arc
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        painter.drawArc(rect, qt_start, qt_span)

    def _draw_check(self, painter: QPainter, cx: float, cy: float, r: float) -> None:
        """Vẽ dấu tick trong vòng tròn xanh lá."""
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(theme.GREEN), 2.0))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Dấu tick
        pen = QPen(
            QColor(theme.GREEN),
            2.0,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
        painter.setPen(pen)
        s = r * 0.45
        painter.drawLine(
            QPointF(cx - s * 0.55, cy),
            QPointF(cx - s * 0.1, cy + s * 0.55),
        )
        painter.drawLine(
            QPointF(cx - s * 0.1, cy + s * 0.55),
            QPointF(cx + s * 0.75, cy - s * 0.55),
        )

    def _draw_texts(self, painter: QPainter, w: int, h: int) -> None:
        """Vẽ text hướng dẫn, trạng thái và format chips."""
        if self._state in (self.STATE_IDLE, self.STATE_HOVER):
            hover = self._state == self.STATE_HOVER
            main_color = QColor(theme.TEXT)
            sub_color = QColor(theme.BLUE if hover else theme.SUBTEXT_0)

            self._draw_text(
                painter,
                self._i18n.t("main.drag_drop"),
                w,
                h * 0.60,
                main_color,
                theme.FONT_MD,
                bold=False,
            )
            self._draw_text(
                painter,
                "hoặc click để chọn file",
                w,
                h * 0.73,
                sub_color,
                theme.FONT_SM,
                bold=False,
            )
            self._draw_format_chips(painter, w, h * 0.88)

        elif self._status_text:
            is_done = self._state == self.STATE_DONE
            text_color = QColor(theme.GREEN if is_done else theme.SUBTEXT_0)
            self._draw_text(
                painter,
                self._status_text,
                w,
                h * 0.64,
                text_color,
                theme.FONT_SM,
                bold=True,
            )

    def _draw_text(
        self,
        painter: QPainter,
        text: str,
        w: int,
        y: float,
        color: QColor,
        font_size: int,
        bold: bool = False,
    ) -> None:
        """Vẽ text căn giữa theo chiều ngang."""
        font = QFont()
        font.setPixelSize(font_size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QPen(color))
        rect = QRectF(0, y - font_size, w, font_size * 2.2)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_format_chips(self, painter: QPainter, w: int, y: float) -> None:
        """Vẽ các chip format hàng ngang (PDF, DOCX, ...)."""
        chip_w = 38.0
        chip_h = 17.0
        gap = 5.0
        total_w = len(self._FORMATS) * chip_w + (len(self._FORMATS) - 1) * gap
        start_x = (w - total_w) / 2.0

        font = QFont()
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)

        for i, fmt in enumerate(self._FORMATS):
            x = start_x + i * (chip_w + gap)
            chip_rect = QRectF(x, y - chip_h / 2, chip_w, chip_h)
            painter.setPen(QPen(QColor(theme.SURFACE_2), 1))
            painter.setBrush(QBrush(QColor(theme.SURFACE_0)))
            painter.drawRoundedRect(chip_rect, 4, 4)
            painter.setPen(QPen(QColor(theme.SUBTEXT_0)))
            painter.drawText(chip_rect, Qt.AlignmentFlag.AlignCenter, fmt)

    # --- Mouse events ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click vào vùng → emit signal trigger extract."""
        if event.button() == Qt.MouseButton.LeftButton and self._state != self.STATE_PROCESSING:
            self.body_clicked.emit()
        super().mousePressEvent(event)

    # --- Public API ---

    def set_drag_hover(self, hovering: bool) -> None:
        """Cập nhật trạng thái hover khi đang kéo file qua vùng này."""
        if hovering:
            self._state = self.STATE_HOVER
        elif self._state == self.STATE_HOVER:
            self._state = self.STATE_IDLE
        self.update()

    def play_file_drop(self) -> None:
        """Phản hồi thị giác khi file được thả vào."""
        self.update()

    def set_status(self, text: str) -> None:
        """Hiển thị trạng thái xử lý và bắt đầu spinner.

        Args:
            text: Chuỗi trạng thái. Rỗng để dừng và về idle.
        """
        self._status_text = text
        if text:
            self._state = self.STATE_PROCESSING
            if self._spin_anim.state() != QPropertyAnimation.State.Running:
                self._spin_anim.start()
        else:
            self._spin_anim.stop()
            self._spin_angle = 0.0
            self._state = self.STATE_IDLE
        self.update()

    def play_done(self) -> None:
        """Hiển thị trạng thái hoàn thành, tự reset sau 2 giây."""
        self._spin_anim.stop()
        self._state = self.STATE_DONE
        self._status_text = "Hoàn thành"
        self.update()
        QTimer.singleShot(2000, self.reset)

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._spin_anim.stop()
        self._spin_angle = 0.0
        self._state = self.STATE_IDLE
        self._status_text = ""
        self.update()
