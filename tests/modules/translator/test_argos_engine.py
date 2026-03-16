"""Test ArgosEngine — Kiểm thử engine dịch offline Argos Translate."""

import pytest

from src.modules.translator.argos_engine import ArgosEngine


class TestDetectLanguage:
    """Test phát hiện ngôn ngữ."""

    def setup_method(self) -> None:
        self.engine = ArgosEngine()

    def test_detect_vietnamese(self) -> None:
        """Phát hiện tiếng Việt từ văn bản có dấu."""
        text = "Xin chào, đây là một đoạn văn bản tiếng Việt có dấu."
        assert self.engine.detect_language(text) == "vi"

    def test_detect_japanese(self) -> None:
        """Phát hiện tiếng Nhật từ văn bản có hiragana/katakana."""
        text = "こんにちは、これは日本語のテキストです。"
        assert self.engine.detect_language(text) == "ja"

    def test_detect_english(self) -> None:
        """Phát hiện tiếng Anh (mặc định khi không có ký tự đặc trưng)."""
        text = "Hello, this is an English text without special characters."
        assert self.engine.detect_language(text) == "en"

    def test_detect_excludes_target_lang(self) -> None:
        """Loại trừ ngôn ngữ đích khi phát hiện."""
        text = "Hello, this is an English text."
        result = self.engine.detect_language(text, exclude_lang="en")
        assert result != "en"
        assert result in ("vi", "ja")

    def test_detect_empty_text(self) -> None:
        """Trả về 'en' khi văn bản rỗng."""
        assert self.engine.detect_language("") == "en"
        assert self.engine.detect_language("   ") == "en"


class TestGetRequiredPairs:
    """Test xác định cặp model cần thiết."""

    def test_direct_pair_en_vi(self) -> None:
        pairs = ArgosEngine._get_required_pairs("en", "vi")
        assert pairs == [("en", "vi")]

    def test_direct_pair_vi_en(self) -> None:
        pairs = ArgosEngine._get_required_pairs("vi", "en")
        assert pairs == [("vi", "en")]

    def test_pivot_vi_ja(self) -> None:
        """vi → ja cần pivot qua en: vi→en + en→ja."""
        pairs = ArgosEngine._get_required_pairs("vi", "ja")
        assert ("vi", "en") in pairs
        assert ("en", "ja") in pairs

    def test_pivot_ja_vi(self) -> None:
        """ja → vi cần pivot qua en: ja→en + en→vi."""
        pairs = ArgosEngine._get_required_pairs("ja", "vi")
        assert ("ja", "en") in pairs
        assert ("en", "vi") in pairs


class TestCreateTranslateFn:
    """Test tạo hàm dịch."""

    def test_empty_text_returns_empty(self) -> None:
        """Hàm dịch trả về text rỗng khi input rỗng."""
        engine = ArgosEngine()
        fn = engine.create_translate_fn("en", "vi")
        assert fn("") == ""
        assert fn("   ") == "   "

    def test_none_text_returns_empty(self) -> None:
        """Hàm dịch trả về rỗng khi input None (edge case)."""
        engine = ArgosEngine()
        fn = engine.create_translate_fn("en", "vi")
        # translate_fn kiểm tra `not text` nên None sẽ trả về None
        assert fn(None) is None
