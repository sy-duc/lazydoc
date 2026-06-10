"""Logging configuration for LazyDoc.

This module keeps runtime logs useful for support while avoiding document
content, prompts, API keys, and unbounded disk growth.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import threading
import tempfile
from hashlib import sha256
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

APP_NAME = "LazyDoc"
APP_AUTHOR = "LazyDoc"
LOG_FILE_NAME = "lazydoc.log"
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 3

_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(api[_-]?key|token|secret|password)(\s*[=:]\s*)[^\s,;]+", re.I),
        r"\1\2[REDACTED]",
    ),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I), r"\1[REDACTED]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{8,}", re.I), "[REDACTED]"),
)

# Tiền tố logger của thư viện bên thứ ba cần lọc khỏi log file
_THIRD_PARTY_PREFIXES = (
    "argostranslate", "google", "openai", "httpx", "httpcore", "urllib3",
)


class _ThirdPartyFilter(logging.Filter):
    """Lọc bỏ log từ thư viện bên thứ ba, tránh ghi nội dung tài liệu vào log."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(record.name.startswith(p) for p in _THIRD_PARTY_PREFIXES)


def get_log_dir() -> Path:
    """Return the user-local log directory and create it if needed."""
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        log_dir = base / APP_NAME / "logs"
    else:
        try:
            from platformdirs import user_log_dir

            log_dir = Path(user_log_dir(APP_NAME, APP_AUTHOR))
        except Exception:
            log_dir = Path.home() / f".{APP_NAME.lower()}" / "logs"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except OSError:
        fallback = Path(tempfile.gettempdir()) / APP_NAME / "logs"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def get_log_file() -> Path:
    """Return the current log file path."""
    return get_log_dir() / LOG_FILE_NAME


def sanitize_error(error: object) -> str:
    """Return a compact, redacted error string for logs and UI messages."""
    message = str(error)
    for pattern, replacement in _SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    message = message.replace("\n", " ").replace("\r", " ").strip()
    return message[:500] if len(message) > 500 else message


def safe_file_label(path: Path | str | None) -> str:
    """Return non-content file metadata suitable for INFO logs.

    The label intentionally avoids full paths and full file names. A short hash
    helps correlate repeated events for the same file within support logs.
    """
    if path is None:
        return "file=unknown"

    p = Path(path)
    ext = p.suffix.lower() or "<none>"
    try:
        size = p.stat().st_size if p.exists() else None
    except OSError:
        size = None

    digest_source = str(p.resolve(strict=False)).encode("utf-8", errors="ignore")
    file_id = sha256(digest_source).hexdigest()[:8]
    if size is None:
        return f"file_id={file_id}, ext={ext}"
    return f"file_id={file_id}, ext={ext}, size={_format_size(size)}"


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    return f"{size_bytes / (1024 * 1024):.1f}MB"


def configure_logging(level: int = logging.INFO) -> Path:
    """Configure app-wide logging with bounded file retention."""
    log_file = get_log_file()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _filter = _ThirdPartyFilter()

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(_filter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)

    if sys.stderr is not None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(_filter)
        root.addHandler(stream_handler)

    install_crash_hooks()
    logging.getLogger("lazydoc").info("Logging initialized: %s", log_file)
    return log_file


def install_crash_hooks() -> None:
    """Log uncaught exceptions from the main thread and Python threads."""
    sys.excepthook = _handle_uncaught_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = _handle_thread_exception


def _handle_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger("lazydoc").critical(
        "Unhandled exception: %s",
        sanitize_error(exc_value),
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def _handle_thread_exception(args: threading.ExceptHookArgs) -> None:
    logging.getLogger("lazydoc").critical(
        "Unhandled thread exception: %s",
        sanitize_error(args.exc_value),
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
