"""Test cho I18nManager."""

import pytest
from src.core.i18n import I18nManager


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton trước mỗi test."""
    I18nManager.reset()
    yield
    I18nManager.reset()


def test_load_vietnamese() -> None:
    """Load ngôn ngữ tiếng Việt mặc định."""
    i18n = I18nManager()
    assert i18n.current_language == "vi"
    assert i18n.t("app.name") == "LazyDoc"


def test_load_english() -> None:
    """Load ngôn ngữ tiếng Anh."""
    i18n = I18nManager(language="en")
    assert i18n.current_language == "en"
    assert i18n.t("app.title") == "LazyDoc — Document Blender"


def test_missing_key_returns_key() -> None:
    """Trả về key gốc khi không tìm thấy translation."""
    i18n = I18nManager()
    assert i18n.t("nonexistent.key") == "nonexistent.key"


def test_switch_language() -> None:
    """Chuyển đổi ngôn ngữ runtime."""
    i18n = I18nManager(language="vi")
    assert i18n.t("main.btn_grind") == "Xay"

    i18n.set_language("en")
    assert i18n.t("main.btn_grind") == "Grind"
    assert i18n.current_language == "en"


def test_nested_dot_notation() -> None:
    """Tra cứu key lồng nhau bằng dot notation."""
    i18n = I18nManager()
    assert i18n.t("status.done") == "Hoàn tất"
