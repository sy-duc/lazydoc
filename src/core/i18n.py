"""I18n Manager — Quản lý đa ngôn ngữ (Việt/Anh)."""

import json
import logging
from pathlib import Path
from typing import Any

from src.core.logging_config import safe_file_label

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "i18n"
SUPPORTED_LANGUAGES = ("vi", "en")
DEFAULT_LANGUAGE = "vi"


class I18nManager:
    """Quản lý load và tra cứu chuỗi ngôn ngữ (Singleton)."""

    _instance: "I18nManager | None" = None

    def __new__(cls, language: str | None = None) -> "I18nManager":
        """Singleton pattern — chỉ tạo 1 instance duy nhất."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, language: str | None = None) -> None:
        """Khởi tạo I18nManager.

        Args:
            language: Mã ngôn ngữ ('vi' hoặc 'en'). Mặc định 'vi'.
        """
        if self._initialized:
            return
        self._current_language = language or DEFAULT_LANGUAGE
        self._translations: dict[str, str] = {}
        self._load_language(self._current_language)
        self._initialized = True

    def _load_language(self, language: str) -> None:
        """Load file translation cho ngôn ngữ chỉ định.

        Args:
            language: Mã ngôn ngữ cần load.
        """
        if language not in SUPPORTED_LANGUAGES:
            logger.warning("Ngôn ngữ '%s' không được hỗ trợ. Dùng '%s'.", language, DEFAULT_LANGUAGE)
            language = DEFAULT_LANGUAGE

        file_path = ASSETS_DIR / f"{language}.json"
        if not file_path.exists():
            logger.warning("File ngôn ngữ không tồn tại: %s", safe_file_label(file_path))
            self._translations = {}
            return

        with open(file_path, "r", encoding="utf-8") as f:
            self._translations = json.load(f)
        self._current_language = language
        logger.info("Đã load ngôn ngữ: %s (%d chuỗi).", language, len(self._translations))

    def t(self, key: str, **kwargs: Any) -> str:
        """Tra cứu chuỗi dịch theo key.

        Args:
            key: Key của chuỗi cần tra cứu (hỗ trợ dot notation).
            **kwargs: Các biến thay thế trong chuỗi (format string).

        Returns:
            Chuỗi đã dịch, hoặc key gốc nếu không tìm thấy.
        """
        # Hỗ trợ dot notation: "main.title" → translations["main"]["title"]
        keys = key.split(".")
        value: Any = self._translations
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return key
            if value is None:
                return key
        if isinstance(value, str) and kwargs:
            try:
                return value.format(**kwargs)
            except KeyError:
                return value
        return value if isinstance(value, str) else key

    def set_language(self, language: str) -> None:
        """Chuyển đổi ngôn ngữ.

        Args:
            language: Mã ngôn ngữ mới ('vi' hoặc 'en').
        """
        if language != self._current_language:
            self._load_language(language)

    @property
    def current_language(self) -> str:
        """Trả về mã ngôn ngữ hiện tại."""
        return self._current_language

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (dùng cho testing)."""
        cls._instance = None
