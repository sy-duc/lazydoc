"""Test thông báo lỗi thân thiện dùng chung."""

import errno

from src.core.error_messages import FILE_ACCESS_ERROR_MESSAGE, format_file_error


def test_format_permission_error() -> None:
    assert format_file_error(PermissionError("Permission denied")) == (
        FILE_ACCESS_ERROR_MESSAGE
    )


def test_format_eacces_os_error() -> None:
    error = OSError(errno.EACCES, "Access denied")
    assert format_file_error(error) == FILE_ACCESS_ERROR_MESSAGE


def test_format_other_error_keeps_original_message() -> None:
    assert format_file_error(ValueError("File lỗi")) == "File lỗi"
