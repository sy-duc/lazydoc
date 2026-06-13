"""Test dữ liệu phiên bản hiển thị trong AboutDialog."""

from src.ui.dialogs.about_dialog import APP_VERSION, RELEASE_DATE, _RELEASE_NOTES


def test_current_release_has_version_date_and_notes() -> None:
    assert APP_VERSION
    assert RELEASE_DATE
    assert _RELEASE_NOTES["Tính năng mới"]
    assert _RELEASE_NOTES["Cải tiến"]
