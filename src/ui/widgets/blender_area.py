"""BlenderArea — Dropzone xử lý tài liệu.

Tên class giữ nguyên để tương thích với MainWindow, nhưng visual hiện là vùng
kéo thả tài liệu gọn và chuyên nghiệp hơn.
"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from src.core.i18n import I18nManager
from src.ui.design import COLORS, RADIUS, TYPOGRAPHY


class BlenderArea(QWidget):
    """Vùng kéo thả file và trigger extract."""

    body_clicked = Signal()

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
        self._activity_progress = 0.0
        self._output_progress = 0.0
        self._file_drop_progress = 0.0

        self.setObjectName("blenderArea")
        self.setMinimumHeight(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_animations()

    # --- Qt animation properties ---

    def _get_activity_progress(self) -> float:
        return self._activity_progress

    def _set_activity_progress(self, value: float) -> None:
        self._activity_progress = value
        self.update()

    def _get_output_progress(self) -> float:
        return self._output_progress

    def _set_output_progress(self, value: float) -> None:
        self._output_progress = value
        self.update()

    def _get_file_drop_progress(self) -> float:
        return self._file_drop_progress

    def _set_file_drop_progress(self, value: float) -> None:
        self._file_drop_progress = value
        self.update()

    activity_progress_prop = Property(
        float,
        _get_activity_progress,
        _set_activity_progress,
    )
    output_progress_prop = Property(float, _get_output_progress, _set_output_progress)
    file_drop_progress_prop = Property(
        float,
        _get_file_drop_progress,
        _set_file_drop_progress,
    )

    def _setup_animations(self) -> None:
        """Tạo animation nhẹ cho processing, drop và done."""
        self._activity_anim = QPropertyAnimation(self, b"activity_progress_prop")
        self._activity_anim.setDuration(1000)
        self._activity_anim.setStartValue(0.0)
        self._activity_anim.setEndValue(1.0)
        self._activity_anim.setLoopCount(-1)
        self._activity_anim.setEasingCurve(QEasingCurve.Type.InOutSine)

        self._output_anim = QPropertyAnimation(self, b"output_progress_prop")
        self._output_anim.setDuration(700)
        self._output_anim.setStartValue(0.0)
        self._output_anim.setEndValue(1.0)
        self._output_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._file_drop_anim = QPropertyAnimation(self, b"file_drop_progress_prop")
        self._file_drop_anim.setDuration(450)
        self._file_drop_anim.setStartValue(0.0)
        self._file_drop_anim.setEndValue(1.0)
        self._file_drop_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # --- Paint ---

    def paintEvent(self, event: object) -> None:
        """Vẽ dropzone tài liệu."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        self._draw_background(painter, rect)
        self._draw_document_mark(painter, rect)
        self._draw_text(painter, rect)

        painter.end()

    def _draw_background(self, painter: QPainter, rect: QRectF) -> None:
        """Vẽ nền và border trạng thái."""
        border = COLORS["border"]
        bg = COLORS["surface"]
        if self._state == self.STATE_HOVER:
            border = COLORS["primary"]
            bg = COLORS["surface_raised"]
        elif self._state == self.STATE_PROCESSING:
            border = COLORS["primary"]
        elif self._state == self.STATE_DONE:
            border = COLORS["success"]

        painter.setBrush(QColor(bg))
        painter.setPen(QPen(QColor(border), 2, Qt.PenStyle.DashLine))
        painter.drawRoundedRect(rect, RADIUS["xl"], RADIUS["xl"])

    def _draw_document_mark(self, painter: QPainter, rect: QRectF) -> None:
        """Vẽ biểu tượng tài liệu trung tâm."""
        size = min(rect.width() * 0.32, rect.height() * 0.42, 82)
        x = rect.center().x() - size / 2
        y = rect.top() + max(22, rect.height() * 0.14)

        if self._file_drop_progress > 0:
            y += (1.0 - self._file_drop_progress) * 18

        if self._state == self.STATE_PROCESSING:
            y += 2.0 * (self._activity_progress - 0.5)

        doc_rect = QRectF(x, y, size, size * 1.12)
        fold = size * 0.24

        body_color = QColor(COLORS["surface_raised"])
        border_color = QColor(COLORS["primary"] if self._state == self.STATE_HOVER else COLORS["border_strong"])
        if self._state == self.STATE_DONE:
            border_color = QColor(COLORS["success"])

        path = QPainterPath()
        path.moveTo(doc_rect.left(), doc_rect.top())
        path.lineTo(doc_rect.right() - fold, doc_rect.top())
        path.lineTo(doc_rect.right(), doc_rect.top() + fold)
        path.lineTo(doc_rect.right(), doc_rect.bottom())
        path.lineTo(doc_rect.left(), doc_rect.bottom())
        path.closeSubpath()

        painter.setBrush(body_color)
        painter.setPen(QPen(border_color, 1.8))
        painter.drawPath(path)

        fold_path = QPainterPath()
        fold_path.moveTo(doc_rect.right() - fold, doc_rect.top())
        fold_path.lineTo(doc_rect.right() - fold, doc_rect.top() + fold)
        fold_path.lineTo(doc_rect.right(), doc_rect.top() + fold)
        painter.setBrush(QColor(COLORS["secondary"]))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawPath(fold_path)

        line_color = QColor(COLORS["text_subtle"])
        painter.setPen(QPen(line_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        line_left = doc_rect.left() + size * 0.18
        line_right = doc_rect.right() - size * 0.18
        first_line = doc_rect.top() + size * 0.46
        for idx, scale in enumerate((1.0, 0.78, 0.58)):
            yy = first_line + idx * size * 0.16
            painter.drawLine(
                QPointF(line_left, yy),
                QPointF(line_left + (line_right - line_left) * scale, yy),
            )

        if self._state == self.STATE_PROCESSING:
            self._draw_activity_dot(painter, doc_rect)
        elif self._state == self.STATE_DONE:
            self._draw_done_check(painter, doc_rect)

    def _draw_activity_dot(self, painter: QPainter, doc_rect: QRectF) -> None:
        """Vẽ dot pulse khi đang xử lý."""
        radius = 4 + 3 * self._activity_progress
        opacity = 1.0 - 0.45 * self._activity_progress
        center_x = doc_rect.center().x()
        center_y = doc_rect.bottom() + 13

        painter.save()
        painter.setOpacity(opacity)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["primary"]))
        painter.drawEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
        painter.restore()

    def _draw_done_check(self, painter: QPainter, doc_rect: QRectF) -> None:
        """Vẽ dấu hoàn tất."""
        progress = max(0.2, self._output_progress)
        badge = QRectF(doc_rect.right() - 20, doc_rect.bottom() - 20, 28, 28)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLORS["success"]))
        painter.drawEllipse(badge)

        painter.setPen(QPen(QColor(COLORS["primary_fg"]), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        start = badge.center()
        painter.drawLine(
            QPointF(start.x() - 7, start.y()),
            QPointF(start.x() - 2, start.y() + 5 * progress),
        )
        painter.drawLine(
            QPointF(start.x() - 2, start.y() + 5 * progress),
            QPointF(start.x() + 8 * progress, start.y() - 7 * progress),
        )

    def _draw_text(self, painter: QPainter, rect: QRectF) -> None:
        """Vẽ heading, mô tả và trạng thái."""
        heading = TYPOGRAPHY["section"]
        body = TYPOGRAPHY["caption"]

        title_font = QFont(heading.family, heading.size)
        title_font.setWeight(heading.weight)
        painter.setFont(title_font)
        painter.setPen(QColor(COLORS["text"]))

        title = self._title_text()
        title_rect = QRectF(rect.left() + 12, rect.bottom() - 72, rect.width() - 24, 22)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)

        body_font = QFont(body.family, body.size)
        body_font.setWeight(body.weight)
        painter.setFont(body_font)
        painter.setPen(QColor(COLORS["text_muted"]))

        subtitle = self._subtitle_text()
        subtitle_rect = QRectF(rect.left() + 16, rect.bottom() - 48, rect.width() - 32, 18)
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter, subtitle)

        if self._state in (self.STATE_PROCESSING, self.STATE_DONE):
            self._draw_status_chip(painter, rect)

    def _title_text(self) -> str:
        if self._state == self.STATE_PROCESSING and self._status_text:
            return self._status_text
        if self._state == self.STATE_DONE:
            return self._i18n.t("dropzone.done")
        if self._state == self.STATE_HOVER:
            return self._i18n.t("dropzone.release")
        return self._i18n.t("dropzone.title")

    def _subtitle_text(self) -> str:
        if self._state == self.STATE_PROCESSING:
            return self._i18n.t("dropzone.processing_hint")
        if self._state == self.STATE_DONE:
            return self._i18n.t("dropzone.done_hint")
        return self._i18n.t("dropzone.subtitle")

    def _draw_status_chip(self, painter: QPainter, rect: QRectF) -> None:
        """Vẽ chip trạng thái nhỏ phía trên."""
        chip_text = self._i18n.t("dropzone.processing")
        chip_color = COLORS["primary"]
        if self._state == self.STATE_DONE:
            chip_text = self._i18n.t("dropzone.ready")
            chip_color = COLORS["success"]

        chip_font = QFont(TYPOGRAPHY["caption"].family, TYPOGRAPHY["caption"].size)
        chip_font.setWeight(700)
        painter.setFont(chip_font)
        metrics = painter.fontMetrics()
        width = metrics.horizontalAdvance(chip_text) + 24
        chip = QRectF(rect.center().x() - width / 2, rect.top() + 12, width, 24)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(chip_color))
        painter.drawRoundedRect(chip, 12, 12)
        painter.setPen(QColor(COLORS["primary_fg"]))
        painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, chip_text)

    # --- Mouse events ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Click vào dropzone để extract."""
        if event.button() == Qt.MouseButton.LeftButton and self._state != self.STATE_PROCESSING:
            self.body_clicked.emit()
        super().mousePressEvent(event)

    # --- Public API ---

    def set_drag_hover(self, hovering: bool) -> None:
        """Cập nhật trạng thái khi kéo file vào/rời khỏi vùng dropzone."""
        if hovering:
            self._state = self.STATE_HOVER
        elif self._state == self.STATE_HOVER:
            self._state = self.STATE_IDLE
        self.update()

    def play_file_drop(self) -> None:
        """Phát animation khi drop file."""
        self._file_drop_progress = 0.0
        self._file_drop_anim.start()

    def set_status(self, text: str) -> None:
        """Hiển thị trạng thái xử lý. Chuỗi rỗng để dừng."""
        self._status_text = text
        if text:
            self._state = self.STATE_PROCESSING
            self._start_processing_animation()
        else:
            self._stop_processing_animation()
            self._state = self.STATE_IDLE
        self.update()

    def play_done(self) -> None:
        """Phát trạng thái hoàn tất."""
        self._stop_processing_animation()
        self._state = self.STATE_DONE
        self._output_progress = 0.0
        self._output_anim.start()

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._stop_processing_animation()
        self._output_anim.stop()
        self._file_drop_anim.stop()
        self._state = self.STATE_IDLE
        self._status_text = ""
        self._activity_progress = 0.0
        self._output_progress = 0.0
        self._file_drop_progress = 0.0
        self.update()

    def _start_processing_animation(self) -> None:
        """Bắt đầu animation processing."""
        if self._activity_anim.state() != QPropertyAnimation.State.Running:
            self._activity_anim.start()

    def _stop_processing_animation(self) -> None:
        """Dừng animation processing."""
        self._activity_anim.stop()
        self._activity_progress = 0.0
