# Handoff Report — Phase 3, Step 3.2: Triển khai từng Processor

## Tổng quan

Đã triển khai **7 processor** cho tất cả định dạng file được hỗ trợ, bao gồm xử lý **shapes text** (XML parsing), **images nhúng**, **merge cells**, **group shapes**. Kèm **logic demo trên UI** để kiểm chứng trực tiếp.

---

## Các file đã tạo/sửa

| File | Hành động | Mô tả |
|---|---|---|
| `src/processors/txt_processor.py` | **Tạo mới** | Đọc file .txt (UTF-8, fallback latin-1) |
| `src/processors/csv_processor.py` | **Tạo mới** | Đọc file .csv, auto-detect delimiter, giữ cấu trúc bảng |
| `src/processors/excel_processor.py` | **Tạo mới** | Đọc .xlsx/.xls, nhiều sheet, merge cells, shapes (XML), images |
| `src/processors/word_processor.py` | **Tạo mới** | Đọc .docx, bảng, hình ảnh, shapes/textbox (XML). .doc cần LibreOffice |
| `src/processors/powerpoint_processor.py` | **Tạo mới** | Đọc .pptx, slides, shapes (bao gồm group shapes), notes, images |
| `src/processors/pdf_processor.py` | **Tạo mới** | Đọc .pdf (pdfplumber), text + bảng + hình ảnh |
| `src/processors/image_processor.py` | **Tạo mới** | Đọc ảnh (Pillow), chuẩn bị bytes cho AI vision |
| `src/processors/xml_shapes.py` | **Tạo mới** | Utility chung: parse XML từ ZIP để extract shapes text + images |
| `src/ui/main_window.py` | **Sửa** | Demo: bấm "Xay" → extract → hiển thị text + shapes + images trên UI |
| `tests/processors/test_processors.py` | **Tạo mới** | 23 unit test cho tất cả processor |
| `tests/processors/test_xml_shapes.py` | **Tạo mới** | 11 unit test cho XML shapes extraction |

---

## Xử lý đặc biệt theo loại file

| Loại file | Case đặc biệt | Cách xử lý |
|---|---|---|
| **Excel .xlsx** | Shapes (textbox, callout, ...) | Parse XML: zipfile → `xl/drawings/*.xml` → `<xdr:sp>` → `<a:t>` |
| **Excel .xlsx** | Images nhúng | Extract từ `xl/media/` trong ZIP |
| **Excel .xlsx** | Merge cells | Openpyxl: lấy giá trị cell góc trên trái, áp cho toàn bộ range |
| **Excel .xlsx** | Nhiều sheet | Extract từng sheet riêng, mapping drawing → sheet |
| **Excel .xls** | (hạn chế) | xlrd chỉ đọc cell data, không hỗ trợ shapes/images |
| **Word .docx** | Shapes/Textbox | Parse XML: `word/document.xml` → `<wps:txbx>` → `<w:t>` và `<w:drawing>` → `<a:t>` |
| **Word .docx** | Images | Extract qua python-docx relationships |
| **Word .docx** | Bảng biểu | Extract qua python-docx, giữ cấu trúc hàng/cột |
| **PowerPoint .pptx** | Group shapes | Đệ quy duyệt shapes bên trong group (`shape_type == 6`) |
| **PowerPoint .pptx** | Images | Extract qua python-pptx `shape.image.blob` |
| **PowerPoint .pptx** | Speaker notes | Extract từ `notes_text_frame` |
| **PDF** | Bảng biểu | pdfplumber `extract_tables()` |
| **PDF** | Images | Crop vùng ảnh trên page → PNG bytes |
| **Image** | RGBA/Palette | Chuyển sang RGB trước khi lưu PNG bytes |

---

## Kết quả test

```
61 passed in 1.62s
```

Chạy test: `source venv/bin/activate && python -m pytest tests/processors/ -v`

---

## Test trên giao diện

### Cách test

1. Chạy ứng dụng:
   ```bash
   source venv/bin/activate && python src/main.py
   ```

2. **Kéo thả file** vào vùng máy xay

3. **Bấm nút "Xay"** (⚡)

### Kết quả mong đợi trên UI

| Thành phần | Khi bấm "Xay" |
|---|---|
| **Máy xay** | "Extracting..." → animation hoàn tất |
| **Cột Trạng thái** | ✓ (thành công) hoặc ✗ (thất bại) |
| **Cột Ý nghĩa** | Metadata: sheets, shapes, images, pages, ... |
| **Vùng tóm tắt** | Nội dung text + section `[Shapes (N)]` + `[Images: N file(s)]` |

### Kịch bản test gợi ý

| Kịch bản | File test | Kiểm tra trên UI |
|---|---|---|
| Excel có shapes | File .xlsx có textbox/callout | Ý nghĩa hiện `shapes: N`, summary hiện `[Shapes (N)]` với text |
| Excel có ảnh nhúng | File .xlsx có Insert Image | Ý nghĩa hiện `images: N`, summary hiện `[Images: N file(s)]` |
| Excel merge cells | File .xlsx có ô gộp | Summary hiện đúng giá trị ô gộp |
| Excel nhiều sheet | File .xlsx 3+ sheet | Ý nghĩa hiện `sheets: 3, sheet_names: ...` |
| Word có textbox | File .docx có Insert Text Box | Ý nghĩa hiện `shapes: N` |
| Word có bảng + ảnh | File .docx | Ý nghĩa hiện `tables: Y, images: Z` |
| PPT có shapes | File .pptx có arrow/callout với text | Summary hiện `[Shapes]` |
| PPT có group shapes | File .pptx có Group (chọn nhiều shapes → Group) | Text trong group vẫn được extract |
| PDF có bảng | File .pdf có bảng biểu | Ý nghĩa hiện `tables: Y` |
| File ảnh | .png/.jpg | Ý nghĩa hiện `width: X, height: Y` |
| Không chọn file | Bỏ tick → Xay | Thông báo "Chưa có file nào" |

---

## Bước tiếp theo

**Step 3.3**: Extract Module logic — điều phối processor, cache kết quả, chạy async (QThread), hỗ trợ cancel.
