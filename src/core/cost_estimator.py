"""Ước tính số lượt API call trước khi xử lý."""

from dataclasses import dataclass, field
from pathlib import Path

from src.core.config import ConfigManager
from src.processors.base import ExtractedContent
from src.providers.token_counter import estimate_tokens

_TEXT_EXTS = {".txt", ".md", ".csv"}


@dataclass
class CostEstimate:
    """Kết quả ước tính số lượt API call.

    Attributes:
        file_count: Số file cần xử lý.
        total_size_bytes: Tổng dung lượng file.
        image_count: Số ảnh nhúng cần gọi vision API.
        api_calls: Số lượt gọi API ước tính (text + vision).
        is_rough: True khi ước tính từ file size (chưa extract).
    """

    file_count: int
    total_size_bytes: int
    image_count: int
    api_calls: int
    is_rough: bool = field(default=False)


def estimate_from_contents(
    contents: dict[Path, ExtractedContent],
    mode: str,
) -> CostEstimate:
    """Ước tính số lượt API call từ ExtractedContent đã extract.

    Args:
        contents: Dict {file_path: ExtractedContent}.
        mode: "summary" hoặc "translate".

    Returns:
        CostEstimate với is_rough=False.
    """
    config = ConfigManager()

    file_count = len(contents)
    total_size = sum(c.file_size for c in contents.values())

    text_tokens = sum(_file_text_tokens(c) for c in contents.values())
    chunk_size = config.get("chunking.chunk_size", 100_000)

    if mode == "summary":
        image_count = sum(len(c.images) for c in contents.values())
        chunk_count = max(0, (text_tokens - 1) // chunk_size) if text_tokens > chunk_size else 0
        api_calls = 1 + chunk_count + image_count
    else:  # translate — ảnh không được xử lý qua vision API
        image_count = 0
        batch_count = max(1, (text_tokens + 7_999) // 8_000)
        api_calls = batch_count

    return CostEstimate(
        file_count=file_count,
        total_size_bytes=total_size,
        image_count=image_count,
        api_calls=api_calls,
        is_rough=False,
    )


def estimate_from_files(
    files: list[Path],
    mode: str,
) -> CostEstimate:
    """Ước tính thô từ file size khi chưa có ExtractedContent.

    Args:
        files: Danh sách file cần xử lý.
        mode: "summary" hoặc "translate".

    Returns:
        CostEstimate với is_rough=True.
    """
    file_count = len(files)
    total_size = 0
    text_tokens = 0

    for f in files:
        if not f.exists():
            continue
        size = f.stat().st_size
        total_size += size
        coeff = 0.25 if f.suffix.lower() in _TEXT_EXTS else 0.10
        text_tokens += int(size * coeff)

    batch_count = max(1, (text_tokens + 7_999) // 8_000)
    api_calls = batch_count

    return CostEstimate(
        file_count=file_count,
        total_size_bytes=total_size,
        image_count=0,
        api_calls=api_calls,
        is_rough=True,
    )


def _file_text_tokens(content: ExtractedContent) -> int:
    """Ước tính token phần văn bản + bảng + shapes của một file."""
    parts = [f"=== File: {content.file_name} ==="]

    full_text = content.get_full_text()
    if full_text:
        parts.append(full_text)

    for section, tables in content.tables.items():
        for table in tables:
            rows = [" | ".join(str(c) for c in row) for row in table]
            if rows:
                parts.append(f"[Bảng - {section}]\n" + "\n".join(rows))

    for section, texts in content.shapes_text.items():
        if texts:
            parts.append(f"[Shapes - {section}]\n" + "\n".join(texts))

    return estimate_tokens("\n\n".join(parts))
