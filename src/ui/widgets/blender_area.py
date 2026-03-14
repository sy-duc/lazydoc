"""BlenderArea — Vùng hoạt ảnh máy xay tài liệu + drag & drop."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.core.i18n import I18nManager


class BlenderArea(QWidget):
    """Vùng hiển thị hoạt ảnh máy xay + khu vực kéo thả file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Khởi tạo BlenderArea."""
        super().__init__(parent)
        self._i18n = I18nManager()
        self._is_hovering = False
        self.setObjectName("blenderArea")
        self._setup_ui()
        self._apply_style()

    def _setup_ui(self) -> None:
        """Thiết lập layout vùng máy xay."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon máy xay (placeholder — sẽ thay bằng animation sau)
        self._blender_icon = QLabel("🔄")
        self._blender_icon.setObjectName("blenderIcon")
        self._blender_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._blender_icon)

        # Nhãn hướng dẫn kéo thả
        self._drop_label = QLabel(self._i18n.t("main.drag_drop"))
        self._drop_label.setObjectName("dropLabel")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setWordWrap(True)
        layout.addWidget(self._drop_label)

        # Nhãn trạng thái xử lý (ẩn khi không xử lý)
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.hide()
        layout.addWidget(self._status_label)

    def _apply_style(self) -> None:
        """Áp dụng stylesheet mặc định."""
        self._update_style()

    def _update_style(self) -> None:
        """Cập nhật style dựa trên trạng thái hover."""
        border_color = "#89b4fa" if self._is_hovering else "#585b70"
        bg_color = "#1e1e2e" if not self._is_hovering else "#252540"
        self.setStyleSheet(f"""
            #blenderArea {{
                background-color: {bg_color};
                border: 2px dashed {border_color};
                border-radius: 12px;
                min-height: 180px;
            }}
            #blenderIcon {{
                font-size: 48px;
                color: #89b4fa;
                background: transparent;
                border: none;
            }}
            #dropLabel {{
                color: #a6adc8;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
            #statusLabel {{
                color: #a6e3a1;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)

    def set_drag_hover(self, hovering: bool) -> None:
        """Cập nhật trạng thái khi đang kéo file qua vùng này.

        Args:
            hovering: True nếu đang hover, False nếu không.
        """
        self._is_hovering = hovering
        self._update_style()

    def set_status(self, text: str) -> None:
        """Hiển thị trạng thái xử lý (Extracting..., Blending..., v.v.).

        Args:
            text: Nội dung trạng thái.
        """
        if text:
            self._status_label.setText(text)
            self._status_label.show()
            self._drop_label.hide()
        else:
            self._status_label.hide()
            self._drop_label.show()

    def reset(self) -> None:
        """Reset về trạng thái ban đầu."""
        self._status_label.hide()
        self._drop_label.show()
        self._is_hovering = False
        self._update_style()
