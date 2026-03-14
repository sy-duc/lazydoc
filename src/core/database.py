"""Database Manager — Quản lý kết nối SQLite và migration."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_data_dir

logger = logging.getLogger(__name__)

APP_NAME = "LazyDoc"
APP_AUTHOR = "LazyDoc"

# Schema version hiện tại
CURRENT_SCHEMA_VERSION = 1


def _get_default_db_path() -> Path:
    """Trả về đường dẫn mặc định đến file database.

    Returns:
        Đường dẫn đến lazydoc.db trong thư mục AppData.
    """
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "lazydoc.db"


class DatabaseManager:
    """Quản lý kết nối SQLite, tạo bảng và migration (Singleton)."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls, db_path: Path | None = None) -> "DatabaseManager":
        """Singleton pattern — chỉ tạo 1 instance duy nhất."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Path | None = None) -> None:
        """Khởi tạo DatabaseManager.

        Args:
            db_path: Đường dẫn đến file SQLite. Mặc định dùng thư mục AppData.
        """
        if self._initialized:
            return
        self._db_path = db_path or _get_default_db_path()
        self._conn: sqlite3.Connection | None = None
        self._initialized = True

    @property
    def connection(self) -> sqlite3.Connection:
        """Trả về connection hiện tại, tạo mới nếu chưa có."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        """Khởi tạo database: tạo bảng và chạy migration nếu cần."""
        logger.info("Đang khởi tạo database tại: %s", self._db_path)
        self._create_schema_version_table()

        current_version = self._get_schema_version()
        if current_version < CURRENT_SCHEMA_VERSION:
            self._run_migrations(current_version)
        else:
            logger.info("Database đã ở phiên bản mới nhất (v%d).", current_version)

    def _create_schema_version_table(self) -> None:
        """Tạo bảng schema_version nếu chưa tồn tại."""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        self.connection.commit()

    def _get_schema_version(self) -> int:
        """Lấy phiên bản schema hiện tại.

        Returns:
            Số phiên bản hiện tại. 0 nếu chưa có migration nào.
        """
        cursor = self.connection.execute(
            "SELECT MAX(version) FROM schema_version"
        )
        row = cursor.fetchone()
        return row[0] if row[0] is not None else 0

    def _set_schema_version(self, version: int) -> None:
        """Ghi nhận phiên bản schema đã áp dụng.

        Args:
            version: Số phiên bản vừa áp dụng.
        """
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
            (version, now),
        )
        self.connection.commit()

    def _run_migrations(self, from_version: int) -> None:
        """Chạy migration từ from_version đến CURRENT_SCHEMA_VERSION.

        Args:
            from_version: Phiên bản hiện tại của database.
        """
        migrations = {
            1: self._migration_v1,
        }

        for version in range(from_version + 1, CURRENT_SCHEMA_VERSION + 1):
            migration_fn = migrations.get(version)
            if migration_fn:
                logger.info("Đang chạy migration v%d...", version)
                migration_fn()
                self._set_schema_version(version)
                logger.info("Migration v%d hoàn tất.", version)

    def _migration_v1(self) -> None:
        """Migration v1: Tạo toàn bộ bảng ban đầu."""
        conn = self.connection
        now = datetime.now(timezone.utc).isoformat()

        # Bảng ai_provider
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_provider (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                api_key_enc TEXT,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Bảng glossary
        conn.execute("""
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lang_from TEXT NOT NULL,
                term_from TEXT NOT NULL,
                lang_to TEXT NOT NULL,
                term_to TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(lang_from, term_from, lang_to)
            )
        """)

        # Index cho glossary
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_glossary_lookup
            ON glossary(lang_from, lang_to, term_from)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_glossary_reverse
            ON glossary(lang_to, lang_from, term_to)
        """)

        # Bảng settings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Dữ liệu khởi tạo mặc định
        providers = [
            ("gemini", 1),
            ("openai", 0),
            ("claude", 0),
        ]
        for name, is_active in providers:
            conn.execute(
                """INSERT OR IGNORE INTO ai_provider (name, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?)""",
                (name, is_active, now, now),
            )

        default_settings = [
            ("app_language", '"vi"'),
            ("active_provider", '"gemini"'),
        ]
        for key, value in default_settings:
            conn.execute(
                """INSERT OR IGNORE INTO settings (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, value, now),
            )

        conn.commit()

    def close(self) -> None:
        """Đóng kết nối database."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (dùng cho testing)."""
        if cls._instance and cls._instance._conn:
            cls._instance._conn.close()
        cls._instance = None
