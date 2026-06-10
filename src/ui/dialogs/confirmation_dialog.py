"""ConfirmationDialog — Dialog xác nhận trước khi xử lý nhiều lượt API."""

import logging

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

from src.core.config import ConfigManager
from src.core.cost_estimator import CostEstimate
from src.ui import theme

logger = logging.getLogger(__name__)

_SHADOW_MARGIN = 16


class ConfirmationDialog(QDialog):
    """Dialog xác nhận khi tác vụ cần nhiều lượt gọi API."""

    def __init__(
        self,
        estimate: CostEstimate,
        mode: str = "summary",
        parent: QWidget | None = None,
    ) -> None:
        """Khởi tạo ConfirmationDialog.

        Args:
            estimate: Kết quả ước tính số lượt API call.
            mode: "summary" hoặc "translate" (ảnh hưởng title).
            parent: Widget cha.
        """
        super().__init__(parent)
        self._estimate = estimate
        self._mode = mode
        self._setup_window()
        self._setup_ui()
        self._setup_style()

    def _setup_window(self) -> None:
        self.setWindowTitle("Xác nhận xử lý")
        m = _SHADOW_MARGIN * 2
        self.setMinimumWidth(380 + m)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(
            _SHADOW_MARGIN, _SHADOW_MARGIN,
            _SHADOW_MARGIN, _SHADOW_MARGIN,
        )

        self._panel = QWidget()
        self._panel.setObjectName("cfmPanel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 130))
        self._panel.setGraphicsEffect(shadow)
        outer.addWidget(self._panel)

        layout = QVBoxLayout(self._panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # Tiêu đề
        title_text = "Xác nhận tổng hợp" if self._mode == "summary" else "Xác nhận dịch thuật"
        title = QLabel(title_text)
        title.setObjectName("cfmTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(self._make_sep())

        # Thông tin
        e = self._estimate
        layout.addWidget(self._make_row("Số file:", f"{e.file_count} file"))
        if e.image_count > 0:
            layout.addWidget(self._make_row(
                "Số ảnh:", f"{e.image_count}  (gọi vision API riêng)"
            ))
        layout.addWidget(self._make_row("Số lượt gọi API:", f"~{e.api_calls} lượt"))

        layout.addWidget(self._make_sep())

        # Cảnh báo
        warn = QLabel("⚠  Tác vụ này cần nhiều lượt gọi API và có thể mất đến vài phút. Xác nhận tiếp tục?")
        warn.setObjectName("cfmWarn")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        # Ghi chú stop
        note = QLabel("💡  Lưu ý: Sau khi xác nhận tiếp tục, bạn vẫn có thể dừng bất cứ lúc nào.")
        note.setObjectName("cfmNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Nút
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        cancel_btn = QPushButton("Hủy")
        cancel_btn.setObjectName("cfmCancelBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Tiếp tục")
        ok_btn.setObjectName("cfmOkBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _setup_style(self) -> None:
        self.setStyleSheet(f"""
            ConfirmationDialog {{
                background-color: transparent;
            }}
            #cfmPanel {{
                background-color: {theme.BG_MANTLE};
                border: 1px solid {theme.SURFACE_1};
                border-radius: {theme.RADIUS_LG}px;
            }}
            #cfmTitle {{
                color: {theme.TEXT};
                font-size: {theme.FONT_LG}px;
                font-weight: bold;
            }}
            QLabel#cfmRow {{
                color: {theme.TEXT};
                font-size: {theme.FONT_MD}px;
            }}
            #cfmWarn {{
                color: {theme.YELLOW};
                font-size: {theme.FONT_SM}px;
            }}
            #cfmNote {{
                color: {theme.SUBTEXT_0};
                font-size: {theme.FONT_SM}px;
            }}
            #cfmOkBtn {{
                background-color: {theme.BLUE};
                color: {theme.BG_BASE};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #cfmOkBtn:hover {{ background-color: {theme.SAPPHIRE}; }}
            #cfmCancelBtn {{
                background-color: {theme.SURFACE_1};
                color: {theme.TEXT};
                border: none;
                border-radius: {theme.RADIUS_MD}px;
                padding: 8px 24px;
                font-size: {theme.FONT_MD}px;
                font-weight: bold;
            }}
            #cfmCancelBtn:hover {{ background-color: {theme.SURFACE_2}; }}
            QWidget#cfmSep {{
                background-color: {theme.SURFACE_0};
            }}
        """)

    def _make_row(self, label: str, value: str) -> QLabel:
        lbl = QLabel(f"<b>{label}</b>&nbsp;&nbsp;{value}")
        lbl.setObjectName("cfmRow")
        return lbl

    def _make_sep(self) -> QWidget:
        sep = QWidget()
        sep.setObjectName("cfmSep")
        sep.setFixedHeight(1)
        return sep

    @staticmethod
    def should_skip(estimate: CostEstimate) -> bool:
        """Trả về True nếu không cần hiển thị dialog.

        Dùng weighted score: vision call nặng hơn text call.
        Score = text_calls * 1 + image_calls * vision_weight.

        Args:
            estimate: CostEstimate cần kiểm tra.

        Returns:
            True nếu tác vụ nhỏ, không cần xác nhận.
        """
        config = ConfigManager()
        if not config.get("confirmation.enabled", True):
            return True
        min_calls = config.get("confirmation.min_api_calls", 5)
        vision_weight = config.get("confirmation.vision_weight", 2)
        text_calls = estimate.api_calls - estimate.image_count
        weighted = text_calls + estimate.image_count * vision_weight
        return weighted < min_calls
