"""Test dữ liệu phiên bản hiển thị trong AboutDialog."""

from src.ui.dialogs.about_dialog import APP_VERSION, RELEASE_DATE, RELEASE_SUMMARY


def test_current_release_has_version_date_and_notes() -> None:
    assert APP_VERSION
    assert RELEASE_DATE
    assert "phiên bản đầu tiên" in RELEASE_SUMMARY
