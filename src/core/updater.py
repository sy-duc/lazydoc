"""UpdateChecker — Kiểm tra phiên bản mới từ GitHub Releases."""

import json
import logging
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

from src.core.version import APP_VERSION

logger = logging.getLogger(__name__)

_API_URL = "https://api.github.com/repos/sy-duc/lazydoc/releases/latest"
_RELEASES_URL = "https://github.com/sy-duc/lazydoc/releases/latest"


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Chuyển chuỗi version thành tuple số để so sánh."""
    try:
        return tuple(int(x) for x in version_str.lstrip("v").split("."))
    except ValueError:
        return (0,)


class UpdateChecker(QThread):
    """Thread kiểm tra phiên bản mới trên GitHub Releases."""

    update_available = Signal(str, str)  # (new_version, release_url)

    def run(self) -> None:
        """Fetch GitHub Releases API và phát signal nếu có bản mới."""
        try:
            req = urllib.request.Request(
                _API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "LazyDoc",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            latest_tag = data.get("tag_name", "")
            release_url = data.get("html_url", _RELEASES_URL)

            if _parse_version(latest_tag) > _parse_version(APP_VERSION):
                self.update_available.emit(latest_tag.lstrip("v"), release_url)

        except Exception:
            logger.debug("Không thể kiểm tra phiên bản mới.", exc_info=True)
