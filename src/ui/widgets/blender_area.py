"""BlenderArea — Vùng hoạt ảnh máy xay tài liệu + drag & drop.

Vẽ máy xay bằng QPainter với các trạng thái:
- Idle: máy tĩnh, hiển thị hướng dẫn kéo thả
- Drag hover: phễu sáng lên, viền highlight
- Processing: máy rung + lưỡi quay
- Done: hiệu ứng tài liệu ra output
"""

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QRect,
    QRectF,
    QPointF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.core.i18n import I18nManager


class BlenderArea(QWidget):
    """Vùng hiển thị hoạt ảnh máy xay tài liệu + khu vực kéo thả file."""

    # Signal khi click vào thân máy xay (trigger extract)
    body_clicked = Signal()

    # Trạng thái máy xay
    STATE_IDLE = "idle"
    STATE_HOVER = "hover"
    STATE_PROCESSING = "processing"
    STATE_DONE = "done"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo BlenderArea."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self._state = self.STATE_IDLE
        self._status_text = ""

        # Thuộc tính animation
        self._shake_offset = 0.0
        self._blade_angle = 0.0
        self._output_progress = 0.0
        self._file_drop_y = 0.0  # vị trí file rơi vào phễu

        self.setObjectName("blenderArea")
        self.setMinimumHeight(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_animations()

    # --- Qt Property cho animation ---

    def _get_shake_offset(self) -> float:
        return self._shake_offset

    def _set_shake_offset(self, value: float) -> None:
        self._shake_offset = value
        self.update()

    def _get_blade_angle(self) -> float:
        return self._blade_angle

    def _set_blade_angle(self, value: float) -> None:
        self._blade_angle = value
        self.update()

    def _get_output_progress(self) -> float:
        return self._output_progress

    def _set_output_progress(self, value: float) -> None:
        self._output_progress = value
        self.update()

    def _get_file_drop_y(self) -> float:
        return self._file_drop_y

    def _set_file_drop_y(self, value: float) -> None:
        self._file_drop_y = value
        self.update()

    shake_offset_prop = Property(float, _get_shake_offset, _set_shake_offset)
    blade_angle_prop = Property(float, _get_blade_angle, _set_blade_angle)
    output_progress_prop = Property(float, _get_output_progress, _set_output_progress)
    file_drop_y_prop = Property(float, _get_file_drop_y, _set_file_drop_y)

    def _setup_animations(self) -> None:
        """Tạo các animation object."""
        # Animation rung máy (lặp liên tục khi processing)
        self._shake_anim = QPropertyAnimation(self, b"shake_offset_prop")
        self._shake_anim.setDuration(80)
        self._shake_anim.setLoopCount(-1)

        # Animation quay lưỡi (lặp liên tục khi processing)
        self._blade_anim = QPropertyAnimation(self, b"blade_angle_prop")
        self._blade_anim.setDuration(600)
        self._blade_anim.setStartValue(0.0)
        self._blade_anim.setEndValue(360.0)
        self._blade_anim.setLoopCount(-1)

        # Animation output (chạy 1 lần khi done)
        self._output_anim = QPropertyAnimation(self, b"output_progress_prop")
        self._output_anim.setDuration(800)
        self._output_anim.setStartValue(0.0)
        self._output_anim.setEndValue(1.0)
        self._output_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Animation file rơi vào phễu (khi drop)
        self._file_drop_anim = QPropertyAnimation(self, b"file_drop_y_prop")
        self._file_drop_anim.setDuration(400)
        self._file_drop_anim.setEasingCurve(QEasingCurve.Type.InQuad)

        # Timer đổi hướng rung
        self._shake_direction = 1
        self._shake_timer = QTimer(self)
        self._shake_timer.setInterval(80)
        self._shake_timer.timeout.connect(self._toggle_shake)

    def _toggle_shake(self) -> None:
        """Đổi hướng rung."""
        self._shake_direction *= -1
        self._shake_offset = 2.0 * self._shake_direction
        self.update()

    # --- Paint ---

    def paintEvent(self, event: object) -> None:
        """Vẽ máy xay tài liệu."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2 + self._shake_offset
        # Tính tỷ lệ scale dựa trên kích thước widget
        scale = min(w / 280, h / 260)

        # Vẽ nền
        self._draw_background(painter, w, h)

        painter.save()
        painter.translate(cx, h * 0.45)
        painter.scale(scale, scale)

        # Vẽ từng phần máy xay
        self._draw_funnel(painter)
        self._draw_body(painter)
        self._draw_blade(painter)
        self._draw_base(painter)

        if self._state == self.STATE_DONE:
            self._draw_output(painter)

        painter.restore()

        # Vẽ text hướng dẫn / trạng thái
        self._draw_text(painter, w, h)

        painter.end()

    def _draw_background(self, painter: QPainter, w: int, h: int) -> None:
        """Vẽ nền với viền."""
        border_color = QColor("#89b4fa") if self._state == self.STATE_HOVER else QColor("#45475a")
        bg = QColor("#1e1e2e") if self._state != self.STATE_HOVER else QColor("#252540")

        painter.setPen(QPen(border_color, 2, Qt.PenStyle.DashLine))
        painter.setBrush(QBrush(bg))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

    def _draw_funnel(self, painter: QPainter) -> None:
        """Vẽ phễu (miệng máy) — hình thang ngược."""
        color = QColor("#585b70")
        if self._state == self.STATE_HOVER:
            color = QColor("#89b4fa")

        path = QPainterPath()
        # Miệng rộng phía trên
        path.moveTo(-50, -70)
        path.lineTo(50, -70)
        # Thu hẹp xuống thân máy
        path.lineTo(30, -35)
        path.lineTo(-30, -35)
        path.closeSubpath()

        painter.setPen(QPen(color.darker(120), 2))
        painter.setBrush(QBrush(color))
        painter.drawPath(path)

        # Vẽ đường kẻ trang trí miệng phễu
        painter.setPen(QPen(color.lighter(140), 1))
        painter.drawLine(-45, -65, 45, -65)

    def _draw_body(self, painter: QPainter) -> None:
        """Vẽ thân máy xay — hình chữ nhật bo góc."""
        body_color = QColor("#45475a")
        if self._state == self.STATE_PROCESSING:
            body_color = QColor("#585b70")

        # Thân máy
        body_rect = QRectF(-35, -38, 70, 60)
        painter.setPen(QPen(body_color.darker(120), 2))

        gradient = QLinearGradient(0, -38, 0, 22)
        gradient.setColorAt(0, body_color)
        gradient.setColorAt(1, body_color.darker(130))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(body_rect, 6, 6)

        # Cửa sổ nhìn bên trong (hình tròn nhỏ)
        window_color = QColor("#313244")
        if self._state == self.STATE_PROCESSING:
            window_color = QColor("#f9e2af")  # sáng vàng khi đang xử lý
        painter.setPen(QPen(QColor("#6c7086"), 2))
        painter.setBrush(QBrush(window_color))
        painter.drawEllipse(QPointF(0, -10), 16, 16)

    def _draw_blade(self, painter: QPainter) -> None:
        """Vẽ lưỡi xay bên trong cửa sổ (quay khi processing)."""
        painter.save()
        painter.translate(0, -10)
        painter.rotate(self._blade_angle)

        blade_color = QColor("#a6adc8")
        if self._state == self.STATE_PROCESSING:
            blade_color = QColor("#cdd6f4")

        painter.setPen(QPen(blade_color, 2))
        # Vẽ 4 cánh
        for i in range(4):
            painter.drawLine(0, 0, 0, -11)
            painter.rotate(90)

        # Tâm lưỡi
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(blade_color))
        painter.drawEllipse(QPointF(0, 0), 3, 3)

        painter.restore()

    def _draw_base(self, painter: QPainter) -> None:
        """Vẽ đế máy + vòi ra output."""
        base_color = QColor("#45475a")
        painter.setPen(QPen(base_color.darker(120), 2))
        painter.setBrush(QBrush(base_color.darker(110)))

        # Đế máy
        base_path = QPainterPath()
        base_path.moveTo(-40, 22)
        base_path.lineTo(40, 22)
        base_path.lineTo(35, 35)
        base_path.lineTo(-35, 35)
        base_path.closeSubpath()
        painter.drawPath(base_path)

        # Vòi xuất output (bên phải)
        spout_color = QColor("#585b70")
        painter.setPen(QPen(spout_color.darker(120), 2))
        painter.setBrush(QBrush(spout_color))
        spout = QPainterPath()
        spout.moveTo(30, 5)
        spout.lineTo(55, 10)
        spout.lineTo(55, 20)
        spout.lineTo(30, 18)
        spout.closeSubpath()
        painter.drawPath(spout)

    def _draw_output(self, painter: QPainter) -> None:
        """Vẽ hiệu ứng tài liệu ra từ vòi khi hoàn tất."""
        if self._output_progress <= 0:
            return

        # Tài liệu output — hình chữ nhật nhỏ giống trang giấy
        progress = self._output_progress
        doc_x = 55 + 15 * progress
        doc_y = 15 + 20 * progress
        opacity = min(1.0, progress * 2)

        painter.setOpacity(opacity)
        painter.setPen(QPen(QColor("#a6e3a1"), 1.5))
        painter.setBrush(QBrush(QColor("#a6e3a1").darker(110)))

        doc_rect = QRectF(doc_x, doc_y, 18, 22)
        painter.drawRoundedRect(doc_rect, 2, 2)

        # Vẽ dòng text giả trên tài liệu
        painter.setPen(QPen(QColor("#1e1e2e"), 1))
        for i in range(3):
            line_y = doc_y + 6 + i * 5
            line_w = 12 if i < 2 else 8
            painter.drawLine(
                QPointF(doc_x + 3, line_y),
                QPointF(doc_x + 3 + line_w, line_y),
            )

        painter.setOpacity(1.0)

    def _draw_text(self, painter: QPainter, w: int, h: int) -> None:
        """Vẽ text hướng dẫn hoặc trạng thái."""
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)

        if self._state == self.STATE_IDLE or self._state == self.STATE_HOVER:
            text = self._i18n.t("main.drag_drop")
            painter.setPen(QPen(QColor("#a6adc8")))
            painter.drawText(QRectF(0, h - 30, w, 24), Qt.AlignmentFlag.AlignCenter, text)
        elif self._status_text:
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#a6e3a1")))
            painter.drawText(QRectF(0, h - 30, w, 24), Qt.AlignmentFlag.AlignCenter, self._status_text)

    # --- Mouse events ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click vào thân máy xay → emit signal extract."""
        if event.button() == Qt.MouseButton.LeftButton and self._state != self.STATE_PROCESSING:
            self.body_clicked.emit()
        super().mousePressEvent(event)

    # --- Public API ---

    def set_drag_hover(self, hovering: bool) -> None:
        """Cập nhật trạng thái khi đang kéo file qua vùng này.

        Args:
            hovering: True nếu đang hover, False nếu không.
        """
        if hovering:
            self._state = self.STATE_HOVER
        else:
            if self._state == self.STATE_HOVER:
                self._state = self.STATE_IDLE
        self.update()

    def play_file_drop(self) -> None:
        """Phát animation file rơi vào phễu (khi drop file)."""
        self._file_drop_anim.setStartValue(0.0)
        self._file_drop_anim.setEndValue(1.0)
        self._file_drop_anim.start()

    def set_status(self, text: str) -> None:
        """Hiển thị trạng thái xử lý và bắt đầu animation.

        Args:
            text: Nội dung trạng thái. Chuỗi rỗng để dừng.
        """
        self._status_text = text
        if text:
            self._state = self.STATE_PROCESSING
            self._start_processing_animation()
        else:
            self._stop_processing_animation()
            self._state = self.STATE_IDLE
        self.update()

    def play_done(self) -> None:
        """Phát animation hoàn tất (output ra tài liệu)."""
        self._stop_processing_animation()
        self._state = self.STATE_DONE
        self._output_progress = 0.0
        self._output_anim.start()

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._stop_processing_animation()
        self._output_anim.stop()
        self._state = self.STATE_IDLE
        self._status_text = ""
        self._shake_offset = 0.0
        self._blade_angle = 0.0
        self._output_progress = 0.0
        self.update()

    def _start_processing_animation(self) -> None:
        """Bắt đầu animation rung + quay."""
        if not self._blade_anim.state() == QPropertyAnimation.State.Running:
            self._blade_anim.start()
        if not self._shake_timer.isActive():
            self._shake_timer.start()

    def _stop_processing_animation(self) -> None:
        """Dừng animation rung + quay."""
        self._blade_anim.stop()
        self._shake_timer.stop()
        self._shake_offset = 0.0
