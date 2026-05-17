"""MessageDialog — Custom styled dialog thay thế QMessageBox."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui import theme


class MessageDialog(QDialog):
    """Dialog thông báo có style đồng bộ với UI Catppuccin Mocha."""

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        text: str,
        dialog_type: str = "info",
        buttons: str = "ok",
    ) -> None:
        super().__init__(parent)
        self._confirmed = False
        self._dialog_type = dialog_type
        self._buttons = buttons
        self._title = title
        self._text = text
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        self.setMinimumWidth(340)
        self.setMaximumWidth(480)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)

        panel = QWidget()
        panel.setObjectName("msgPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 140))
        panel.setGraphicsEffect(shadow)
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header: icon + title
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        icon_label = QLabel()
        icon_name, icon_color = self._icon_config()
        icon_label.setPixmap(theme.pixmap(icon_name, icon_color, 20))
        header_row.addWidget(icon_label)
        title_label = QLabel(self._title)
        title_label.setObjectName("msgTitle")
        header_row.addWidget(title_label, stretch=1)
        layout.addLayout(header_row)

        # Separator
        sep = QWidget()
        sep.setObjectName("msgSep")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Message
        msg_label = QLabel(self._text)
        msg_label.setObjectName("msgText")
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(msg_label)

        layout.addSpacing(4)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.setSpacing(8)

        if self._buttons == "yesno":
            no_btn = QPushButton("Không")
            no_btn.setObjectName("msgBtnSecondary")
            no_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            no_btn.clicked.connect(self.reject)
            btn_row.addWidget(no_btn)

            yes_btn = QPushButton("Có")
            yes_btn.setObjectName("msgBtnPrimary")
            yes_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            yes_btn.clicked.connect(self._on_yes)
            btn_row.addWidget(yes_btn)
        else:
            ok_btn = QPushButton("OK")
            ok_btn.setObjectName("msgBtnPrimary")
            ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            ok_btn.clicked.connect(self.accept)
            btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _icon_config(self) -> tuple[str, str]:
        mapping = {
            "info": ("information-outline", theme.BLUE),
            "warning": ("alert-outline", theme.YELLOW),
            "error": ("close-circle-outline", theme.RED),
            "question": ("help-circle-outline", theme.MAUVE),
        }
        return mapping.get(self._dialog_type, ("information-outline", theme.BLUE))

    def _on_yes(self) -> None:
        self._confirmed = True
        self.accept()

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            MessageDialog {{
                background-color: {theme.BG_CRUST};
            }}
            #msgPanel {{
                background-color: {theme.SURFACE_0};
                border: 1px solid {theme.SURFACE_2};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #msgTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #msgSep {{
                background-color: {theme.SURFACE_1};
            }}
            #msgText {{
                color: {theme.SUBTEXT_1};
                font-size: {theme.FONT_SM}px;
            }}
            #msgBtnPrimary {{
                background-color: {theme.MAUVE};
                color: {theme.BG_BASE};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
                min-width: 80px;
            }}
            #msgBtnPrimary:hover {{ background-color: {theme.LAVENDER}; }}
            #msgBtnPrimary:pressed {{ background-color: {theme.BLUE}; }}
            #msgBtnSecondary {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: 1px solid {theme.SURFACE_2};
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_SM}px;
                font-weight: bold;
                min-width: 80px;
            }}
            #msgBtnSecondary:hover {{ background-color: {theme.SURFACE_2}; }}
        """)

    # --- Static helpers ---

    @staticmethod
    def information(parent: QWidget | None, title: str, text: str) -> None:
        MessageDialog(parent, title, text, "info", "ok").exec()

    @staticmethod
    def warning(parent: QWidget | None, title: str, text: str) -> None:
        MessageDialog(parent, title, text, "warning", "ok").exec()

    @staticmethod
    def critical(parent: QWidget | None, title: str, text: str) -> None:
        MessageDialog(parent, title, text, "error", "ok").exec()

    @staticmethod
    def question(parent: QWidget | None, title: str, text: str) -> bool:
        dlg = MessageDialog(parent, title, text, "question", "yesno")
        dlg.exec()
        return dlg._confirmed
