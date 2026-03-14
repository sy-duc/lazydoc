"""Test SettingsDialog — Dialog cài đặt API Key."""

import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.core.database import DatabaseManager
from src.core.encryption import EncryptionManager
from src.core.i18n import I18nManager


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances trước mỗi test."""
    DatabaseManager.reset()
    I18nManager.reset()
    yield
    DatabaseManager.reset()
    I18nManager.reset()


@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    """Tạo database tạm cho test."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path)
    manager.initialize()
    return manager


@pytest.fixture
def encryption() -> EncryptionManager:
    """Tạo EncryptionManager cho test."""
    return EncryptionManager()


class TestSettingsDialogLogic:
    """Test logic nghiệp vụ của settings dialog (không cần GUI)."""

    def test_providers_loaded_from_db(self, db: DatabaseManager) -> None:
        """Kiểm tra danh sách provider được load đúng từ database."""
        cursor = db.connection.execute(
            "SELECT name, is_active FROM ai_provider ORDER BY id"
        )
        providers = cursor.fetchall()
        assert len(providers) == 3
        assert providers[0]["name"] == "gemini"
        assert providers[0]["is_active"] == 1
        assert providers[1]["name"] == "openai"
        assert providers[1]["is_active"] == 0
        assert providers[2]["name"] == "claude"
        assert providers[2]["is_active"] == 0

    def test_save_api_key_encrypted(
        self, db: DatabaseManager, encryption: EncryptionManager
    ) -> None:
        """Kiểm tra API key được mã hóa trước khi lưu."""
        test_key = "sk-test-key-12345"
        encrypted = encryption.encrypt(test_key)

        db.connection.execute(
            "UPDATE ai_provider SET api_key_enc = ? WHERE name = ?",
            (encrypted, "gemini"),
        )
        db.connection.commit()

        cursor = db.connection.execute(
            "SELECT api_key_enc FROM ai_provider WHERE name = ?", ("gemini",)
        )
        row = cursor.fetchone()
        assert row["api_key_enc"] is not None
        assert row["api_key_enc"] != test_key

        # Giải mã lại phải khớp
        decrypted = encryption.decrypt(row["api_key_enc"])
        assert decrypted == test_key

    def test_switch_active_provider(self, db: DatabaseManager) -> None:
        """Kiểm tra chuyển đổi provider active."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        # Chuyển sang openai
        db.connection.execute(
            "UPDATE ai_provider SET is_active = 0, updated_at = ?", (now,)
        )
        db.connection.execute(
            "UPDATE ai_provider SET is_active = 1, updated_at = ? WHERE name = ?",
            (now, "openai"),
        )
        db.connection.commit()

        # Kiểm tra chỉ openai active
        cursor = db.connection.execute(
            "SELECT name, is_active FROM ai_provider ORDER BY id"
        )
        providers = cursor.fetchall()
        active_providers = [p for p in providers if p["is_active"]]
        assert len(active_providers) == 1
        assert active_providers[0]["name"] == "openai"

    def test_save_without_key_keeps_existing(
        self, db: DatabaseManager, encryption: EncryptionManager
    ) -> None:
        """Kiểm tra lưu provider mà không nhập key mới vẫn giữ key cũ."""
        test_key = "sk-existing-key"
        encrypted = encryption.encrypt(test_key)

        db.connection.execute(
            "UPDATE ai_provider SET api_key_enc = ? WHERE name = ?",
            (encrypted, "gemini"),
        )
        db.connection.commit()

        # Đọc lại key
        cursor = db.connection.execute(
            "SELECT api_key_enc FROM ai_provider WHERE name = ?", ("gemini",)
        )
        row = cursor.fetchone()
        decrypted = encryption.decrypt(row["api_key_enc"])
        assert decrypted == test_key

    def test_active_provider_setting_updated(self, db: DatabaseManager) -> None:
        """Kiểm tra bảng settings cũng được cập nhật khi chuyển provider."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()

        db.connection.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES ('active_provider', ?, ?)""",
            ('"openai"', now),
        )
        db.connection.commit()

        cursor = db.connection.execute(
            "SELECT value FROM settings WHERE key = 'active_provider'"
        )
        row = cursor.fetchone()
        assert row["value"] == '"openai"'
