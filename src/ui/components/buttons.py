"""Base button components that enforce LazyDoc UI semantics."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton, QWidget

from src.ui.design.icons import IconName, app_icon


class BaseButton(QPushButton):
    """Common button behavior shared by semantic button classes."""

    object_name = "BaseButton"

    def __init__(
        self,
        text: str = "",
        icon_name: IconName | str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName(self.object_name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        if icon_name is not None:
            self.setIcon(app_icon(icon_name, self._icon_color()))
            self.setIconSize(QSize(16, 16))

    def _icon_color(self) -> str:
        return "text"


class PrimaryButton(BaseButton):
    """Primary call-to-action button."""

    object_name = "PrimaryButton"

    def _icon_color(self) -> str:
        return "primary_fg"


class SecondaryButton(BaseButton):
    """Secondary action button."""

    object_name = "SecondaryButton"


class DangerButton(BaseButton):
    """Destructive or stop action button."""

    object_name = "DangerButton"

    def _icon_color(self) -> str:
        return "primary_fg"


class StopButton(DangerButton):
    """Standard stop button used during processing states."""

    def __init__(self, text: str = "Dừng", parent: QWidget | None = None) -> None:
        super().__init__(text, IconName.STOP, parent)


class IconButton(QPushButton):
    """Compact icon-only button with required tooltip."""

    def __init__(
        self,
        icon_name: IconName | str,
        tooltip: str,
        parent: QWidget | None = None,
        *,
        color: str = "text_muted",
        size: int = 36,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setFixedSize(size, size)
        self.setIcon(app_icon(icon_name, color))
        self.setIconSize(QSize(16, 16))
