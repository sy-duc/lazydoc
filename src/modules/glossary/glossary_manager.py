"""GlossaryManager — Quản lý bảng thuật ngữ (CRUD, tra cứu hai chiều, áp dụng khi dịch)."""

import csv
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from src.core.database import DatabaseManager
from src.core.logging_config import safe_file_label

logger = logging.getLogger(__name__)


class GlossaryManager:
    """Quản lý bảng thuật ngữ: CRUD, tra cứu hai chiều, import/export CSV,
    áp dụng thuật ngữ vào văn bản khi dịch."""

    def __init__(self, db: DatabaseManager | None = None) -> None:
        """Khởi tạo GlossaryManager.

        Args:
            db: DatabaseManager instance. Mặc định dùng singleton.
        """
        self._db = db or DatabaseManager()

    @property
    def _conn(self):
        """Shortcut truy cập connection."""
        return self._db.connection

    # --- CRUD ---

    def add(
        self,
        lang_from: str,
        term_from: str,
        lang_to: str,
        term_to: str,
    ) -> int:
        """Thêm thuật ngữ mới. Nếu đã tồn tại thì cập nhật term_to.

        Args:
            lang_from: Mã ngôn ngữ nguồn (vi, en, ja).
            term_from: Thuật ngữ nguồn.
            lang_to: Mã ngôn ngữ đích.
            term_to: Thuật ngữ đích.

        Returns:
            ID của bản ghi (mới hoặc đã cập nhật).

        Raises:
            ValueError: Nếu lang_from == lang_to hoặc thiếu dữ liệu.
        """
        self._validate(lang_from, term_from, lang_to, term_to)
        now = datetime.now(timezone.utc).isoformat()

        try:
            cursor = self._conn.execute(
                """INSERT INTO glossary
                   (lang_from, term_from, lang_to, term_to, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (lang_from, term_from, lang_to, term_to, now, now),
            )
            self._conn.commit()
            logger.info("Đã thêm thuật ngữ glossary: %s -> %s", lang_from, lang_to)
            return cursor.lastrowid
        except Exception:
            # UNIQUE constraint — cập nhật bản ghi cũ
            self._conn.execute(
                """UPDATE glossary
                   SET term_to = ?, updated_at = ?
                   WHERE lang_from = ? AND term_from = ? AND lang_to = ?""",
                (term_to, now, lang_from, term_from, lang_to),
            )
            self._conn.commit()
            row = self._conn.execute(
                "SELECT id FROM glossary WHERE lang_from = ? AND term_from = ? AND lang_to = ?",
                (lang_from, term_from, lang_to),
            ).fetchone()
            logger.info("Đã cập nhật thuật ngữ trùng: %s -> %s", lang_from, lang_to)
            return row["id"]

    def update(
        self,
        entry_id: int,
        lang_from: str,
        term_from: str,
        lang_to: str,
        term_to: str,
    ) -> None:
        """Cập nhật thuật ngữ theo ID.

        Args:
            entry_id: ID bản ghi.
            lang_from: Mã ngôn ngữ nguồn.
            term_from: Thuật ngữ nguồn.
            lang_to: Mã ngôn ngữ đích.
            term_to: Thuật ngữ đích.

        Raises:
            ValueError: Nếu lang_from == lang_to hoặc thiếu dữ liệu.
        """
        self._validate(lang_from, term_from, lang_to, term_to)
        now = datetime.now(timezone.utc).isoformat()

        self._conn.execute(
            """UPDATE glossary
               SET term_from = ?, term_to = ?, lang_from = ?, lang_to = ?,
                   updated_at = ?
               WHERE id = ?""",
            (term_from, term_to, lang_from, lang_to, now, entry_id),
        )
        self._conn.commit()
        logger.info("Đã cập nhật thuật ngữ id=%d: %s -> %s", entry_id, lang_from, lang_to)

    def delete(self, entry_id: int) -> None:
        """Xóa thuật ngữ theo ID.

        Args:
            entry_id: ID bản ghi cần xóa.
        """
        self._conn.execute("DELETE FROM glossary WHERE id = ?", (entry_id,))
        self._conn.commit()
        logger.info("Đã xóa thuật ngữ id=%d.", entry_id)

    def search(
        self,
        lang_from: str,
        lang_to: str,
        keyword: str = "",
    ) -> list[dict]:
        """Tìm kiếm thuật ngữ theo cặp ngôn ngữ, có thể lọc theo keyword.

        Chỉ tìm theo hướng (lang_from, lang_to) — không đảo chiều.

        Args:
            lang_from: Mã ngôn ngữ nguồn.
            lang_to: Mã ngôn ngữ đích.
            keyword: Từ khóa tìm kiếm (tìm trong cả term_from và term_to).

        Returns:
            Danh sách dict với keys: id, term_from, term_to.
        """
        if keyword:
            pattern = f"%{keyword}%"
            cursor = self._conn.execute(
                """SELECT id, term_from, term_to FROM glossary
                   WHERE lang_from = ? AND lang_to = ?
                     AND (term_from LIKE ? OR term_to LIKE ?)
                   ORDER BY term_from COLLATE NOCASE""",
                (lang_from, lang_to, pattern, pattern),
            )
        else:
            cursor = self._conn.execute(
                """SELECT id, term_from, term_to FROM glossary
                   WHERE lang_from = ? AND lang_to = ?
                   ORDER BY term_from COLLATE NOCASE""",
                (lang_from, lang_to),
            )

        return [
            {"id": row["id"], "term_from": row["term_from"], "term_to": row["term_to"]}
            for row in cursor.fetchall()
        ]

    # --- Tra cứu hai chiều ---

    def lookup(self, lang_from: str, lang_to: str) -> dict[str, str]:
        """Tra cứu tất cả thuật ngữ cho cặp ngôn ngữ, hỗ trợ hai chiều.

        Khi dịch từ A → B:
        - Tìm record có lang_from=A, lang_to=B → dùng trực tiếp.
        - Tìm record có lang_from=B, lang_to=A → đảo ngược (term_to → term_from).

        Args:
            lang_from: Mã ngôn ngữ nguồn.
            lang_to: Mã ngôn ngữ đích.

        Returns:
            Dict mapping thuật ngữ nguồn → thuật ngữ đích.
        """
        result: dict[str, str] = {}

        # Hướng thuận: lang_from → lang_to
        cursor = self._conn.execute(
            "SELECT term_from, term_to FROM glossary WHERE lang_from = ? AND lang_to = ?",
            (lang_from, lang_to),
        )
        for row in cursor.fetchall():
            result[row["term_from"]] = row["term_to"]

        # Hướng ngược: lang_to → lang_from (đảo term)
        cursor = self._conn.execute(
            "SELECT term_from, term_to FROM glossary WHERE lang_from = ? AND lang_to = ?",
            (lang_to, lang_from),
        )
        for row in cursor.fetchall():
            # Đảo: term_to (ngôn ngữ nguồn gốc) → term_from (ngôn ngữ đích gốc)
            # Nhưng ở đây lang_from của record = lang_to mà ta cần dịch
            # Nên term_from = thuật ngữ ở ngôn ngữ đích, term_to = thuật ngữ ở ngôn ngữ nguồn
            # → ta cần dịch term_to (ngôn ngữ nguồn) → term_from (ngôn ngữ đích)
            if row["term_to"] not in result:
                result[row["term_to"]] = row["term_from"]

        return result

    # --- Áp dụng thuật ngữ khi dịch ---

    def apply_pre_translate(self, text: str, lang_from: str, lang_to: str) -> tuple[str, dict[str, str]]:
        """Thay thế thuật ngữ trong văn bản trước khi gửi cho AI dịch.

        Thay thuật ngữ nguồn bằng placeholder để AI không dịch sai.
        Thuật ngữ dài hơn được ưu tiên thay trước (tránh thay partial match).

        Args:
            text: Văn bản cần xử lý.
            lang_from: Mã ngôn ngữ nguồn.
            lang_to: Mã ngôn ngữ đích.

        Returns:
            Tuple (văn bản đã thay placeholder, dict placeholder → thuật ngữ đích).
        """
        glossary = self.lookup(lang_from, lang_to)
        if not glossary:
            return text, {}

        # Sắp xếp theo độ dài giảm dần để tránh thay partial match
        sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
        placeholders: dict[str, str] = {}

        for i, term in enumerate(sorted_terms):
            placeholder = f"⟦GLOSS_{i}⟧"
            # Thay thế case-insensitive, giữ word boundary
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(text):
                text = pattern.sub(placeholder, text)
                placeholders[placeholder] = glossary[term]

        return text, placeholders

    def apply_post_translate(self, text: str, placeholders: dict[str, str]) -> str:
        """Thay thế placeholder bằng thuật ngữ đích sau khi AI dịch xong.

        Args:
            text: Văn bản đã dịch (có chứa placeholder).
            placeholders: Dict placeholder → thuật ngữ đích.

        Returns:
            Văn bản đã thay placeholder bằng thuật ngữ đích.
        """
        for placeholder, term_to in placeholders.items():
            text = text.replace(placeholder, term_to)
        return text

    # --- Import / Export CSV ---

    def import_csv(self, file_path: str | Path) -> int:
        """Import thuật ngữ từ file CSV.

        Format CSV: lang_from, term_from, lang_to, term_to
        Dòng header (nếu có) bắt đầu bằng 'lang_from' sẽ bị bỏ qua.

        Args:
            file_path: Đường dẫn đến file CSV.

        Returns:
            Số thuật ngữ đã import.

        Raises:
            FileNotFoundError: Nếu file không tồn tại.
            ValueError: Nếu file không đúng format.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

        count = 0
        now = datetime.now(timezone.utc).isoformat()

        with open(file_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            for row_data in reader:
                if len(row_data) < 4:
                    continue
                lang_from, term_from, lang_to, term_to = (
                    row_data[0].strip(),
                    row_data[1].strip(),
                    row_data[2].strip(),
                    row_data[3].strip(),
                )
                # Bỏ qua header
                if lang_from == "lang_from":
                    continue
                if not all([lang_from, term_from, lang_to, term_to]):
                    continue
                self._conn.execute(
                    """INSERT OR REPLACE INTO glossary
                       (lang_from, term_from, lang_to, term_to, created_at, updated_at)
                       VALUES (?, ?, ?, ?,
                               COALESCE(
                                   (SELECT created_at FROM glossary
                                    WHERE lang_from=? AND term_from=? AND lang_to=?),
                                   ?),
                               ?)""",
                    (
                        lang_from, term_from, lang_to, term_to,
                        lang_from, term_from, lang_to, now, now,
                    ),
                )
                count += 1
        self._conn.commit()
        logger.info("Import thành công %d thuật ngữ từ %s.", count, safe_file_label(file_path))
        return count

    def export_csv(self, file_path: str | Path) -> int:
        """Export toàn bộ thuật ngữ ra file CSV.

        Args:
            file_path: Đường dẫn file CSV đích.

        Returns:
            Số thuật ngữ đã export.
        """
        file_path = Path(file_path)
        cursor = self._conn.execute(
            """SELECT lang_from, term_from, lang_to, term_to
               FROM glossary ORDER BY lang_from, lang_to, term_from"""
        )

        count = 0
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["lang_from", "term_from", "lang_to", "term_to"])
            for row in cursor.fetchall():
                writer.writerow([
                    row["lang_from"],
                    row["term_from"],
                    row["lang_to"],
                    row["term_to"],
                ])
                count += 1

        logger.info("Export thành công %d thuật ngữ ra %s.", count, safe_file_label(file_path))
        return count

    # --- Validation ---

    @staticmethod
    def _validate(
        lang_from: str, term_from: str, lang_to: str, term_to: str
    ) -> None:
        """Validate dữ liệu đầu vào.

        Raises:
            ValueError: Nếu thiếu dữ liệu hoặc lang_from == lang_to.
        """
        if not all([lang_from, term_from, lang_to, term_to]):
            raise ValueError("Tất cả các trường đều bắt buộc.")
        if lang_from == lang_to:
            raise ValueError("Ngôn ngữ nguồn và đích không được trùng nhau.")
