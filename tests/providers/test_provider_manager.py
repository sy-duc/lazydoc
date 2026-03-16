"""Test ProviderManager — Kiểm tra quản lý vòng đời provider."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.providers.provider_manager import ProviderManager, PROVIDER_CLASSES


@pytest.fixture
def in_memory_db():
    """Tạo database in-memory cho testing."""
    with patch("src.providers.provider_manager.DatabaseManager") as mock_db_cls:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        # Tạo schema
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            CREATE TABLE ai_provider (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                api_key_enc TEXT,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Chèn dữ liệu test
        providers = [
            ("gemini", "encrypted_gemini_key", 1),
            ("openai", None, 0),
            ("claude", "encrypted_claude_key", 0),
        ]
        for name, key, active in providers:
            conn.execute(
                "INSERT INTO ai_provider (name, api_key_enc, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, key, active, now, now),
            )
        conn.commit()

        db_instance = MagicMock()
        db_instance.connection = conn
        mock_db_cls.return_value = db_instance
        yield conn

        conn.close()


@pytest.fixture
def mock_encryption():
    """Mock EncryptionManager."""
    with patch("src.providers.provider_manager.EncryptionManager") as mock_cls:
        enc_instance = MagicMock()
        enc_instance.decrypt.return_value = "fake-api-key-12345"
        mock_cls.return_value = enc_instance
        yield enc_instance


@pytest.fixture
def mock_provider_classes():
    """Mock các provider class để không gọi API thật."""
    mock_providers = {}
    for name in ["gemini", "openai", "claude"]:
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_instance.name = name
        mock_instance.model = f"{name}-default"
        mock_instance.validate_key.return_value = True
        mock_cls.return_value = mock_instance
        mock_providers[name] = mock_cls

    with patch.dict(
        "src.providers.provider_manager.PROVIDER_CLASSES",
        mock_providers,
    ):
        yield mock_providers


@pytest.fixture
def manager(in_memory_db, mock_encryption, mock_provider_classes):
    """Tạo ProviderManager instance với mọi dependency đã mock."""
    return ProviderManager()


class TestLoadActiveProvider:
    """Test load_active_provider."""

    def test_load_success(self, manager: ProviderManager) -> None:
        result = manager.load_active_provider()
        assert result is True
        assert manager.provider is not None
        assert manager.provider_name == "gemini"

    def test_load_no_key(self, in_memory_db, mock_encryption, mock_provider_classes) -> None:
        # Xóa key của gemini
        in_memory_db.execute("UPDATE ai_provider SET api_key_enc = NULL WHERE name = 'gemini'")
        in_memory_db.commit()

        manager = ProviderManager()
        result = manager.load_active_provider()
        assert result is False
        assert manager.provider is None

    def test_load_no_active(self, in_memory_db, mock_encryption, mock_provider_classes) -> None:
        # Không có provider active
        in_memory_db.execute("UPDATE ai_provider SET is_active = 0")
        in_memory_db.commit()

        manager = ProviderManager()
        result = manager.load_active_provider()
        assert result is False


class TestSwitchProvider:
    """Test switch_provider."""

    def test_switch_success(self, manager: ProviderManager) -> None:
        result = manager.switch_provider("claude")
        assert result is True
        assert manager.provider_name == "claude"

    def test_switch_no_key(self, manager: ProviderManager) -> None:
        # OpenAI không có key
        result = manager.switch_provider("openai")
        assert result is False

    def test_switch_invalid_provider(self, manager: ProviderManager) -> None:
        result = manager.switch_provider("invalid_provider")
        assert result is False

    def test_switch_emits_signal(self, manager: ProviderManager) -> None:
        signals = []
        manager.provider_changed.connect(lambda name: signals.append(name))

        manager.switch_provider("claude")

        assert len(signals) == 1
        assert signals[0] == "claude"

    def test_switch_updates_database(self, manager: ProviderManager, in_memory_db) -> None:
        manager.switch_provider("claude")

        # Kiểm tra database đã cập nhật
        cursor = in_memory_db.execute(
            "SELECT name, is_active FROM ai_provider ORDER BY id"
        )
        rows = cursor.fetchall()
        active_providers = {r["name"]: r["is_active"] for r in rows}

        assert active_providers["gemini"] == 0
        assert active_providers["claude"] == 1


class TestValidateApiKey:
    """Test validate_api_key."""

    def test_valid_key(self, manager: ProviderManager, mock_provider_classes) -> None:
        result = manager.validate_api_key("gemini", "valid-key")
        assert result is True

    def test_invalid_key(self, manager: ProviderManager, mock_provider_classes) -> None:
        # Mock validate_key trả về False
        mock_provider_classes["openai"].return_value.validate_key.return_value = False
        result = manager.validate_api_key("openai", "invalid-key")
        assert result is False

    def test_invalid_provider(self, manager: ProviderManager) -> None:
        result = manager.validate_api_key("unknown", "key")
        assert result is False

    def test_emits_validation_signal(self, manager: ProviderManager) -> None:
        signals = []
        manager.validation_result.connect(
            lambda valid, msg: signals.append((valid, msg))
        )

        manager.validate_api_key("gemini", "test-key")

        assert len(signals) == 1
        assert signals[0][0] is True


class TestGetProviderStatus:
    """Test get_provider_status."""

    def test_returns_all_providers(self, manager: ProviderManager) -> None:
        status = manager.get_provider_status()
        assert len(status) == 3

        names = [s["name"] for s in status]
        assert "gemini" in names
        assert "openai" in names
        assert "claude" in names

    def test_has_key_flag(self, manager: ProviderManager) -> None:
        status = manager.get_provider_status()
        status_map = {s["name"]: s for s in status}

        assert status_map["gemini"]["has_key"] is True
        assert status_map["openai"]["has_key"] is False
        assert status_map["claude"]["has_key"] is True

    def test_is_active_flag(self, manager: ProviderManager) -> None:
        status = manager.get_provider_status()
        status_map = {s["name"]: s for s in status}

        assert status_map["gemini"]["is_active"] is True
        assert status_map["openai"]["is_active"] is False


class TestTokenCounter:
    """Test tích hợp với TokenCounter."""

    def test_has_token_counter(self, manager: ProviderManager) -> None:
        assert manager.token_counter is not None
