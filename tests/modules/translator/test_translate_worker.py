"""Test TranslateWorker output filename sanitization."""

import pytest

from src.modules.translator.translate_worker import TranslateWorker


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        (
            "thử nghiệm\n    ⟦2⟧ về các kỹ năng của claude",
            "thử nghiệm ⟦2⟧ về các kỹ năng của claude",
        ),
        ("report\t2026", "report 2026"),
        ("report. ", "report"),
        ("CON", "translated_CON"),
        ("nul.txt", "translated_nul.txt"),
        ('<>:"/\\|?*', "translated"),
    ],
)
def test_sanitize_filename(raw_name: str, expected: str) -> None:
    assert TranslateWorker._sanitize_filename(raw_name) == expected


def test_sanitize_filename_limits_length() -> None:
    assert len(TranslateWorker._sanitize_filename("a" * 300)) == 180
