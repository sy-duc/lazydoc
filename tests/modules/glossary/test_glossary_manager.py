"""Test cho GlossaryManager."""

import csv
from pathlib import Path

import pytest

from src.core.database import DatabaseManager
from src.modules.glossary.glossary_manager import GlossaryManager


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


@pytest.fixture
def glossary(db: DatabaseManager) -> GlossaryManager:
    """Tạo GlossaryManager với database tạm."""
    return GlossaryManager(db=db)


# --- CRUD ---


class TestAdd:
    """Test thêm thuật ngữ."""

    def test_add_new(self, glossary: GlossaryManager) -> None:
        """Thêm thuật ngữ mới thành công."""
        entry_id = glossary.add("en", "Machine Learning", "vi", "Học máy")
        assert entry_id > 0

    def test_add_duplicate_updates(self, glossary: GlossaryManager) -> None:
        """Thêm trùng → cập nhật term_to."""
        glossary.add("en", "API", "vi", "Giao diện lập trình")
        entry_id = glossary.add("en", "API", "vi", "Giao diện lập trình ứng dụng")
        results = glossary.search("en", "vi", "API")
        assert len(results) == 1
        assert results[0]["term_to"] == "Giao diện lập trình ứng dụng"
        assert results[0]["id"] == entry_id

    def test_add_validation_same_lang(self, glossary: GlossaryManager) -> None:
        """Không cho phép lang_from == lang_to."""
        with pytest.raises(ValueError, match="không được trùng"):
            glossary.add("vi", "test", "vi", "kiểm thử")

    def test_add_validation_empty(self, glossary: GlossaryManager) -> None:
        """Không cho phép trường rỗng."""
        with pytest.raises(ValueError, match="bắt buộc"):
            glossary.add("en", "", "vi", "test")


class TestUpdate:
    """Test cập nhật thuật ngữ."""

    def test_update(self, glossary: GlossaryManager) -> None:
        """Cập nhật thuật ngữ theo ID."""
        entry_id = glossary.add("en", "Database", "vi", "Cơ sở dữ liệu")
        glossary.update(entry_id, "en", "Database", "vi", "CSDL")
        results = glossary.search("en", "vi", "Database")
        assert results[0]["term_to"] == "CSDL"

    def test_update_validation(self, glossary: GlossaryManager) -> None:
        """Validate khi cập nhật."""
        entry_id = glossary.add("en", "test", "vi", "kiểm thử")
        with pytest.raises(ValueError):
            glossary.update(entry_id, "vi", "test", "vi", "test")


class TestDelete:
    """Test xóa thuật ngữ."""

    def test_delete(self, glossary: GlossaryManager) -> None:
        """Xóa thuật ngữ."""
        entry_id = glossary.add("en", "API", "vi", "API")
        glossary.delete(entry_id)
        results = glossary.search("en", "vi", "API")
        assert len(results) == 0


class TestSearch:
    """Test tìm kiếm thuật ngữ."""

    def test_search_all(self, glossary: GlossaryManager) -> None:
        """Tìm tất cả thuật ngữ theo cặp ngôn ngữ."""
        glossary.add("en", "API", "vi", "API")
        glossary.add("en", "Database", "vi", "CSDL")
        glossary.add("en", "Server", "ja", "サーバー")
        results = glossary.search("en", "vi")
        assert len(results) == 2

    def test_search_keyword(self, glossary: GlossaryManager) -> None:
        """Tìm theo keyword."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")
        glossary.add("en", "Deep Learning", "vi", "Học sâu")
        glossary.add("en", "Database", "vi", "CSDL")
        results = glossary.search("en", "vi", "Learning")
        assert len(results) == 2

    def test_search_keyword_in_term_to(self, glossary: GlossaryManager) -> None:
        """Tìm keyword trong term_to."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")
        results = glossary.search("en", "vi", "máy")
        assert len(results) == 1


# --- Tra cứu hai chiều ---


class TestLookup:
    """Test tra cứu hai chiều."""

    def test_lookup_forward(self, glossary: GlossaryManager) -> None:
        """Tra cứu hướng thuận."""
        glossary.add("en", "API", "vi", "Giao diện lập trình")
        result = glossary.lookup("en", "vi")
        assert result["API"] == "Giao diện lập trình"

    def test_lookup_reverse(self, glossary: GlossaryManager) -> None:
        """Tra cứu hướng ngược — đảo chiều tự động."""
        glossary.add("en", "Database", "vi", "Cơ sở dữ liệu")
        result = glossary.lookup("vi", "en")
        assert result["Cơ sở dữ liệu"] == "Database"

    def test_lookup_both_directions(self, glossary: GlossaryManager) -> None:
        """Tra cứu gộp cả hai hướng."""
        glossary.add("en", "API", "vi", "Giao diện lập trình")
        glossary.add("vi", "Máy chủ", "en", "Server")

        # Dịch en → vi
        en_vi = glossary.lookup("en", "vi")
        assert en_vi["API"] == "Giao diện lập trình"
        assert en_vi["Server"] == "Máy chủ"

        # Dịch vi → en
        vi_en = glossary.lookup("vi", "en")
        assert vi_en["Giao diện lập trình"] == "API"
        assert vi_en["Máy chủ"] == "Server"

    def test_lookup_forward_takes_priority(self, glossary: GlossaryManager) -> None:
        """Hướng thuận ưu tiên hơn hướng ngược nếu trùng."""
        glossary.add("en", "Cloud", "vi", "Đám mây")
        glossary.add("vi", "Cloud", "en", "Mây")
        result = glossary.lookup("en", "vi")
        assert result["Cloud"] == "Đám mây"


# --- Áp dụng thuật ngữ khi dịch ---


class TestApplyGlossary:
    """Test áp dụng thuật ngữ trước/sau khi dịch."""

    def test_pre_translate(self, glossary: GlossaryManager) -> None:
        """Thay thuật ngữ bằng placeholder."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")
        glossary.add("en", "API", "vi", "API")

        text = "Use Machine Learning and API to build apps."
        result, placeholders = glossary.apply_pre_translate(text, "en", "vi")

        assert "Machine Learning" not in result
        assert "API" not in result
        assert len(placeholders) == 2

    def test_post_translate(self, glossary: GlossaryManager) -> None:
        """Thay placeholder bằng thuật ngữ đích."""
        placeholders = {"⟦GLOSS_0⟧": "Học máy", "⟦GLOSS_1⟧": "API"}
        text = "Sử dụng ⟦GLOSS_0⟧ và ⟦GLOSS_1⟧ để xây dựng ứng dụng."
        result = glossary.apply_post_translate(text, placeholders)
        assert result == "Sử dụng Học máy và API để xây dựng ứng dụng."

    def test_pre_translate_longer_term_first(self, glossary: GlossaryManager) -> None:
        """Thuật ngữ dài hơn được thay trước."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")
        glossary.add("en", "Machine", "vi", "Máy")

        text = "Machine Learning is part of Machine intelligence."
        result, placeholders = glossary.apply_pre_translate(text, "en", "vi")

        # "Machine Learning" phải được thay trước, không bị "Machine" cắt ngang
        assert any(v == "Học máy" for v in placeholders.values())

    def test_pre_translate_case_insensitive(self, glossary: GlossaryManager) -> None:
        """Thay thế không phân biệt hoa thường."""
        glossary.add("en", "API", "vi", "API")
        text = "The api is ready."
        result, placeholders = glossary.apply_pre_translate(text, "en", "vi")
        assert "api" not in result.lower() or any(v == "API" for v in placeholders.values())

    def test_pre_translate_empty_glossary(self, glossary: GlossaryManager) -> None:
        """Không có thuật ngữ → trả về nguyên văn."""
        text = "Hello world"
        result, placeholders = glossary.apply_pre_translate(text, "en", "vi")
        assert result == text
        assert placeholders == {}

    def test_roundtrip(self, glossary: GlossaryManager) -> None:
        """Kiểm tra toàn bộ luồng pre → dịch → post."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")

        original = "Machine Learning is great."
        pre_text, placeholders = glossary.apply_pre_translate(original, "en", "vi")
        # Giả lập AI dịch (giữ nguyên placeholder)
        translated = pre_text.replace("is great", "rất tuyệt")
        final = glossary.apply_post_translate(translated, placeholders)

        assert "Học máy" in final
        assert "⟦GLOSS_" not in final


# --- Import / Export CSV ---


class TestImportExport:
    """Test import/export CSV."""

    def test_import_csv(self, glossary: GlossaryManager, tmp_path: Path) -> None:
        """Import từ file CSV."""
        csv_file = tmp_path / "import.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["lang_from", "term_from", "lang_to", "term_to"])
            writer.writerow(["en", "API", "vi", "API"])
            writer.writerow(["en", "Database", "vi", "CSDL"])

        count = glossary.import_csv(csv_file)
        assert count == 2

        results = glossary.search("en", "vi")
        assert len(results) == 2

    def test_import_csv_skip_header(self, glossary: GlossaryManager, tmp_path: Path) -> None:
        """Bỏ qua dòng header."""
        csv_file = tmp_path / "import.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["lang_from", "term_from", "lang_to", "term_to"])
            writer.writerow(["en", "API", "vi", "API"])

        count = glossary.import_csv(csv_file)
        assert count == 1

    def test_import_csv_no_header(self, glossary: GlossaryManager, tmp_path: Path) -> None:
        """Import file không có header."""
        csv_file = tmp_path / "import.csv"
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["en", "API", "vi", "API"])

        count = glossary.import_csv(csv_file)
        assert count == 1

    def test_import_csv_file_not_found(self, glossary: GlossaryManager) -> None:
        """File không tồn tại → raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            glossary.import_csv("/nonexistent/file.csv")

    def test_export_csv(self, glossary: GlossaryManager, tmp_path: Path) -> None:
        """Export ra file CSV."""
        glossary.add("en", "API", "vi", "API")
        glossary.add("en", "Database", "vi", "CSDL")

        csv_file = tmp_path / "export.csv"
        count = glossary.export_csv(csv_file)
        assert count == 2

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # 1 header + 2 data rows
        assert len(rows) == 3
        assert rows[0] == ["lang_from", "term_from", "lang_to", "term_to"]

    def test_import_export_roundtrip(self, glossary: GlossaryManager, tmp_path: Path) -> None:
        """Export → import lại → dữ liệu giữ nguyên."""
        glossary.add("en", "Machine Learning", "vi", "Học máy")
        glossary.add("ja", "人工知能", "vi", "Trí tuệ nhân tạo")

        csv_file = tmp_path / "roundtrip.csv"
        glossary.export_csv(csv_file)

        # Xóa sạch rồi import lại
        glossary.delete(glossary.search("en", "vi")[0]["id"])
        glossary.delete(glossary.search("ja", "vi")[0]["id"])
        assert glossary.search("en", "vi") == []

        count = glossary.import_csv(csv_file)
        assert count == 2
        assert len(glossary.search("en", "vi")) == 1
        assert len(glossary.search("ja", "vi")) == 1
