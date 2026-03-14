"""Test cho DatabaseManager."""

import pytest
from pathlib import Path
from src.core.database import DatabaseManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton trước mỗi test."""
    DatabaseManager.reset()
    yield
    DatabaseManager.reset()


@pytest.fixture
def db(tmp_path: Path) -> DatabaseManager:
    """Tạo DatabaseManager với database tạm."""
    db_path = tmp_path / "test.db"
    manager = DatabaseManager(db_path=db_path)
    manager.initialize()
    return manager


def test_tables_created(db: DatabaseManager) -> None:
    """Kiểm tra các bảng được tạo đúng."""
    cursor = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert "ai_provider" in tables
    assert "glossary" in tables
    assert "settings" in tables
    assert "schema_version" in tables


def test_default_providers(db: DatabaseManager) -> None:
    """Kiểm tra 3 provider mặc định được tạo."""
    cursor = db.connection.execute("SELECT name, is_active FROM ai_provider ORDER BY name")
    providers = {row[0]: row[1] for row in cursor.fetchall()}
    assert providers == {"claude": 0, "gemini": 1, "openai": 0}


def test_default_settings(db: DatabaseManager) -> None:
    """Kiểm tra settings mặc định."""
    cursor = db.connection.execute("SELECT key, value FROM settings ORDER BY key")
    settings = {row[0]: row[1] for row in cursor.fetchall()}
    assert settings["app_language"] == '"vi"'
    assert settings["active_provider"] == '"gemini"'


def test_schema_version(db: DatabaseManager) -> None:
    """Kiểm tra schema version = 1 sau migration."""
    cursor = db.connection.execute("SELECT MAX(version) FROM schema_version")
    assert cursor.fetchone()[0] == 1


def test_idempotent_initialize(db: DatabaseManager) -> None:
    """Gọi initialize lần 2 không lỗi."""
    db.initialize()  # Lần 2
    cursor = db.connection.execute("SELECT COUNT(*) FROM ai_provider")
    assert cursor.fetchone()[0] == 3  # Vẫn chỉ 3 provider
