"""File Processor — Abstract interface cho các bộ xử lý file."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExtractedContent:
    """Kết quả trích xuất nội dung từ file.

    Attributes:
        file_path: Đường dẫn file gốc.
        file_name: Tên file.
        file_size: Kích thước file (bytes).
        text_content: Nội dung văn bản chính, tổ chức theo section.
            Key là tên section (sheet name, slide number, heading, ...).
            Value là nội dung text của section đó.
        tables: Danh sách bảng biểu, tổ chức theo section.
            Key là tên section, value là list các bảng (mỗi bảng là list[list[str]]).
        shapes_text: Text bên trong shapes, tổ chức theo section.
            Key là tên section, value là list các đoạn text từ shapes.
        images: Danh sách hình ảnh (bytes) để gửi AI vision.
            Key là mô tả vị trí, value là dữ liệu ảnh dạng bytes.
        metadata: Thông tin bổ sung (số trang, số sheet, ...).
    """

    file_path: Path
    file_name: str
    file_size: int
    text_content: dict[str, str] = field(default_factory=dict)
    tables: dict[str, list[list[list[str]]]] = field(default_factory=dict)
    shapes_text: dict[str, list[str]] = field(default_factory=dict)
    images: dict[str, bytes] = field(default_factory=dict)
    metadata: dict[str, str | int] = field(default_factory=dict)

    @property
    def has_content(self) -> bool:
        """Kiểm tra có nội dung nào được trích xuất không."""
        return bool(
            self.text_content
            or self.tables
            or self.shapes_text
            or self.images
        )

    def get_full_text(self) -> str:
        """Ghép toàn bộ text content thành một chuỗi duy nhất.

        Returns:
            Chuỗi text đã ghép, các section cách nhau bởi dòng trống.
        """
        parts: list[str] = []
        for section_name, content in self.text_content.items():
            if content.strip():
                parts.append(f"[{section_name}]\n{content}")
        return "\n\n".join(parts)


class FileProcessor(ABC):
    """Abstract interface cho các bộ xử lý file.

    Mỗi loại file (Excel, Word, PDF, ...) cần triển khai một class con
    kế thừa từ FileProcessor và implement method extract().
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Danh sách phần mở rộng file mà processor này hỗ trợ.

        Returns:
            List các extension (bao gồm dấu chấm), ví dụ: [".xlsx", ".xls"].
        """
        ...

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractedContent:
        """Trích xuất nội dung từ file.

        Args:
            file_path: Đường dẫn đến file cần xử lý.

        Returns:
            ExtractedContent chứa toàn bộ nội dung đã trích xuất.

        Raises:
            FileNotFoundError: Nếu file không tồn tại.
            ValueError: Nếu file không thuộc định dạng hỗ trợ.
            ProcessingError: Nếu xảy ra lỗi trong quá trình xử lý.
        """
        ...

    def can_process(self, file_path: Path) -> bool:
        """Kiểm tra processor này có xử lý được file không.

        Args:
            file_path: Đường dẫn file cần kiểm tra.

        Returns:
            True nếu extension của file nằm trong danh sách hỗ trợ.
        """
        return file_path.suffix.lower() in self.supported_extensions

    def validate_file(self, file_path: Path) -> None:
        """Kiểm tra file hợp lệ trước khi xử lý.

        Args:
            file_path: Đường dẫn file cần kiểm tra.

        Raises:
            FileNotFoundError: Nếu file không tồn tại.
            ValueError: Nếu extension không được hỗ trợ.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File không tồn tại: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Đường dẫn không phải file: {file_path}")
        if not self.can_process(file_path):
            raise ValueError(
                f"Định dạng '{file_path.suffix}' không được hỗ trợ. "
                f"Các định dạng hỗ trợ: {self.supported_extensions}"
            )
