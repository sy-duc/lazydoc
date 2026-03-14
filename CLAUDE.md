# LazyDoc Tool — Project Configuration

## Quy tắc chung

### Ngôn ngữ tài liệu
- Tất cả file tài liệu (*.md) trong dự án phải được viết bằng **tiếng Việt có dấu** (Unicode).
- Áp dụng cho cả code comments.
- Ngoại trừ: variable names vẫn dùng tiếng Anh theo coding standards.

### Phân tách phạm vi tài liệu
Mỗi loại tài liệu (docs) có scope riêng, tránh trùng lặp nội dung.

---

## Định hướng vai trò của từng loại tài liệu

| File | Vai trò | Nội dung chính |
|---|---|---|
| `docs/idea.md` | Ý tưởng gốc | Bối cảnh ban đầu, brainstorm. Chỉ mang tính tham khảo, không phải đặc tả chính thức. |
| `docs/requirement_spec.md` | Đặc tả yêu cầu | Yêu cầu chức năng, phi chức năng, luồng xử lý, UI. Đây là nguồn sự thật (source of truth) về "cần làm gì". |
| `docs/architecture.md` | Kiến trúc hệ thống | Các layer, module, design patterns, luồng dữ liệu, xử lý bất đồng bộ, cache. |
| `docs/tech_stack.md` | Công nghệ sử dụng | Ngôn ngữ, framework, thư viện, cấu trúc thư mục, yêu cầu hệ thống. |
| `docs/database_schema.md` | Thiết kế database | Cấu trúc bảng SQLite, index, migration, file config. |
| `docs/summary_output_template.md` | Mẫu output tổng hợp | Cấu trúc file .md chi tiết khi người dùng tải báo cáo tổng hợp. |
| `docs/development_plan.md` | Kế hoạch phát triển | Các phase/step triển khai, thứ tự ưu tiên. |

### Nguyên tắc tham chiếu
- Khi cần hiểu **"làm gì"** → đọc `requirement_spec.md`.
- Khi cần hiểu **"làm như thế nào"** → đọc `architecture.md` + `tech_stack.md`.
- Khi cần hiểu **"dữ liệu lưu ở đâu"** → đọc `database_schema.md`.
- Khi cần hiểu **"thứ tự làm"** → đọc `development_plan.md`.
- **Không** trùng lặp nội dung giữa các file. Nếu cần tham chiếu → ghi link đến file tương ứng.

---

## Code Quality

### Coding Standards
- **Ngôn ngữ code**: Python 3.10+.
- **Style guide**: PEP 8. Sử dụng type hints cho tất cả function signatures.
- **Docstrings**: Google style, viết bằng tiếng Việt.
- **Comments**: tiếng Việt, chỉ comment khi logic không tự giải thích được.
- **Variable/function/class names**: tiếng Anh, snake_case cho function/variable, PascalCase cho class.

### Cấu trúc code
- Tách rõ UI layer và business logic — UI không chứa logic xử lý.
- Mỗi module là một package riêng trong `src/modules/`.
- Mỗi file processor là một class riêng trong `src/processors/`.
- Mỗi AI provider là một class riêng trong `src/providers/`.
- Shared utilities đặt trong `src/core/`.

### Testing
- Unit test cho business logic (modules, processors, providers).
- Sử dụng pytest.
- File test đặt trong thư mục `tests/`, cấu trúc mirror với `src/`.

### Error Handling
- Không nuốt exception — log rõ ràng và thông báo cho UI.
- Xử lý graceful khi file không đọc được, API lỗi, hoặc network timeout.
- Khi cancel giữa chừng: dọn dẹp tài nguyên, giữ lại kết quả đã hoàn thành.

### Bảo mật
- API key phải mã hóa trước khi lưu SQLite.
- Không log API key, không hiển thị plaintext trên UI.
- Không hardcode secret hoặc key trong source code.
