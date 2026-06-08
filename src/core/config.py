"""Config Manager — Đọc/ghi file cấu hình config.yaml."""

import logging
from pathlib import Path
from typing import Any

import yaml

from src.core.logging_config import safe_file_label

logger = logging.getLogger(__name__)

# Đường dẫn mặc định đến file config
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"


class ConfigManager:
    """Quản lý đọc/ghi cấu hình từ file config.yaml (Singleton)."""

    _instance: "ConfigManager | None" = None

    def __new__(cls, config_path: Path | None = None) -> "ConfigManager":
        """Singleton pattern — chỉ tạo 1 instance duy nhất."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Path | None = None) -> None:
        """Khởi tạo ConfigManager.

        Args:
            config_path: Đường dẫn đến file config.yaml. Mặc định dùng config/config.yaml.
        """
        if self._initialized:
            return
        self._config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load()
        self._initialized = True

    def _load(self) -> None:
        """Đọc file config.yaml vào memory."""
        if not self._config_path.exists():
            logger.warning("File config không tồn tại: %s", safe_file_label(self._config_path))
            self._data = {}
            return

        with open(self._config_path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}
        logger.info("Đã load config từ: %s", safe_file_label(self._config_path))

    def get(self, key: str, default: Any = None) -> Any:
        """Lấy giá trị config theo key (hỗ trợ dot notation).

        Dùng greedy matching để xử lý đúng các key có dấu chấm trong tên
        (ví dụ model name "gemini-2.5-flash" trong path pricing.gemini.gemini-2.5-flash.input).

        Args:
            key: Key cấu hình, hỗ trợ dạng "pricing.gemini.gemini-2.5-flash.input".
            default: Giá trị mặc định nếu key không tồn tại.

        Returns:
            Giá trị config hoặc default.
        """
        parts = key.split(".")
        value: Any = self._data
        i = 0
        while i < len(parts):
            if not isinstance(value, dict):
                return default
            # Greedy: thử ghép nhiều segment nhất có thể để khớp với dict key
            # (xử lý key chứa dấu chấm như "gemini-2.5-flash")
            matched = False
            for end in range(len(parts), i, -1):
                candidate = ".".join(parts[i:end])
                if candidate in value:
                    value = value[candidate]
                    i = end
                    matched = True
                    break
            if not matched:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Gán giá trị config theo key (hỗ trợ dot notation) và lưu file.

        Args:
            key: Key cấu hình.
            value: Giá trị cần gán.
        """
        keys = key.split(".")
        data = self._data
        for k in keys[:-1]:
            if k not in data or not isinstance(data[k], dict):
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self._save()

    def _save(self) -> None:
        """Ghi config hiện tại ra file yaml."""
        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("Đã lưu config vào: %s", safe_file_label(self._config_path))

    @property
    def data(self) -> dict[str, Any]:
        """Trả về toàn bộ dữ liệu config."""
        return self._data

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (dùng cho testing)."""
        cls._instance = None
