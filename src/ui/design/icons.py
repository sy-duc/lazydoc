"""Central icon registry for LazyDoc.

Widgets should request semantic icon names from this module instead of using
emoji or hand-drawn button icons.
"""

from enum import Enum
import logging

from PySide6.QtGui import QIcon

from src.ui.design.tokens import COLORS

logger = logging.getLogger(__name__)


class IconName(str, Enum):
    """Semantic icon names used across the app."""

    ABOUT = "about"
    CHECK = "check"
    CHEVRON_DOWN = "chevron_down"
    CHEVRON_UP = "chevron_up"
    CLOSE = "close"
    DOCUMENT = "document"
    DOWNLOAD = "download"
    EDIT = "edit"
    ERROR = "error"
    GLOSSARY = "glossary"
    GUIDE = "guide"
    LANGUAGE = "language"
    PLAY = "play"
    SETTINGS = "settings"
    STOP = "stop"
    SUMMARY = "summary"
    TRASH = "trash"
    UPLOAD = "upload"
    WARNING = "warning"


_ICON_KEYS: dict[IconName, str] = {
    IconName.ABOUT: "fa5s.info-circle",
    IconName.CHECK: "fa5s.check-circle",
    IconName.CHEVRON_DOWN: "fa5s.chevron-down",
    IconName.CHEVRON_UP: "fa5s.chevron-up",
    IconName.CLOSE: "fa5s.times",
    IconName.DOCUMENT: "fa5s.file-alt",
    IconName.DOWNLOAD: "fa5s.download",
    IconName.EDIT: "fa5s.pen",
    IconName.ERROR: "fa5s.times-circle",
    IconName.GLOSSARY: "fa5s.book",
    IconName.GUIDE: "fa5s.question-circle",
    IconName.LANGUAGE: "fa5s.language",
    IconName.PLAY: "fa5s.play",
    IconName.SETTINGS: "fa5s.cog",
    IconName.STOP: "fa5s.stop",
    IconName.SUMMARY: "fa5s.clipboard-list",
    IconName.TRASH: "fa5s.trash",
    IconName.UPLOAD: "fa5s.folder-open",
    IconName.WARNING: "fa5s.exclamation-triangle",
}


def app_icon(
    name: IconName | str,
    color: str = "text",
    disabled_color: str = "disabled_fg",
) -> QIcon:
    """Return a themed icon by semantic name.

    Args:
        name: Semantic icon name.
        color: Color token key or literal color.
        disabled_color: Color token key or literal color for disabled state.
    """
    icon_name = IconName(name)
    icon_color = COLORS.get(color, color)
    icon_disabled_color = COLORS.get(disabled_color, disabled_color)
    try:
        import qtawesome as qta
    except ImportError:
        logger.warning("QtAwesome is not installed; returning empty icon.")
        return QIcon()

    return qta.icon(
        _ICON_KEYS[icon_name],
        color=icon_color,
        color_disabled=icon_disabled_color,
    )
