"""ArgosEngine — Wrapper cho Argos Translate (dịch offline, miễn phí)."""

import logging
import re
from typing import Callable

logger = logging.getLogger(__name__)

# Mapping mã ngôn ngữ nội bộ → mã Argos
_LANG_MAP = {
    "vi": "vi",
    "en": "en",
    "ja": "ja",
}

# Cặp ngôn ngữ Argos hỗ trợ trực tiếp
_DIRECT_PAIRS = {
    ("en", "vi"), ("vi", "en"),
    ("en", "ja"), ("ja", "en"),
}


class ArgosEngine:
    """Engine dịch offline sử dụng Argos Translate.

    Hỗ trợ:
    - Dịch trực tiếp: en↔vi, en↔ja.
    - Dịch qua trung gian (pivot qua English): vi↔ja.
    - Tự động phát hiện ngôn ngữ nguồn.
    - Cài đặt model tự động nếu chưa có.
    """

    def __init__(self) -> None:
        """Khởi tạo ArgosEngine."""
        self._installed_pairs: set[tuple[str, str]] = set()
        self._initialized = False

    def ensure_models(self, source_lang: str, target_lang: str) -> None:
        """Đảm bảo model cho cặp ngôn ngữ đã được cài đặt.

        Args:
            source_lang: Mã ngôn ngữ nguồn (vi, en, ja).
            target_lang: Mã ngôn ngữ đích (vi, en, ja).

        Raises:
            RuntimeError: Nếu không thể cài đặt model.
        """
        import argostranslate.package
        import argostranslate.translate

        if not self._initialized:
            argostranslate.package.update_package_index()
            self._initialized = True

        pairs_needed = self._get_required_pairs(source_lang, target_lang)

        for src, tgt in pairs_needed:
            if (src, tgt) in self._installed_pairs:
                continue

            # Kiểm tra đã cài chưa
            installed = argostranslate.translate.get_installed_languages()
            installed_codes = {lang.code for lang in installed}
            if src in installed_codes and tgt in installed_codes:
                src_lang_obj = next(l for l in installed if l.code == src)
                translations = src_lang_obj.get_translation(
                    next(l for l in installed if l.code == tgt)
                )
                if translations is not None:
                    self._installed_pairs.add((src, tgt))
                    logger.info("Model đã có sẵn: %s → %s", src, tgt)
                    continue

            # Cài đặt model
            available = argostranslate.package.get_available_packages()
            pkg = next(
                (p for p in available if p.from_code == src and p.to_code == tgt),
                None,
            )
            if pkg is None:
                raise RuntimeError(
                    f"Không tìm thấy model Argos cho {src} → {tgt}. "
                    f"Vui lòng kiểm tra kết nối mạng."
                )
            logger.info("Đang tải model: %s → %s ...", src, tgt)
            argostranslate.package.install_from_path(pkg.download())
            self._installed_pairs.add((src, tgt))
            logger.info("Đã cài model: %s → %s", src, tgt)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Dịch văn bản bằng Argos Translate.

        Args:
            text: Văn bản cần dịch.
            source_lang: Mã ngôn ngữ nguồn.
            target_lang: Mã ngôn ngữ đích.

        Returns:
            Văn bản đã dịch.
        """
        if not text or not text.strip():
            return text

        if source_lang == target_lang:
            return text

        import argostranslate.translate

        # Dịch trực tiếp nếu có model
        if (source_lang, target_lang) in _DIRECT_PAIRS:
            return argostranslate.translate.translate(text, source_lang, target_lang)

        # Pivot qua English cho vi↔ja
        if source_lang != "en" and target_lang != "en":
            intermediate = argostranslate.translate.translate(text, source_lang, "en")
            return argostranslate.translate.translate(intermediate, "en", target_lang)

        return argostranslate.translate.translate(text, source_lang, target_lang)

    def detect_language(self, text: str, exclude_lang: str = "") -> str:
        """Phát hiện ngôn ngữ của văn bản.

        Sử dụng heuristic đơn giản dựa trên bộ ký tự:
        - Tiếng Nhật: hiragana, katakana, kanji.
        - Tiếng Việt: ký tự có dấu đặc trưng.
        - Tiếng Anh: mặc định nếu không phải 2 ngôn ngữ trên.

        Args:
            text: Văn bản cần phát hiện.
            exclude_lang: Ngôn ngữ cần loại trừ (ngôn ngữ đích).

        Returns:
            Mã ngôn ngữ phát hiện được (vi, en, ja).
        """
        if not text or not text.strip():
            return "en"

        sample = text[:2000]

        # Phát hiện tiếng Nhật (hiragana, katakana, kanji)
        ja_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]')
        ja_count = len(ja_pattern.findall(sample))

        # Phát hiện tiếng Việt (ký tự có dấu đặc trưng)
        vi_pattern = re.compile(
            r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡ'
            r'ùúụủũưừứựửữỳýỵỷỹđ'
            r'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ'
            r'ÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]'
        )
        vi_count = len(vi_pattern.findall(sample))

        # Xác định ngôn ngữ
        scores = {"ja": ja_count, "vi": vi_count, "en": 0}
        if exclude_lang in scores:
            scores.pop(exclude_lang)

        # Nếu có ký tự đặc trưng rõ ràng → chọn ngôn ngữ đó
        if ja_count > 5:
            detected = "ja"
        elif vi_count > 5:
            detected = "vi"
        else:
            detected = "en"

        if detected == exclude_lang:
            # Fallback: chọn ngôn ngữ khác
            for lang in ["en", "vi", "ja"]:
                if lang != exclude_lang:
                    return lang

        return detected

    def create_translate_fn(
        self,
        source_lang: str,
        target_lang: str,
        glossary_manager: object | None = None,
    ) -> Callable[[str], str]:
        """Tạo hàm dịch đã bind sẵn ngôn ngữ và glossary.

        Args:
            source_lang: Mã ngôn ngữ nguồn.
            target_lang: Mã ngôn ngữ đích.
            glossary_manager: GlossaryManager instance (tuỳ chọn).

        Returns:
            Hàm translate_fn(text) -> str.
        """
        def translate_fn(text: str) -> str:
            if not text or not text.strip():
                return text

            placeholders: dict[str, str] = {}

            # Áp dụng glossary trước khi dịch
            if glossary_manager is not None:
                text, placeholders = glossary_manager.apply_pre_translate(
                    text, source_lang, target_lang
                )

            # Dịch bằng Argos
            translated = self.translate(text, source_lang, target_lang)

            # Khôi phục glossary
            if placeholders:
                translated = glossary_manager.apply_post_translate(
                    translated, placeholders
                )

            return translated

        return translate_fn

    @staticmethod
    def _get_required_pairs(source_lang: str, target_lang: str) -> list[tuple[str, str]]:
        """Xác định các cặp model cần thiết.

        Args:
            source_lang: Mã ngôn ngữ nguồn.
            target_lang: Mã ngôn ngữ đích.

        Returns:
            Danh sách cặp (source, target) cần cài đặt.
        """
        if (source_lang, target_lang) in _DIRECT_PAIRS:
            return [(source_lang, target_lang)]

        # Pivot qua English
        pairs = []
        if source_lang != "en":
            pairs.append((source_lang, "en"))
        if target_lang != "en":
            pairs.append(("en", target_lang))
        return pairs
