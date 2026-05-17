"""Base dialog shell for LazyDoc dialogs."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.design.tokens import COLORS, SPACING


class BaseDialog(QDialog):
    """Frameless modal dialog with a shared panel and content layout."""

    shadow_margin = 20

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
        *,
        width: int = 460,
        height: int = 300,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)

        margin = self.shadow_margin
        self.setFixedSize(width + margin * 2, height + margin * 2)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(margin, margin, margin, margin)

        self.panel = QWidget(self)
        self.panel.setObjectName("DialogPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.panel.setGraphicsEffect(shadow)
        outer_layout.addWidget(self.panel)

        self.body_layout = QVBoxLayout(self.panel)
        self.body_layout.setContentsMargins(
            SPACING["xl"],
            SPACING["lg"],
            SPACING["xl"],
            SPACING["lg"],
        )
        self.body_layout.setSpacing(SPACING["md"])

        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "heading")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"background-color: {COLORS['surface_raised']};")
        self.body_layout.addWidget(self.title_label)
