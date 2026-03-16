"""FileWriter — Abstract interface cho các bộ ghi file dịch."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class FileWriter(ABC):
    """Abstract interface cho các bộ ghi file dịch.

    Mỗi loại file cần triển khai một class con kế thừa từ FileWriter.
    Writer mở file gốc, dịch text in-place, lưu file mới giữ nguyên định dạng.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Danh sách phần mở rộng file mà writer này hỗ trợ.

        Returns:
            List các extension (bao gồm dấu chấm).
        """
        ...

    @abstractmethod
    def write_translated(
        self,
        source_path: Path,
        output_path: Path,
        translate_fn: Callable[[str], str],
    ) -> None:
        """Dịch và ghi file giữ nguyên định dạng.

        Mở file gốc, duyệt qua các phần tử text, dịch bằng translate_fn,
        lưu file mới tại output_path.

        Args:
            source_path: Đường dẫn file gốc.
            output_path: Đường dẫn file đầu ra.
            translate_fn: Hàm dịch text (str) -> str.

        Raises:
            FileNotFoundError: Nếu file gốc không tồn tại.
            RuntimeError: Nếu xảy ra lỗi khi ghi file.
        """
        ...

    def can_write(self, file_path: Path) -> bool:
        """Kiểm tra writer này có xử lý được file không.

        Args:
            file_path: Đường dẫn file.

        Returns:
            True nếu extension nằm trong danh sách hỗ trợ.
        """
        return file_path.suffix.lower() in self.supported_extensions
