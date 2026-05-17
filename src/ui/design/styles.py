"""QSS builders for shared LazyDoc UI styling."""

from src.ui.design.tokens import COLORS, RADIUS, SPACING, TYPOGRAPHY


def _font(role: str) -> str:
    style = TYPOGRAPHY[role]
    return (
        f"font-family: '{style.family}'; "
        f"font-size: {style.size}px; "
        f"font-weight: {style.weight};"
    )


def build_global_stylesheet() -> str:
    """Build the global stylesheet for base components.

    Existing widgets can keep local QSS while they are migrated. New base
    widgets should use these object names.
    """
    return f"""
        QWidget {{
            {_font("body")}
            color: {COLORS["text"]};
            background-color: {COLORS["bg"]};
        }}

        QLabel[role="heading"] {{
            {_font("heading")}
            color: {COLORS["text"]};
        }}

        QLabel[role="section"] {{
            {_font("section")}
            color: {COLORS["text_muted"]};
        }}

        QLabel[role="caption"] {{
            {_font("caption")}
            color: {COLORS["text_subtle"]};
        }}

        #PrimaryButton, #SecondaryButton, #DangerButton {{
            {_font("button")}
            border: none;
            border-radius: {RADIUS["md"]}px;
            padding: {SPACING["sm"]}px {SPACING["lg"]}px;
            min-height: 20px;
        }}

        #PrimaryButton {{
            background-color: {COLORS["primary"]};
            color: {COLORS["primary_fg"]};
        }}
        #PrimaryButton:hover {{
            background-color: {COLORS["primary_hover"]};
        }}
        #PrimaryButton:pressed {{
            background-color: {COLORS["primary_pressed"]};
        }}
        #PrimaryButton:disabled {{
            background-color: {COLORS["disabled_bg"]};
            color: {COLORS["disabled_fg"]};
        }}

        #SecondaryButton {{
            background-color: {COLORS["secondary"]};
            color: {COLORS["text"]};
        }}
        #SecondaryButton:hover {{
            background-color: {COLORS["secondary_hover"]};
        }}
        #SecondaryButton:pressed {{
            background-color: {COLORS["secondary_pressed"]};
        }}
        #SecondaryButton:disabled {{
            background-color: {COLORS["disabled_bg"]};
            color: {COLORS["disabled_fg"]};
        }}

        #DangerButton {{
            background-color: {COLORS["danger"]};
            color: {COLORS["primary_fg"]};
        }}
        #DangerButton:hover {{
            background-color: {COLORS["danger_hover"]};
        }}
        #DangerButton:pressed {{
            background-color: {COLORS["danger_pressed"]};
        }}
        #DangerButton:disabled {{
            background-color: {COLORS["disabled_bg"]};
            color: {COLORS["disabled_fg"]};
        }}

        #IconButton {{
            background-color: transparent;
            border: none;
            border-radius: {RADIUS["md"]}px;
            padding: 0;
        }}
        #IconButton:hover {{
            background-color: {COLORS["secondary"]};
        }}
        #IconButton:pressed {{
            background-color: {COLORS["secondary_pressed"]};
        }}
        #IconButton:disabled {{
            background-color: transparent;
        }}

        #DialogPanel {{
            background-color: {COLORS["surface_raised"]};
            border: 1px solid {COLORS["border"]};
            border-radius: {RADIUS["xl"]}px;
        }}

        QLineEdit, QComboBox, QTextEdit, QPlainTextEdit {{
            {_font("body")}
            background-color: {COLORS["surface_subtle"]};
            color: {COLORS["text"]};
            border: 1px solid {COLORS["border"]};
            border-radius: {RADIUS["md"]}px;
            padding: {SPACING["sm"]}px {SPACING["md"]}px;
            selection-background-color: {COLORS["primary"]};
            selection-color: {COLORS["primary_fg"]};
        }}

        QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {COLORS["focus"]};
        }}

        QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled,
        QPlainTextEdit:disabled {{
            background-color: {COLORS["disabled_bg"]};
            color: {COLORS["disabled_fg"]};
        }}
    """
