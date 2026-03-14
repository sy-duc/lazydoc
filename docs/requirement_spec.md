# LazyDoc — Đặc tả yêu cầu

## 1. Tổng quan sản phẩm

### 1.1. Mô tả
LazyDoc là ứng dụng desktop cá nhân, kết hợp AI để:
- **Tổng hợp thông tin** từ nhiều loại tài liệu đầu vào thành báo cáo Markdown.
- **Dịch tài liệu** giữ nguyên định dạng gốc, hỗ trợ cả dịch offline và dịch thông minh qua AI.

### 1.2. Ngôn ngữ giao diện
- Hỗ trợ đa ngôn ngữ: Tiếng Việt (mặc định), Tiếng Anh.
- Sử dụng cơ chế i18n để dễ mở rộng thêm ngôn ngữ sau.

---

## 2. Định dạng file đầu vào

### 2.1. Danh sách định dạng hỗ trợ
| Định dạng | Phần mở rộng | Ghi chú |
|---|---|---|
| Excel | `.xlsx`, `.xls` | Hỗ trợ nhiều sheet, merge cells, shapes |
| Word | `.docx`, `.doc` | Hỗ trợ bảng, hình ảnh, shapes |
| PowerPoint | `.pptx`, `.ppt` | Hỗ trợ slide, shapes, speaker notes |
| PDF | `.pdf` | Hỗ trợ text-based và scan (OCR) |
| Văn bản thuần | `.txt` | |
| CSV | `.csv` | |
| Hình ảnh | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif` | Sử dụng AI vision để mô tả nội dung |

### 2.2. Yêu cầu extract
- **Text**: trích xuất toàn bộ nội dung văn bản.
- **Shapes** (Excel, Word, PowerPoint): extract text bên trong shapes để hiểu nội dung mô tả.
- **Hình ảnh/Biểu đồ**: sử dụng AI vision để tổng hợp ý nghĩa, mô tả nội dung.
- **Bảng biểu**: giữ cấu trúc hàng/cột khi extract.
- **Merge cells** (Excel): xử lý đúng giá trị ô gộp.
- **Nhiều sheet** (Excel): extract từng sheet riêng biệt.

---

## 3. Module Tổng hợp thông tin

### 3.1. Luồng xử lý
```
Người dùng kéo thả file vào giao diện
    ↓
Bảng hiển thị tên file + kích thước (chưa extract)
    ↓
Người dùng checked các file muốn tổng hợp → bấm nút "Xay"
    ↓
Bắt đầu tiến trình:
    Extract → Analysing → Blending → ...
    (hiển thị trạng thái vui nhộn kiểu Claude Code)
    ↓
Trong quá trình gọi API:
    Hiển thị realtime: token đã dùng + chi phí hiện tại
    Người dùng có thể bấm Stop bất kỳ lúc nào
    ↓
Xử lý xong → cập nhật trạng thái từng file (✓/✗)
    ↓
Hiển thị tóm tắt (typing effect) + button tải file chi tiết
```

### 3.2. Dừng giữa chừng (Stop)
- Khi người dùng bấm Stop, giữ lại toàn bộ kết quả đã xử lý được đến thời điểm đó.
- Các file chưa xử lý xong đánh trạng thái "Đã dừng".
- Kết quả tổng hợp chỉ bao gồm các file đã xử lý thành công.

### 3.3. Hiển thị kết quả tổng hợp
- **Tóm tắt ngắn**: hiển thị trực tiếp trên giao diện với **hiệu ứng typing** (streaming từng token như AI trả lời).
  - Tổng quan ý nghĩa, mục đích chung của toàn bộ file.
  - Nếu các file không liên quan nhau → thông báo rõ.
- **Button "Chi tiết"**: tải file `.md` chi tiết về thư mục **Downloads** của máy người dùng.
  - Cấu trúc file chi tiết: xem `docs/summary_output_template.md`.
- **Bảng file**: cập nhật thêm các cột sau khi tổng hợp:
  - Ý nghĩa/mục đích từng file.
  - Ngôn ngữ sử dụng trong file (chỉ hiển thị nếu file không phải tiếng Việt).

### 3.4. Xử lý file lớn (Chunking)
Khi nội dung file vượt quá context window của AI:
1. **Chia nhỏ** nội dung thành các chunk có overlap (để không mất ngữ cảnh giữa các đoạn).
2. **Tổng hợp từng chunk**: AI tạo bản tóm tắt cho mỗi chunk.
3. **Merge tổng hợp**: AI nhận toàn bộ bản tóm tắt các chunk → tạo bản tổng hợp cuối cùng.
4. Áp dụng đệ quy nếu tổng các bản tóm tắt vẫn vượt context window.

---

## 4. Module Dịch thuật

### 4.1. Luồng xử lý
```
Người dùng checked file cần dịch từ bảng file → bấm button "Dịch"
    ↓
Mở dialog Dịch thuật
    ↓
Chọn ngôn ngữ đích, cấu hình mở rộng (nếu cần)
    ↓
Bấm "Dịch" → bắt đầu tiến trình:
    Extracting → Translating → Writing → ...
    Hiển thị realtime: tiến độ %, token đã dùng, chi phí
    Người dùng có thể bấm Stop
    ↓
File dịch xong tự động tải về thư mục Downloads
```

### 4.2. Ngôn ngữ đích hỗ trợ
- Tiếng Việt
- Tiếng Anh
- Tiếng Nhật

### 4.3. Yêu cầu dịch
- **Giữ nguyên định dạng gốc**: Excel → Excel, Word → Word, PowerPoint → PowerPoint, v.v.
- **Dịch tên file**: tên file output được dịch sang ngôn ngữ đích.
- **Dịch tên sheet** (Excel): tên các sheet cũng được dịch.
- **Không dịch**: hình ảnh, biểu đồ (giữ nguyên).
- **Xử lý đặc biệt**: merge cells, shapes (dịch text bên trong, giữ nguyên cấu trúc).

### 4.4. Chế độ dịch
| Chế độ | Mô tả | Engine |
|---|---|---|
| Mặc định | Dịch nhanh, không quan tâm ngữ cảnh, miễn phí | Argos Translate (offline) |
| Thông minh | Dịch có ngữ cảnh, sử dụng domain + văn phong | AI Provider API |

### 4.5. Tùy chọn mở rộng (vùng "Mở rộng")
- **Domain**: lĩnh vực tài liệu (Mặc định, CNTT, Y tế, Pháp lý, Tài chính, Kỹ thuật, ...).
- **Văn phong**: phong cách dịch (Mặc định, Báo cáo, Súc tích, Bay bổng, ...).
- Các tùy chọn này chỉ có tác dụng khi chế độ dịch = "Thông minh".

### 4.6. Chiến lược gom batch khi dịch (chế độ Thông minh)
Gom nội dung theo đơn vị logic thay vì dịch từng cell/đoạn riêng lẻ, nhằm:
- Giảm overhead API (latency + token system prompt lặp lại).
- Cho AI hiểu ngữ cảnh giữa các phần liên quan → dịch sát nghĩa hơn.

| Loại nội dung | Chiến lược gom batch |
|---|---|
| Excel/CSV cells | Gom theo sheet, gửi dạng bảng (giữ cấu trúc hàng/cột). Sheet quá lớn → chia theo nhóm hàng, overlap vài hàng header. |
| Shapes | Gom tất cả shapes trong 1 sheet/slide thành 1 batch, kèm thông tin vị trí. |
| Word | Gom theo section/heading, mỗi section 1 batch. |
| PowerPoint | Gom theo slide, mỗi slide 1 batch (text boxes + shapes + notes). |

### 4.7. Tận dụng kết quả tổng hợp cho dịch thuật
Nếu người dùng đã "Xay" trước khi "Dịch":
- **Cache extract**: tái sử dụng nội dung đã extract, không cần extract lại.
- **Ngữ cảnh tổng hợp**: sử dụng mục đích/ý nghĩa file (từ kết quả tổng hợp) làm context cho prompt dịch → AI chọn từ vựng chính xác hơn mà không cần gửi thêm nội dung file khác.
  - Ví dụ: tổng hợp xong biết file là "Báo cáo tài chính Q3" → prompt dịch thêm: "Đây là báo cáo tài chính" → AI tự động chọn từ vựng tài chính phù hợp.

### 4.8. Bảng thuật ngữ
- **Lưu trữ**: SQLite, mỗi người dùng một bảng riêng.
- **Cấu trúc**: mapping giữa các cặp ngôn ngữ (Việt ↔ Anh, Việt ↔ Nhật, Anh ↔ Nhật).
- **Hai chiều**: khi đã mapping thuật ngữ A ↔ B, dịch từ ngôn ngữ nào sang ngôn ngữ nào đều áp dụng.
- **Thao tác**: thêm, sửa, xóa, tìm kiếm thuật ngữ.
- **Import/Export**: hỗ trợ CSV để chia sẻ bảng thuật ngữ.
- **Dialog bảng thuật ngữ**:
  - Selectbox chọn ngôn ngữ + vùng nhập thuật ngữ gốc và thuật ngữ đích.
  - Không hiển thị toàn bộ, chỉ hiển thị kết quả tìm kiếm kèm icon xóa.
  - Button Lưu để thêm/sửa.

---

## 5. Quản lý AI Provider

### 5.1. Danh sách AI Provider
| Provider | Ghi chú |
|---|---|
| Gemini | Mặc định |
| OpenAI | |
| Claude (Anthropic) | |

### 5.2. Cấu hình API key
- Mỗi provider có trường nhập API key riêng.
- Key được bảo mật (không lưu plaintext, không hiển thị trên UI).
- Không cho phép chọn provider nếu chưa nhập key.
- Nếu provider đã có key từ trước → cho phép chuyển đổi bình thường.

### 5.3. Theo dõi chi phí realtime
- Không ước tính trước (vì chưa biết nội dung trước khi extract).
- Khi bắt đầu gọi API → hiển thị realtime: token đã dùng, chi phí tích lũy.
- Giá per token cấu hình trong **file config** (sửa trực tiếp, không cần giao diện).
- Người dùng có thể Stop bất kỳ lúc nào nếu thấy chi phí quá cao.

---

## 6. Giao diện người dùng (UI)

### 6.1. Màn hình chính
- **Hoạt ảnh "máy xay tài liệu"**:
  - Vùng drag & drop file (kéo thả file vào "miệng máy"). Đây là phương thức nhập file duy nhất.
  - Khi đang xử lý: máy rung/quay kèm trạng thái vui nhộn (Extracting..., Analysing..., Blending..., v.v.).
  - Khi xong: hiệu ứng "ra output".
- **Bảng danh sách file**:
  - Cột: checkbox, tên file, kích thước (size), trạng thái (✓/✗/trống), ý nghĩa file (sau tổng hợp), ngôn ngữ (nếu không phải tiếng Việt), icon xóa.
  - Ban đầu khi kéo file vào: chỉ hiển thị tên file + size, các cột khác trống.
  - Sau khi xử lý: cập nhật trạng thái và thông tin bổ sung.
- **Vùng tóm tắt**: hiển thị tóm tắt ngắn với hiệu ứng typing + button "Chi tiết" (tải `.md`).
- **Vùng theo dõi chi phí**: hiển thị realtime token + chi phí khi đang gọi API, kèm button Stop.
- **Thanh công cụ**:
  - Button "Xay" (tổng hợp các file đã checked).
  - Button "Dịch" (chuyển sang dialog dịch thuật với các file đã checked).
  - Icon Setting (mở dialog cấu hình API key).
  - Button "Hướng dẫn", "Thông tin".
- **Thanh tiêu đề**: chỉ có icon ✗ đóng ứng dụng (không có phóng to/thu nhỏ).

### 6.2. Dialog Setting API Key
- Label hiển thị AI provider đang sử dụng.
- Selectbox chọn provider + trường nhập API key.
- Button "Chọn" để lưu và chuyển đổi provider.
- Validation: không cho lưu nếu key trống.

### 6.3. Dialog Dịch thuật
- Danh sách tên file cần dịch.
- Selectbox ngôn ngữ đích (Việt, Anh, Nhật).
- Button "Bảng thuật ngữ" → mở dialog bảng thuật ngữ.
- Button "Mở rộng" → hiển thị/ẩn vùng tùy chọn (domain, văn phong, chế độ dịch).
- Button "Dịch" → hiển thị tiến trình + chi phí realtime + button Stop.

### 6.4. Dialog Bảng thuật ngữ
- Selectbox chọn ngôn ngữ + vùng nhập thuật ngữ gốc và thuật ngữ đích.
- Button Lưu (thêm/sửa).
- Ô tìm kiếm → hiển thị kết quả kèm icon xóa.
- Button Import CSV, Export CSV.

---

## 7. Yêu cầu phi chức năng

### 7.1. Đóng gói & Phân phối
- Đóng gói thành file thực thi (.exe cho Windows) không cần cài Python.
- Bao gồm model dịch offline trong gói cài đặt.
- Dễ dàng sử dụng trên nhiều máy.

### 7.2. Hiệu năng
- Toàn bộ xử lý nặng (extract, gọi API) chạy async/thread riêng, không block UI.
- Hiển thị tiến độ và chi phí realtime.
- Quản lý bộ nhớ khi xử lý file lớn.

### 7.3. Bảo mật
- API key không lưu plaintext — sử dụng obfuscation hoặc mã hóa.
- Không gửi API key qua log hoặc hiển thị trên giao diện (ẩn bằng `***`).

### 7.4. UX
- Drag & drop là phương thức nhập file duy nhất.
- Trạng thái xử lý hiển thị vui nhộn, rõ ràng kiểu Claude Code.
- Kết quả tóm tắt hiển thị với hiệu ứng typing (streaming).
- Thông báo lỗi rõ ràng khi file không hỗ trợ hoặc xử lý thất bại.

---

## 8. Phạm vi ngoài (Out of Scope)

- Lịch sử phiên làm việc.
- Xem trước kết quả dịch trước khi lưu.
- Đề xuất thuật ngữ tự động từ AI.
- Google Translate (API không tương thích interface chung LLM).
- Giao diện chỉnh sửa giá token (sửa trực tiếp file config).
- Cho phép người dùng chọn thư mục lưu output (luôn lưu vào Downloads).
- Chọn file bằng dialog (chỉ hỗ trợ drag & drop).
