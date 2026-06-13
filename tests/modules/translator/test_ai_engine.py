"""Test AIEngine batch parsing."""

from src.modules.translator.ai_engine import AIEngine


def test_parse_numbered_response_accepts_indented_markers() -> None:
    response = (
        "⟦1⟧ thử nghiệm\n"
        "    ⟦2⟧ về các kỹ năng của claude"
    )

    parsed = AIEngine._parse_numbered_response(response, 2)

    assert parsed == {
        1: "thử nghiệm",
        2: "về các kỹ năng của claude",
    }


def test_parse_numbered_response_preserves_multiline_item() -> None:
    response = (
        "⟦1⟧ dòng đầu\n"
        "dòng thứ hai\n"
        "\t⟦2⟧ mục tiếp theo"
    )

    parsed = AIEngine._parse_numbered_response(response, 2)

    assert parsed[1] == "dòng đầu\ndòng thứ hai"
    assert parsed[2] == "mục tiếp theo"
