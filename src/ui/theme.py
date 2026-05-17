"""theme.py — Design tokens và icon utilities cho toàn bộ UI LazyDoc."""

from __future__ import annotations

try:
    import qtawesome as qta

    _QTA_AVAILABLE = True
except ImportError:
    _QTA_AVAILABLE = False

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap

# =============================================================================
# Catppuccin Mocha — Color Tokens
# =============================================================================

# Backgrounds
BG_BASE = "#1e1e2e"
BG_MANTLE = "#181825"
BG_CRUST = "#11111b"

# Surfaces
SURFACE_0 = "#313244"
SURFACE_1 = "#45475a"
SURFACE_2 = "#585b70"

# Text
TEXT = "#cdd6f4"
SUBTEXT_1 = "#bac2de"
SUBTEXT_0 = "#a6adc8"
MUTED = "#6c7086"

# Accents
BLUE = "#89b4fa"
LAVENDER = "#b4befe"
SAPPHIRE = "#74c7ec"
GREEN = "#a6e3a1"
TEAL = "#94e2d5"
YELLOW = "#f9e2af"
MAUVE = "#cba6f7"
RED = "#f38ba8"
MAROON = "#eba0ac"

# =============================================================================
# Typography
# =============================================================================

FONT_XS = 10
FONT_SM = 11
FONT_MD = 13
FONT_LG = 15
FONT_XL = 18

# =============================================================================
# Geometry
# =============================================================================

RADIUS_SM = 6
RADIUS_MD = 8
RADIUS_LG = 12

# =============================================================================
# Icons — Material Design via qtawesome
# =============================================================================


def icon(name: str, color: str = TEXT, scale: float = 1.0) -> QIcon:
    """Tạo QIcon từ mdi.{name} qua qtawesome.

    Args:
        name: Tên icon mdi không có prefix, ví dụ "cog-outline".
        color: Màu hex của icon.
        scale: Hệ số scale (dùng cho icon nhỏ/lớn hơn mặc định).

    Returns:
        QIcon sẵn dùng cho QPushButton.setIcon() hoặc QLabel.setPixmap().
    """
    if _QTA_AVAILABLE:
        if scale != 1.0:
            return qta.icon(f"mdi.{name}", color=color, options=[{"scale_factor": scale}])
        return qta.icon(f"mdi.{name}", color=color)
    return QIcon()


def pixmap(name: str, color: str = TEXT, size: int = 16) -> QPixmap:
    """Tạo QPixmap từ icon mdi, dùng cho QLabel.setPixmap()."""
    if _QTA_AVAILABLE:
        return qta.icon(f"mdi.{name}", color=color).pixmap(QSize(size, size))
    return QPixmap()


# =============================================================================
# Common QSS Snippets
# =============================================================================


def btn_primary_qss(obj_name: str) -> str:
    """Stylesheet nút CTA chính (màu mauve/tím)."""
    return f"""
        #{obj_name} {{
            background-color: {MAUVE};
            color: {BG_BASE};
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 8px 20px;
            font-size: {FONT_MD}px;
            font-weight: bold;
        }}
        #{obj_name}:hover {{ background-color: {LAVENDER}; }}
        #{obj_name}:pressed {{ background-color: {BLUE}; }}
        #{obj_name}:disabled {{ background-color: {SURFACE_0}; color: {MUTED}; }}
    """


def btn_secondary_qss(obj_name: str, fg: str = BLUE) -> str:
    """Stylesheet nút action phụ (nền neutral, text màu accent)."""
    return f"""
        #{obj_name} {{
            background-color: {SURFACE_1};
            color: {fg};
            border: 1px solid {SURFACE_2};
            border-radius: {RADIUS_MD}px;
            padding: 8px 20px;
            font-size: {FONT_MD}px;
            font-weight: bold;
        }}
        #{obj_name}:hover {{ background-color: {SURFACE_2}; }}
        #{obj_name}:pressed {{ background-color: {SURFACE_0}; }}
        #{obj_name}:disabled {{ color: {MUTED}; border-color: {SURFACE_1}; }}
    """


def btn_success_qss(obj_name: str) -> str:
    """Stylesheet nút success/save (màu xanh lá)."""
    return f"""
        #{obj_name} {{
            background-color: {GREEN};
            color: {BG_BASE};
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 8px 24px;
            font-size: {FONT_MD}px;
            font-weight: bold;
        }}
        #{obj_name}:hover {{ background-color: {TEAL}; }}
        #{obj_name}:pressed {{ background-color: {SAPPHIRE}; }}
        #{obj_name}:disabled {{ background-color: {SURFACE_0}; color: {MUTED}; }}
    """


def btn_danger_qss(obj_name: str) -> str:
    """Stylesheet nút stop/danger (màu đỏ hồng)."""
    return f"""
        #{obj_name} {{
            background-color: {RED};
            color: {BG_BASE};
            border: none;
            border-radius: {RADIUS_SM}px;
            padding: 5px 16px;
            font-size: {FONT_SM}px;
            font-weight: bold;
        }}
        #{obj_name}:hover {{ background-color: {MAROON}; }}
    """


def btn_icon_qss(*obj_names: str, size: int = 36) -> str:
    """Stylesheet cho nút icon-only (vuông nhỏ, không viền)."""
    selectors = ", ".join(f"#{n}" for n in obj_names)
    selectors_hover = ", ".join(f"#{n}:hover" for n in obj_names)
    selectors_pressed = ", ".join(f"#{n}:pressed" for n in obj_names)
    return f"""
        {selectors} {{
            background-color: transparent;
            border: none;
            border-radius: {RADIUS_MD}px;
            padding: 0;
            min-width: {size}px;
            max-width: {size}px;
            min-height: {size}px;
            max-height: {size}px;
        }}
        {selectors_hover} {{ background-color: {SURFACE_1}; }}
        {selectors_pressed} {{ background-color: {SURFACE_0}; }}
    """


def input_qss(obj_name: str) -> str:
    """Stylesheet cho input field."""
    return f"""
        #{obj_name} {{
            background-color: {SURFACE_0};
            color: {TEXT};
            border: 1px solid {SURFACE_1};
            border-radius: {RADIUS_MD}px;
            padding: 6px 10px;
            font-size: {FONT_MD}px;
        }}
        #{obj_name}:focus {{ border-color: {BLUE}; }}
        #{obj_name}:disabled {{ color: {MUTED}; }}
    """


def panel_qss(obj_name: str) -> str:
    """Stylesheet cho panel/card trong dialog."""
    return f"""
        #{obj_name} {{
            background-color: #262640;
            border: 1px solid {SURFACE_2};
            border-radius: {RADIUS_LG}px;
        }}
    """


def combo_qss(obj_name: str) -> str:
    """Stylesheet cho QComboBox."""
    return f"""
        #{obj_name} {{
            background-color: {SURFACE_0};
            color: {TEXT};
            border: 1px solid {SURFACE_1};
            border-radius: {RADIUS_MD}px;
            padding: 6px 10px;
            font-size: {FONT_MD}px;
        }}
        #{obj_name}::drop-down {{
            border: none;
            width: 24px;
        }}
        #{obj_name} QAbstractItemView {{
            background-color: {SURFACE_0};
            color: {TEXT};
            border: 1px solid {SURFACE_1};
            selection-background-color: {SURFACE_1};
            outline: none;
        }}
    """
