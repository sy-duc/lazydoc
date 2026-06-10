"""ContentFilter — Tier-1 filtering để loại bỏ nội dung rác trước khi gửi AI."""

import re

# Dòng kẻ trang trí: chỉ gồm các ký tự -, =, _, *, ~, #, +, . và khoảng trắng, dài ≥ 3
_DECORATIVE_RE = re.compile(r'^[\-=_*~#+. ]{3,}$')

# Số trang độc lập: chỉ chứa chữ số (bao gồm số La Mã không được hỗ trợ ở đây)
_PAGE_NUM_RE = re.compile(r'^\d+$')


def filter_excel_table(rows: list[list[str]]) -> list[list[str]]:
    """Lọc bỏ hàng toàn rỗng và cột toàn rỗng khỏi dữ liệu bảng Excel.

    Args:
        rows: Dữ liệu bảng dạng list[list[str]].

    Returns:
        Dữ liệu sau khi lọc. Thứ tự hàng/cột còn lại được giữ nguyên.
    """
    # Bước 1: bỏ hàng toàn rỗng
    filtered = [r for r in rows if any(c.strip() for c in r)]
    if not filtered:
        return filtered

    # Bước 2: bỏ cột mà tất cả hàng đều rỗng tại vị trí đó
    n_cols = max(len(r) for r in filtered)
    empty_col_indices = {
        col
        for col in range(n_cols)
        if all(col >= len(r) or not r[col].strip() for r in filtered)
    }
    if not empty_col_indices:
        return filtered

    return [
        [cell for i, cell in enumerate(r) if i not in empty_col_indices]
        for r in filtered
    ]


def filter_text_lines(lines: list[str]) -> list[str]:
    """Lọc bỏ dòng kẻ trang trí và số trang độc lập.

    Chỉ áp dụng filter an toàn (Tier 1): không xóa dòng có nội dung thực.

    Args:
        lines: Danh sách dòng text (chưa strip).

    Returns:
        Danh sách sau khi lọc, giữ nguyên nội dung còn lại.
    """
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _DECORATIVE_RE.match(stripped):
            continue
        if _PAGE_NUM_RE.match(stripped):
            continue
        result.append(line)
    return result
