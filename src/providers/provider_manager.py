"""ProviderManager — Quản lý vòng đời AI Provider."""

import logging
from datetime import datetime, timezone

from PySide6.QtCore import QObject, Signal

from src.core.database import DatabaseManager
from src.core.encryption import EncryptionManager
from src.core.logging_config import sanitize_error
from src.providers.base import BaseProvider
from src.providers.claude_provider import ClaudeProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.openai_provider import OpenAIProvider
from src.providers.token_counter import TokenCounter

logger = logging.getLogger(__name__)

# Mapping tên provider → class
PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
}


class ProviderManager(QObject):
    """Quản lý khởi tạo, chuyển đổi, và validate AI Provider.

    Chịu trách nhiệm:
    - Load provider đang active từ database.
    - Chuyển đổi provider tại runtime.
    - Validate API key.
    - Quản lý TokenCounter cho theo dõi chi phí.

    Signals:
        provider_changed: Phát khi provider active thay đổi (str tên provider mới).
        validation_result: Phát kết quả validate key (bool hợp lệ, str thông báo).
    """

    provider_changed = Signal(str)
    validation_result = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        """Khởi tạo ProviderManager."""
        super().__init__(parent)
        self._db = DatabaseManager()
        self._encryption = EncryptionManager()
        self._token_counter = TokenCounter(self)
        self._current_provider: BaseProvider | None = None
        self._current_provider_name: str = ""

    @property
    def provider(self) -> BaseProvider | None:
        """Provider đang active. None nếu chưa khởi tạo hoặc không có key."""
        return self._current_provider

    @property
    def provider_name(self) -> str:
        """Tên provider đang active."""
        return self._current_provider_name

    @property
    def token_counter(self) -> TokenCounter:
        """TokenCounter để theo dõi chi phí."""
        return self._token_counter

    def load_active_provider(self) -> bool:
        """Load provider đang active từ database.

        Returns:
            True nếu load thành công, False nếu không có key hoặc lỗi.
        """
        cursor = self._db.connection.execute(
            "SELECT name, api_key_enc FROM ai_provider WHERE is_active = 1"
        )
        row = cursor.fetchone()

        if not row:
            logger.warning("Không tìm thấy provider active trong database.")
            return False

        provider_name = row["name"]
        api_key_enc = row["api_key_enc"]

        if not api_key_enc:
            logger.info("Provider '%s' chưa có API key.", provider_name)
            self._current_provider_name = provider_name
            self._current_provider = None
            return False

        return self._init_provider(provider_name, api_key_enc)

    def switch_provider(self, provider_name: str) -> bool:
        """Chuyển đổi sang provider khác.

        Args:
            provider_name: Tên provider (gemini, openai, claude).

        Returns:
            True nếu chuyển thành công.
        """
        if provider_name not in PROVIDER_CLASSES:
            logger.error("Provider không hỗ trợ: %s", provider_name)
            return False

        # Lấy API key từ database
        cursor = self._db.connection.execute(
            "SELECT api_key_enc FROM ai_provider WHERE name = ?",
            (provider_name,),
        )
        row = cursor.fetchone()

        if not row or not row["api_key_enc"]:
            logger.warning("Provider '%s' chưa có API key.", provider_name)
            return False

        # Cập nhật active trong database
        now = datetime.now(timezone.utc).isoformat()
        conn = self._db.connection
        conn.execute("UPDATE ai_provider SET is_active = 0, updated_at = ?", (now,))
        conn.execute(
            "UPDATE ai_provider SET is_active = 1, updated_at = ? WHERE name = ?",
            (now, provider_name),
        )
        conn.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES ('active_provider', ?, ?)""",
            (f'"{provider_name}"', now),
        )
        conn.commit()

        success = self._init_provider(provider_name, row["api_key_enc"])
        if success:
            self.provider_changed.emit(provider_name)

        return success

    def validate_api_key(self, provider_name: str, api_key: str) -> bool:
        """Validate API key bằng cách tạo provider tạm và gọi validate.

        Args:
            provider_name: Tên provider.
            api_key: API key plaintext cần validate.

        Returns:
            True nếu key hợp lệ.
        """
        provider_cls = PROVIDER_CLASSES.get(provider_name)
        if not provider_cls:
            self.validation_result.emit(False, f"Provider không hỗ trợ: {provider_name}")
            return False

        try:
            temp_provider = provider_cls(api_key)
            is_valid = temp_provider.validate_key()

            if is_valid:
                self.validation_result.emit(True, f"API key {provider_name} hợp lệ.")
            else:
                self.validation_result.emit(False, f"API key {provider_name} không hợp lệ.")

            return is_valid
        except Exception as e:
            msg = f"Lỗi validate key {provider_name}: {sanitize_error(e)}"
            logger.error(msg)
            self.validation_result.emit(False, msg)
            return False

    def get_provider_status(self) -> list[dict]:
        """Lấy trạng thái tất cả provider.

        Returns:
            Danh sách dict với keys: name, has_key, is_active.
        """
        cursor = self._db.connection.execute(
            "SELECT name, api_key_enc, is_active FROM ai_provider ORDER BY id"
        )
        result = []
        for row in cursor.fetchall():
            result.append({
                "name": row["name"],
                "has_key": bool(row["api_key_enc"]),
                "is_active": bool(row["is_active"]),
            })
        return result

    def _init_provider(self, provider_name: str, api_key_enc: str) -> bool:
        """Khởi tạo provider instance từ tên và encrypted key.

        Args:
            provider_name: Tên provider.
            api_key_enc: API key đã mã hóa.

        Returns:
            True nếu khởi tạo thành công.
        """
        provider_cls = PROVIDER_CLASSES.get(provider_name)
        if not provider_cls:
            logger.error("Provider không hỗ trợ: %s", provider_name)
            return False

        try:
            api_key = self._encryption.decrypt(api_key_enc)
            self._current_provider = provider_cls(api_key)
            self._current_provider_name = provider_name
            logger.info("Đã khởi tạo provider: %s (model: %s)",
                        provider_name, self._current_provider.model)
            return True
        except Exception as e:
            logger.error(
                "Không thể khởi tạo provider '%s': %s",
                provider_name,
                sanitize_error(e),
            )
            self._current_provider = None
            self._current_provider_name = provider_name
            return False
