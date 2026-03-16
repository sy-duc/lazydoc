"""ImageProcessor — Chuẩn bị dữ liệu hình ảnh cho AI vision."""

import logging
from pathlib import Path

from src.processors.base import ExtractedContent, FileProcessor

logger = logging.getLogger(__name__)


class ImageProcessor(FileProcessor):
    """Processor cho file hình ảnh (.png, .jpg, .jpeg, .bmp, .gif).

    Đọc ảnh và chuẩn bị dữ liệu bytes để gửi cho AI vision mô tả nội dung.
    """

    @property
    def supported_extensions(self) -> list[str]:
        return [".png", ".jpg", ".jpeg", ".bmp", ".gif"]

    def extract(self, file_path: Path) -> ExtractedContent:
        """Đọc file hình ảnh và chuẩn bị cho AI vision.

        Args:
            file_path: Đường dẫn file hình ảnh.

        Returns:
            ExtractedContent với images chứa dữ liệu ảnh.
        """
        self.validate_file(file_path)

        from PIL import Image
        import io

        # Đọc ảnh và lấy metadata
        with Image.open(file_path) as img:
            width, height = img.size
            img_format = img.format or file_path.suffix.lstrip(".").upper()

            # Chuyển sang PNG bytes để gửi AI
            buf = io.BytesIO()
            # Chuyển RGBA/P → RGB nếu cần
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        content = ExtractedContent(
            file_path=file_path,
            file_name=file_path.name,
            file_size=file_path.stat().st_size,
            text_content={"main": f"[Hình ảnh: {file_path.name} ({width}x{height})]"},
            images={file_path.name: image_bytes},
            metadata={
                "width": width,
                "height": height,
                "format": img_format,
            },
        )

        logger.info(
            "Đã extract file ảnh: %s (%dx%d, %s)",
            file_path.name, width, height, img_format,
        )
        return content
