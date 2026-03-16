# Handoff Report — Phase 3, Step 3.1: File Processor Interface + Factory

## Tổng quan

Đã triển khai xong **abstract interface** cho File Processor và **Factory pattern** để tạo processor phù hợp theo extension file.

---

## Các file đã tạo/sửa

| File | Hành động | Mô tả |
|---|---|---|
| `src/processors/base.py` | **Tạo mới** | Định nghĩa `ExtractedContent` (dataclass) và `FileProcessor` (abstract class) |
| `src/processors/factory.py` | **Tạo mới** | `ProcessorFactory` — nhận file path → trả về processor phù hợp (lazy import) |
| `src/processors/__init__.py` | **Cập nhật** | Export public API: `ExtractedContent`, `FileProcessor`, `ProcessorFactory` |
| `tests/processors/__init__.py` | **Tạo mới** | Package init cho test |
| `tests/processors/test_base.py` | **Tạo mới** | 13 unit test cho `ExtractedContent` và `FileProcessor` |
| `tests/processors/test_factory.py` | **Tạo mới** | 14 unit test cho `ProcessorFactory` |

---

## Chi tiết triển khai

### 1. `ExtractedContent` (dataclass)
Cấu trúc dữ liệu chuẩn cho kết quả trích xuất, bao gồm:
- `text_content`: nội dung text theo section (dict[str, str])
- `tables`: bảng biểu theo section (dict[str, list[list[list[str]]]])
- `shapes_text`: text từ shapes theo section (dict[str, list[str]])
- `images`: hình ảnh dạng bytes để gửi AI vision (dict[str, bytes])
- `metadata`: thông tin bổ sung (dict[str, str | int])
- Property `has_content` và method `get_full_text()` hỗ trợ kiểm tra/ghép nội dung

### 2. `FileProcessor` (abstract class)
Interface bắt buộc mỗi processor triển khai:
- `supported_extensions` (abstract property): danh sách extension hỗ trợ
- `extract(file_path)` (abstract method): trích xuất nội dung
- `can_process(file_path)`: kiểm tra file có xử lý được không
- `validate_file(file_path)`: kiểm tra file tồn tại + đúng extension

### 3. `ProcessorFactory`
- Mapping extension → processor type dựa trên `SUPPORTED_EXTENSIONS`
- **Lazy import**: chỉ import processor module khi cần, tránh load toàn bộ thư viện lúc khởi động
- `get_processor(file_path)` → trả về instance processor phù hợp
- `is_supported(file_path)` → kiểm tra nhanh
- `get_supported_extensions()` → liệt kê tất cả extension

---

## Kết quả test

```
27 passed in 0.17s
```

Chạy test: `source venv/bin/activate && python -m pytest tests/processors/ -v`

---

## Có thể test gì sau khi triển khai

### 1. Chạy toàn bộ unit test
```bash
source venv/bin/activate && python -m pytest tests/processors/ -v
```

### 2. Test thủ công trong Python REPL
```python
from src.processors import ProcessorFactory, ExtractedContent, FileProcessor

# Kiểm tra danh sách extension hỗ trợ
ProcessorFactory.get_supported_extensions()
# → ['.bmp', '.csv', '.doc', '.docx', '.gif', '.jpeg', '.jpg', '.pdf', '.png', '.ppt', '.pptx', '.txt', '.xls', '.xlsx']

# Kiểm tra file có được hỗ trợ không
ProcessorFactory.is_supported("report.xlsx")  # True
ProcessorFactory.is_supported("music.mp3")    # False

# Thử get processor cho file không hỗ trợ → raise ValueError
ProcessorFactory.get_processor("file.mp3")
# → ValueError: Định dạng '.mp3' không được hỗ trợ...
```

> **Lưu ý**: `ProcessorFactory.get_processor()` cho các file hỗ trợ (ví dụ `.txt`, `.xlsx`) sẽ raise `ImportError` vì các processor cụ thể (TxtProcessor, ExcelProcessor, ...) chưa được triển khai — đây là nội dung của **Step 3.2**.

---

## Bước tiếp theo

**Step 3.2**: Triển khai từng processor cụ thể (TxtProcessor, CsvProcessor, ExcelProcessor, WordProcessor, PowerPointProcessor, PdfProcessor, ImageProcessor).
