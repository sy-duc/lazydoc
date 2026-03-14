"""Test TranslateDialog — Dialog dịch thuật tài liệu."""

from pathlib import Path

import pytest

from src.core.i18n import I18nManager


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances trước mỗi test."""
    I18nManager.reset()
    yield
    I18nManager.reset()


class TestTranslateDialogLogic:
    """Test logic nghiệp vụ của translate dialog (không cần GUI)."""

    def test_target_languages_defined(self) -> None:
        """Kiểm tra danh sách ngôn ngữ đích được định nghĩa đúng."""
        from src.ui.dialogs.translate_dialog import TARGET_LANGUAGES

        codes = [code for code, _ in TARGET_LANGUAGES]
        assert "vi" in codes
        assert "en" in codes
        assert "ja" in codes
        assert len(TARGET_LANGUAGES) == 3

    def test_domains_defined(self) -> None:
        """Kiểm tra danh sách domain được định nghĩa đúng."""
        from src.ui.dialogs.translate_dialog import DOMAINS

        assert "default" in DOMAINS
        assert "it" in DOMAINS
        assert "medical" in DOMAINS
        assert "legal" in DOMAINS
        assert "financial" in DOMAINS
        assert "engineering" in DOMAINS

    def test_styles_defined(self) -> None:
        """Kiểm tra danh sách văn phong được định nghĩa đúng."""
        from src.ui.dialogs.translate_dialog import STYLES

        assert "default" in STYLES
        assert "report" in STYLES
        assert "concise" in STYLES
        assert "literary" in STYLES

    def test_i18n_keys_exist_vi(self) -> None:
        """Kiểm tra tất cả i18n keys cho translate dialog tồn tại (tiếng Việt)."""
        i18n = I18nManager(language="vi")
        keys = [
            "translate.title",
            "translate.file_list",
            "translate.target_language",
            "translate.btn_glossary",
            "translate.btn_expand",
            "translate.btn_translate",
            "translate.btn_stop",
            "translate.domain",
            "translate.style",
            "translate.mode",
            "translate.mode_default",
            "translate.mode_smart",
            "translate.no_files",
            "translate.domain_default",
            "translate.domain_it",
            "translate.domain_medical",
            "translate.domain_legal",
            "translate.domain_financial",
            "translate.domain_engineering",
            "translate.style_default",
            "translate.style_report",
            "translate.style_concise",
            "translate.style_literary",
        ]
        for key in keys:
            value = i18n.t(key)
            assert value != key, f"i18n key không tồn tại: {key}"

    def test_i18n_keys_exist_en(self) -> None:
        """Kiểm tra tất cả i18n keys cho translate dialog tồn tại (tiếng Anh)."""
        I18nManager.reset()
        i18n = I18nManager(language="en")
        keys = [
            "translate.title",
            "translate.file_list",
            "translate.target_language",
            "translate.btn_glossary",
            "translate.btn_expand",
            "translate.btn_translate",
            "translate.btn_stop",
            "translate.domain",
            "translate.style",
            "translate.mode",
            "translate.no_files",
        ]
        for key in keys:
            value = i18n.t(key)
            assert value != key, f"i18n key không tồn tại (en): {key}"
