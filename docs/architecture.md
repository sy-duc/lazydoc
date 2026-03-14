# LazyDoc — Kiến trúc hệ thống

## 1. Tổng quan kiến trúc

Thiết kế theo mô hình **module hóa**, các module độc lập giao tiếp qua interface rõ ràng.
Dễ mở rộng thêm module mới mà không ảnh hưởng module hiện tại.

```
┌─────────────────────────────────────────────────┐
│                    UI Layer                      │
│         (PySide6: màn hình, dialog)              │
└──────────┬──────────┬──────────┬────────────────┘
           │          │          │
     ┌─────▼───┐  ┌───▼────┐  ┌─▼────────┐
     │ Extract  │  │Summary │  │Translate │   ← Module Layer
     └───┬─────┘  └──┬─────┘  └─┬────────┘
         │           │          │
    ┌────▼───────────▼──────────▼─────────┐
    │           Core Services             │
    │  (Config, DB, i18n, Encryption)     │
    └────┬──────────┬─────────────────────┘
         │          │
   ┌─────▼───┐  ┌──▼──────────┐
   │   File   │  │ AI Provider │   ← Service Layer
   │Processor │  │  (Strategy) │
   └──────────┘  └─────────────┘
```

---

## 2. Các layer

### 2.1. UI Layer
- Chịu trách nhiệm hiển thị giao diện, nhận tương tác người dùng.
- Không chứa business logic — chỉ gọi xuống Module Layer.
- Xử lý: drag & drop, hiệu ứng animation, typing effect, realtime progress.

### 2.2. Module Layer
3 module nghiệp vụ chính:

| Module | Trách nhiệm |
|---|---|
| **Extract** | Đọc và trích xuất nội dung từ các định dạng file (text, shapes, hình ảnh, bảng biểu). Cache kết quả để các module khác tái sử dụng. |
| **Summary (Tổng hợp)** | Nhận nội dung từ Extract → chunking → gọi AI tổng hợp → tạo output (tóm tắt + file .md chi tiết). |
| **Translate (Dịch thuật)** | Nhận nội dung từ Extract → gom batch → dịch (Argos offline hoặc AI thông minh) → ghi file output giữ nguyên định dạng. Bao gồm quản lý **bảng thuật ngữ** (CRUD, import/export CSV). |

### 2.3. Service Layer

**File Processor:**
- Nhận file đầu vào → extract nội dung (text, shapes, metadata).
- Mỗi định dạng file có một processor riêng (Excel, Word, PDF, ...) triển khai chung một interface.
- Được gọi bởi module Extract.

**AI Provider:**
- Abstract interface (Strategy Pattern) cho các AI provider.
- Mỗi provider (Gemini, OpenAI, Claude) triển khai cùng interface.
- Chuyển đổi provider tại runtime bằng cách thay đổi strategy.

### 2.4. Core Services
- **Config Manager**: đọc/ghi file cấu hình (giá token, chunking, ...).
- **Database Manager**: truy cập SQLite (thuật ngữ, API key, settings).
- **i18n Manager**: quản lý ngôn ngữ giao diện (Việt/Anh).
- **Encryption**: mã hóa/giải mã API key.

---

## 3. Luồng dữ liệu chính

### 3.1. Luồng Tổng hợp

```
Drag & Drop file
    │
    ▼
UI ghi nhận file (tên + size) vào bảng
    │
    ▼ [Người dùng bấm "Xay"]
    │
Extract Module
    ├── Gọi File Processor: extract nội dung từng file (async)
    │       ├── Cache kết quả extract vào memory
    │       └── Cập nhật UI: trạng thái từng file (✓/✗)
    │
    ▼
Summary Module
    ├── Nhận nội dung từ Extract cache
    │
    ├── Chunking: chia nội dung lớn thành chunks (nếu cần)
    │
    ├── Gọi AI Provider: tổng hợp thông tin
    │       ├── Stream response → UI hiển thị typing effect
    │       └── Cập nhật realtime: token + chi phí
    │
    └── Tạo output:
            ├── Tóm tắt ngắn → hiển thị trên UI
            └── File .md chi tiết → sẵn sàng tải về Downloads
```

### 3.2. Luồng Dịch thuật

```
Người dùng checked file → bấm "Dịch" → dialog Dịch thuật
    │
    ▼
Extract Module
    ├── Kiểm tra cache (nếu đã extract trước → tái sử dụng)
    │       └── Nếu chưa → gọi File Processor extract
    │
    ▼
Translate Module
    ├── Lấy ngữ cảnh tổng hợp từ Summary (nếu có) làm context
    │
    ├── Lấy bảng thuật ngữ liên quan (sub-module Glossary)
    │
    ├── Gom batch nội dung theo chiến lược (sheet/section/slide)
    │
    ├── Chọn engine dịch:
    │       ├── Mặc định → Argos Translate (offline, miễn phí)
    │       └── Thông minh → AI Provider API (kèm domain + văn phong)
    │
    ├── Dịch từng batch:
    │       ├── Áp dụng bảng thuật ngữ (replace trước/sau khi dịch)
    │       └── Cập nhật realtime: tiến độ %, token, chi phí
    │
    └── Ghi file output (giữ nguyên định dạng gốc)
            ├── Dịch tên file + tên sheet
            └── Tự động tải về Downloads
```

---

## 4. Design Patterns sử dụng

| Pattern | Áp dụng cho | Mục đích |
|---|---|---|
| **Strategy** | AI Provider | Chuyển đổi provider tại runtime |
| **Factory** | File Processor | Tạo processor phù hợp theo extension file |
| **Observer** | UI ↔ Module | Cập nhật realtime (progress, token, chi phí) mà không coupling |
| **Template Method** | Luồng xử lý module | Chuẩn hóa các bước extract → process → output |
| **Singleton** | Config, DB Manager | Đảm bảo chỉ có 1 instance quản lý tài nguyên dùng chung |

---

## 5. Xử lý bất đồng bộ

- Toàn bộ xử lý nặng (extract, gọi API, dịch) chạy trên **QThread** hoặc **asyncio + QAsync**.
- UI thread chỉ nhận signal cập nhật từ worker thread.
- Hỗ trợ **hủy (cancel)** tại bất kỳ thời điểm nào:
  - Worker kiểm tra flag cancel trước mỗi bước xử lý.
  - Khi cancel → giữ lại kết quả đã hoàn thành, dọn dẹp tài nguyên.

---

## 6. Quản lý cache

| Loại cache | Phạm vi | Mục đích |
|---|---|---|
| Extract cache | Trong phiên (memory) | Tái sử dụng nội dung extract giữa Summary và Translate |
| Ngữ cảnh tổng hợp | Trong phiên (memory) | Cung cấp context cho prompt dịch thông minh |

- Cache tự động xóa khi đóng ứng dụng (không persist).
- Cache bị invalidate khi người dùng xóa file khỏi bảng.
