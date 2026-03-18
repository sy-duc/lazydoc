"""SettingsDialog — Dialog cài đặt API Key cho AI Provider."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.database import DatabaseManager
from src.core.encryption import EncryptionManager
from src.core.i18n import I18nManager
from src.providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)

# Tên hiển thị của provider
PROVIDER_DISPLAY_NAMES = {
    "gemini": "Gemini",
    "openai": "OpenAI",
    "claude": "Claude",
}


class SettingsDialog(QDialog):
    """Dialog cài đặt API Key cho AI Provider."""

    def __init__(
        self,
        parent: QWidget | None = None,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        """Khởi tạo SettingsDialog.

        Args:
            parent: Widget cha.
            provider_manager: ProviderManager để validate key và chuyển đổi provider.
        """
        super().__init__(parent)
        self._i18n = I18nManager()
        self._db = DatabaseManager()
        self._encryption = EncryptionManager()
        self._provider_manager = provider_manager
        self._providers: list[dict] = []
        self._setup_window()
        self._setup_ui()
        self._setup_style()
        self._load_providers()

    def _setup_window(self) -> None:
        """Cấu hình dialog."""
        self.setWindowTitle(self._i18n.t("settings.title"))
        self.setFixedSize(460, 300)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setModal(True)

    def _setup_ui(self) -> None:
        """Thiết lập layout và các widget."""
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(20, 20, 20, 20)

        self._panel = QWidget()
        self._panel.setObjectName("panel")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self._panel.setGraphicsEffect(shadow)
        outer_layout.addWidget(self._panel)

        layout = QVBoxLayout(self._panel)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Tiêu đề dialog
        title_label = QLabel(self._i18n.t("settings.title"))
        title_label.setObjectName("dialogTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Label provider hiện tại
        self._current_provider_label = QLabel()
        self._current_provider_label.setObjectName("currentProvider")
        self._current_provider_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._current_provider_label)

        # Selectbox chọn provider
        provider_row = QHBoxLayout()
        provider_row.setSpacing(10)
        provider_lbl = QLabel(self._i18n.t("settings.select_provider"))
        provider_lbl.setFixedWidth(100)
        self._provider_combo = QComboBox()
        self._provider_combo.setObjectName("providerCombo")
        self._provider_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(provider_lbl)
        provider_row.addWidget(self._provider_combo, stretch=1)
        layout.addLayout(provider_row)

        # Trường nhập API key
        key_row = QHBoxLayout()
        key_row.setSpacing(10)
        key_lbl = QLabel(self._i18n.t("settings.api_key_label"))
        key_lbl.setFixedWidth(100)
        self._key_input = QLineEdit()
        self._key_input.setObjectName("keyInput")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("sk-...")
        key_row.addWidget(key_lbl)
        key_row.addWidget(self._key_input, stretch=1)
        layout.addLayout(key_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self._cancel_btn = QPushButton(self._i18n.t("settings.btn_cancel"))
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        self._save_btn = QPushButton(self._i18n.t("settings.btn_save"))
        self._save_btn.setObjectName("saveBtn")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)

        layout.addLayout(btn_row)

    def _setup_style(self) -> None:
        """Áp dụng stylesheet cho dialog."""
        arrow_icon = Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "dropdown_arrow.svg"
        arrow_url = arrow_icon.as_posix()
        self.setStyleSheet("""
            SettingsDialog {
                background-color: #11111b;
            }
            #panel {
                background-color: #262640;
                border: 1px solid #585b70;
                border-radius: 10px;
            }
            #dialogTitle {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
            }
            #currentProvider {
                color: #a6adc8;
                font-size: 12px;
            }
            QLabel {
                color: #cdd6f4;
                font-size: 13px;
            }
            #providerCombo {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #providerCombo::drop-down {
                border: none;
                width: 24px;
            }
            #providerCombo::down-arrow {
                image: url(__ARROW_URL__);
                width: 10px;
                height: 6px;
                margin-right: 8px;
            }
            #providerCombo QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                selection-background-color: #45475a;
                outline: none;
            }
            #keyInput {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            #keyInput:focus {
                border: 1px solid #89b4fa;
            }
            #saveBtn {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #saveBtn:hover {
                background-color: #94e2d5;
            }
            #saveBtn:pressed {
                background-color: #74c7ec;
            }
            #cancelBtn {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: bold;
            }
            #cancelBtn:hover {
                background-color: #585b70;
            }
            QMessageBox {
                background-color: #e0e0e0;
            }
            QMessageBox QLabel {
                color: #1e1e2e;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                min-width: 60px;
            }
        """.replace("__ARROW_URL__", arrow_url))

    def _load_providers(self) -> None:
        """Đọc danh sách provider từ database và hiển thị."""
        cursor = self._db.connection.execute(
            "SELECT id, name, api_key_enc, is_active FROM ai_provider ORDER BY id"
        )
        self._providers = [dict(row) for row in cursor.fetchall()]

        # Tìm provider đang active
        active_name = ""
        active_index = 0
        for i, provider in enumerate(self._providers):
            display_name = PROVIDER_DISPLAY_NAMES.get(provider["name"], provider["name"])
            self._provider_combo.addItem(display_name, provider["name"])
            if provider["is_active"]:
                active_name = display_name
                active_index = i

        # Hiển thị provider hiện tại
        self._current_provider_label.setText(
            f"{self._i18n.t('settings.provider_label')}: {active_name}"
        )

        # Chọn provider đang active trong combobox
        self._provider_combo.setCurrentIndex(active_index)

    def _on_provider_changed(self, index: int) -> None:
        """Xử lý khi người dùng chọn provider khác trong combobox.

        Args:
            index: Index của provider được chọn.
        """
        if index < 0 or index >= len(self._providers):
            return

        provider = self._providers[index]
        # Hiển thị masked key nếu đã có
        if provider["api_key_enc"]:
            try:
                decrypted = self._encryption.decrypt(provider["api_key_enc"])
                # Hiển thị 4 ký tự cuối, che phần còn lại
                masked = "***" + decrypted[-4:] if len(decrypted) > 4 else "***"
                self._key_input.setPlaceholderText(masked)
            except Exception:
                self._key_input.setPlaceholderText("sk-...")
        else:
            self._key_input.setPlaceholderText("sk-...")

        # Xóa input để người dùng nhập key mới (nếu muốn)
        self._key_input.clear()

    def _on_save(self) -> None:
        """Xử lý khi người dùng bấm nút Lưu.

        Luồng xử lý:
        1. Validate input (key không trống).
        2. Nếu có key mới → validate bằng cách gọi API thật.
        3. Lưu key mã hóa vào DB.
        4. Chuyển đổi provider active.
        5. Reload ProviderManager để sử dụng provider mới.
        """
        index = self._provider_combo.currentIndex()
        if index < 0:
            return

        provider = self._providers[index]
        new_key = self._key_input.text().strip()

        # Validation: key trống và chưa có key cũ
        if not new_key and not provider["api_key_enc"]:
            QMessageBox.warning(
                self,
                self._i18n.t("settings.title"),
                self._i18n.t("settings.validation_empty"),
            )
            self._key_input.setFocus()
            return

        # Validate API key mới bằng cách gọi API thật
        if new_key and self._provider_manager:
            self._save_btn.setEnabled(False)
            self._save_btn.setText(self._i18n.t("settings.validating"))
            self._save_btn.repaint()

            is_valid = self._provider_manager.validate_api_key(
                provider["name"], new_key
            )

            self._save_btn.setEnabled(True)
            self._save_btn.setText(self._i18n.t("settings.btn_save"))

            if not is_valid:
                QMessageBox.warning(
                    self,
                    self._i18n.t("settings.title"),
                    self._i18n.t("settings.validation_failed"),
                )
                self._key_input.setFocus()
                return

        now = datetime.now(timezone.utc).isoformat()
        conn = self._db.connection

        # Cập nhật API key nếu người dùng nhập key mới
        if new_key:
            encrypted_key = self._encryption.encrypt(new_key)
            conn.execute(
                "UPDATE ai_provider SET api_key_enc = ?, updated_at = ? WHERE id = ?",
                (encrypted_key, now, provider["id"]),
            )
            # Cập nhật cache local
            provider["api_key_enc"] = encrypted_key
            logger.info("Đã cập nhật API key cho provider: %s", provider["name"])

        # Chuyển đổi provider active
        conn.execute("UPDATE ai_provider SET is_active = 0, updated_at = ?", (now,))
        conn.execute(
            "UPDATE ai_provider SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, provider["id"]),
        )
        # Cập nhật settings
        conn.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES ('active_provider', ?, ?)""",
            (f'"{provider["name"]}"', now),
        )
        conn.commit()

        # Cập nhật cache local
        for p in self._providers:
            p["is_active"] = 1 if p["id"] == provider["id"] else 0

        display_name = PROVIDER_DISPLAY_NAMES.get(provider["name"], provider["name"])
        self._current_provider_label.setText(
            f"{self._i18n.t('settings.provider_label')}: {display_name}"
        )

        # Reload ProviderManager để sử dụng provider mới ngay lập tức
        if self._provider_manager:
            self._provider_manager.load_active_provider()

        logger.info("Đã chuyển provider active sang: %s", provider["name"])

        QMessageBox.information(
            self,
            self._i18n.t("settings.title"),
            self._i18n.t("settings.save_success"),
        )
        self.accept()
