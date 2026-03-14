"""Test cho ConfigManager."""

import pytest
from pathlib import Path
from src.core.config import ConfigManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton trước mỗi test."""
    ConfigManager.reset()
    yield
    ConfigManager.reset()


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Tạo file config tạm để test."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "pricing:\n"
        "  gemini:\n"
        "    gemini-1.5-flash:\n"
        "      input: 0.075\n"
        "      output: 0.30\n"
        "chunking:\n"
        "  chunk_size: 100000\n"
        "  overlap_size: 500\n",
        encoding="utf-8",
    )
    return config_path


def test_load_config(config_file: Path) -> None:
    """Đọc config thành công."""
    config = ConfigManager(config_path=config_file)
    assert config.get("chunking.chunk_size") == 100000


def test_get_nested_key(config_file: Path) -> None:
    """Truy xuất key lồng nhau bằng dot notation."""
    config = ConfigManager(config_path=config_file)
    # Dot notation hoạt động khi key không chứa dấu chấm
    assert config.get("chunking.overlap_size") == 500
    # Key chứa dấu chấm (vd: "1.5") cần truy cập trực tiếp qua data
    assert config.data["pricing"]["gemini"]["gemini-1.5-flash"]["input"] == 0.075


def test_get_missing_key_returns_default(config_file: Path) -> None:
    """Trả về default khi key không tồn tại."""
    config = ConfigManager(config_path=config_file)
    assert config.get("nonexistent.key", "fallback") == "fallback"


def test_set_and_persist(config_file: Path) -> None:
    """Set giá trị và lưu vào file."""
    config = ConfigManager(config_path=config_file)
    config.set("chunking.chunk_size", 50000)
    assert config.get("chunking.chunk_size") == 50000

    # Đọc lại file để xác nhận đã persist
    ConfigManager.reset()
    config2 = ConfigManager(config_path=config_file)
    assert config2.get("chunking.chunk_size") == 50000


def test_missing_config_file(tmp_path: Path) -> None:
    """Không lỗi khi file config không tồn tại."""
    config = ConfigManager(config_path=tmp_path / "nonexistent.yaml")
    assert config.data == {}
    assert config.get("any.key") is None
