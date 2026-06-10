"""Thông báo lỗi thân thiện dùng chung cho các thao tác với file."""

import errno

FILE_ACCESS_ERROR_MESSAGE = (
    "File đang được mở hoặc bị ứng dụng khác khóa. "
    "Vui lòng đóng file rồi thử lại."
)


def format_file_error(error: Exception) -> str:
    """Chuyển lỗi truy cập file thường gặp thành thông báo dễ hiểu."""
    winerror = getattr(error, "winerror", None)
    if (
        isinstance(error, PermissionError)
        or getattr(error, "errno", None) in {errno.EACCES, errno.EPERM}
        or winerror in {5, 32, 33}
    ):
        return FILE_ACCESS_ERROR_MESSAGE
    return str(error)
