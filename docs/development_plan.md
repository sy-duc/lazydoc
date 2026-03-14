# LazyDoc — Kế hoạch phát triển

## Tổng quan

Các phase được sắp xếp theo thứ tự phụ thuộc: phase sau dựa trên kết quả phase trước.
Mỗi phase kết thúc bằng một phiên bản chạy được (có thể test thủ công).

---

## Phase 1: Khởi tạo dự án

### Step 1.1: Tạo source base
- Khởi tạo cấu trúc thư mục theo `docs/tech_stack.md`.
- Tạo `venv` + `requirements.txt` với toàn bộ dependencies.
- Tạo `README.md` hướng dẫn setup môi trường (clone, tạo venv, cài dependencies, chạy app).
- Tạo file `config.yaml` mẫu (giá token, chunking config).
- Tạo script `run.py` hoặc `main.py` làm entry point.

### Step 1.2: Khởi tạo Core Services
- **Database Manager**: kết nối SQLite, tạo bảng theo `docs/database_schema.md`, migration.
- **Config Manager**: đọc/ghi `config.yaml`.
- **Encryption**: mã hóa/giải mã API key (Fernet).
- **i18n Manager**: cơ chế load ngôn ngữ Việt/Anh, file translation strings.

**Kết quả Phase 1**: Chạy `python main.py` không lỗi, database được khởi tạo, config được load.

---

## Phase 2: UI cơ bản

### Step 2.1: Màn hình chính (Main Window)
- Thanh tiêu đề (chỉ icon đóng, không phóng to/thu nhỏ).
- Hoạt ảnh "máy xay tài liệu" (placeholder ban đầu, hoàn thiện animation sau).
- Vùng drag & drop file.
- Bảng danh sách file (cột: checkbox, tên file, size, trạng thái, ý nghĩa, ngôn ngữ, icon xóa).
- Vùng tóm tắt kết quả (có hiệu ứng typing).
- Vùng theo dõi chi phí realtime + button Stop.
- Thanh công cụ: button Xay, Dịch, icon Setting, button Hướng dẫn, Thông tin.

### Step 2.2: Dialog Setting API Key
- Label provider hiện tại.
- Selectbox chọn provider + trường nhập API key.
- Button Chọn + validation.

### Step 2.3: Dialog Dịch thuật
- Danh sách file cần dịch.
- Selectbox ngôn ngữ đích.
- Button Bảng thuật ngữ, Mở rộng, Dịch.
- Vùng mở rộng (domain, văn phong, chế độ dịch).
- Thanh tiến độ + chi phí realtime + button Stop.

### Step 2.4: Dialog Bảng thuật ngữ
- Selectbox ngôn ngữ + vùng nhập thuật ngữ.
- Ô tìm kiếm + hiển thị kết quả + icon xóa.
- Button Lưu, Import CSV, Export CSV.

**Kết quả Phase 2**: Giao diện đầy đủ, các dialog mở/đóng đúng, drag & drop file hiển thị trong bảng. Chưa có logic xử lý.

---

## Phase 3: Module Extract

### Step 3.1: File Processor interface + Factory
- Định nghĩa abstract interface cho File Processor.
- Tạo Factory: nhận file path → trả về processor phù hợp theo extension.

### Step 3.2: Triển khai từng processor
- **TxtProcessor**: đọc file .txt.
- **CsvProcessor**: đọc file .csv, giữ cấu trúc bảng.
- **ExcelProcessor**: đọc .xlsx/.xls, hỗ trợ nhiều sheet, merge cells, shapes.
- **WordProcessor**: đọc .docx/.doc, hỗ trợ bảng, hình ảnh, shapes.
- **PowerPointProcessor**: đọc .pptx/.ppt, hỗ trợ slides, shapes, notes.
- **PdfProcessor**: đọc .pdf (text-based + OCR).
- **ImageProcessor**: đọc hình ảnh (chuẩn bị data cho AI vision).

### Step 3.3: Module Extract logic
- Điều phối gọi processor cho từng file.
- Cache kết quả extract trong memory.
- Chạy async (QThread), hỗ trợ cancel.
- Emit signal cập nhật UI (trạng thái từng file).

### Step 3.4: Kết nối Extract với UI
- Bấm Xay/Dịch → trigger Extract → cập nhật bảng file (trạng thái, hiển thị loading).

**Kết quả Phase 3**: Kéo file vào → bấm Xay → extract thành công → bảng hiển thị ✓/✗. Chưa có tổng hợp/dịch.

---

## Phase 4: Module AI Provider

### Step 4.1: Abstract interface
- Định nghĩa interface chung: `summarize()`, `translate()`, `describe_image()`, `count_tokens()`.

### Step 4.2: Triển khai từng provider
- **GeminiProvider**: sử dụng google-generativeai SDK.
- **OpenAIProvider**: sử dụng openai SDK.
- **ClaudeProvider**: sử dụng anthropic SDK.
- Hỗ trợ streaming response cho tất cả provider.

### Step 4.3: Kết nối với UI Setting
- Lưu/đọc API key (mã hóa) từ SQLite.
- Chuyển đổi provider tại runtime.
- Validation API key.

### Step 4.4: Chi phí realtime
- Đếm token (tiktoken/tokenizers).
- Tính chi phí dựa trên config giá token.
- Emit signal cập nhật UI realtime.

**Kết quả Phase 4**: Cấu hình API key qua dialog → gọi API thành công → hiển thị chi phí realtime.

---

## Phase 5: Module Summary (Tổng hợp)

### Step 5.1: Logic tổng hợp
- Nhận nội dung từ Extract cache.
- Chunking: chia nội dung lớn, overlap, tổng hợp đệ quy.
- Gọi AI Provider tổng hợp (streaming).

### Step 5.2: Tạo output
- Tóm tắt ngắn → hiển thị trên UI (typing effect).
- File .md chi tiết theo template `docs/summary_output_template.md`.
- Tải file về Downloads.

### Step 5.3: Cập nhật bảng file
- Thêm ý nghĩa/mục đích từng file vào bảng.
- Hiển thị ngôn ngữ file (nếu không phải tiếng Việt).

### Step 5.4: Xử lý Stop giữa chừng
- Cancel → giữ lại kết quả đã xử lý → hiển thị tổng hợp partial.

**Kết quả Phase 5**: Kéo file → Xay → hiển thị tóm tắt (typing) + tải file .md chi tiết. Module tổng hợp hoàn chỉnh.

---

## Phase 6: Module Translate (Dịch thuật)

### Step 6.1: Tích hợp Argos Translate (chế độ Mặc định)
- Cài đặt, load model Argos cho Việt/Anh/Nhật.
- Dịch nội dung không quan tâm ngữ cảnh.

### Step 6.2: Dịch thông minh qua AI
- Gom batch theo chiến lược (sheet/section/slide).
- Tận dụng ngữ cảnh tổng hợp (nếu có) làm context prompt.
- Áp dụng domain + văn phong vào prompt.
- Streaming + chi phí realtime.

### Step 6.3: Bảng thuật ngữ (Glossary)
- CRUD thuật ngữ trong SQLite.
- Tra cứu hai chiều.
- Import/Export CSV.
- Áp dụng bảng thuật ngữ khi dịch (replace trước/sau).

### Step 6.4: Ghi file output
- Ghi lại file giữ nguyên định dạng gốc (Excel → Excel, Word → Word, ...).
- Dịch tên file + tên sheet.
- Tự động tải về Downloads.

### Step 6.5: Xử lý Stop giữa chừng
- Cancel → giữ lại file đã dịch xong → tải về.

**Kết quả Phase 6**: Chọn file → Dịch → file dịch tải về Downloads. Module dịch thuật hoàn chỉnh.

---

## Phase 7: Hoàn thiện & Đóng gói

### Step 7.1: Hoàn thiện UI/UX
- Hoạt ảnh máy xay tài liệu (rung, quay, hiệu ứng output).
- Trạng thái loading vui nhộn (Extracting..., Analysing..., Blending..., Translating...).
- Hiệu ứng typing cho vùng tóm tắt.
- I18n: hoàn thiện file translation Việt/Anh.

### Step 7.2: Error handling & Edge cases
- File không hỗ trợ → thông báo rõ.
- API lỗi / timeout → retry + thông báo.
- File rỗng, file quá lớn, file bị hỏng.
- Mất mạng khi đang gọi API.

### Step 7.3: Testing
- Unit test cho processors, providers, modules.
- Test thủ công với các loại file thực tế.

### Step 7.4: Đóng gói
- PyInstaller / Nuitka → file .exe.
- Bao gồm model Argos Translate.
- Test trên máy Windows sạch (không có Python).

**Kết quả Phase 7**: File .exe chạy độc lập, đầy đủ chức năng, sẵn sàng sử dụng.
