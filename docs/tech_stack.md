# LazyDoc — Công nghệ sử dụng

## 1. Tổng quan

| Thành phần | Công nghệ | Phiên bản tối thiểu | Lý do chọn |
|---|---|---|---|
| Ngôn ngữ | Python | 3.10+ | Hệ sinh thái thư viện phong phú, dễ đóng gói |
| GUI Framework | PySide6 (Qt6) | 6.5+ | Cross-platform, hỗ trợ animation/drag-drop tốt, license LGPL |
| Database | SQLite | Tích hợp sẵn Python | Nhẹ, không cần cài đặt, phù hợp ứng dụng cá nhân |
| Dịch offline | Argos Translate | 1.9+ | Nhẹ, chạy CPU, hỗ trợ Việt/Anh/Nhật, open source |
| Đóng gói | PyInstaller hoặc Nuitka | — | Tạo file .exe độc lập không cần cài Python |

---

## 2. Thư viện xử lý file

| Định dạng | Thư viện | Ghi chú |
|---|---|---|
| Excel (`.xlsx`) | openpyxl | Đọc/ghi xlsx, hỗ trợ shapes, merge cells, nhiều sheet |
| Excel (`.xls`) | xlrd | Đọc định dạng Excel cũ |
| Word (`.docx`) | python-docx | Đọc/ghi docx, hỗ trợ bảng, hình ảnh |
| Word (`.doc`) | python-docx + libreoffice CLI | Chuyển đổi .doc → .docx rồi xử lý |
| PowerPoint (`.pptx`) | python-pptx | Đọc/ghi pptx, hỗ trợ shapes, notes |
| PowerPoint (`.ppt`) | python-pptx + libreoffice CLI | Chuyển đổi .ppt → .pptx rồi xử lý |
| PDF | pdfplumber hoặc PyMuPDF | Extract text + bảng biểu |
| PDF (scan/OCR) | pytesseract + Pillow | OCR cho PDF dạng hình ảnh |
| CSV | csv (stdlib) | Tích hợp sẵn Python |
| TXT | built-in | Tích hợp sẵn Python |
| Hình ảnh | Pillow | Đọc/xử lý ảnh trước khi gửi AI vision |

---

## 3. Thư viện AI Provider

| Provider | Thư viện / SDK | Ghi chú |
|---|---|---|
| Gemini | google-generativeai | SDK chính thức của Google |
| OpenAI | openai | SDK chính thức, hỗ trợ vision |
| Claude | anthropic | SDK chính thức của Anthropic |

---

## 4. Thư viện hỗ trợ khác

| Thư viện | Mục đích |
|---|---|
| tiktoken / tokenizers | Đếm token để tính chi phí realtime |
| cryptography (Fernet) | Mã hóa API key trong SQLite |
| pathlib (stdlib) | Xử lý đường dẫn file cross-platform |
| platformdirs | Xác định thư mục Downloads, AppData trên các OS |

---

## 5. Cấu trúc thư mục dự án (dự kiến)

```
lazydoc/
├── docs/                       # Tài liệu dự án
├── src/
│   ├── main.py                 # Entry point
│   ├── ui/                     # PySide6 UI (màn hình, dialog)
│   ├── modules/
│   │   ├── summarizer/         # Module tổng hợp
│   │   ├── translator/         # Module dịch thuật
│   │   └── glossary/           # Module bảng thuật ngữ
│   ├── providers/              # AI Provider (interface + implementations)
│   ├── processors/             # File Processor (extract nội dung)
│   ├── core/                   # Shared logic (config, db, i18n, encryption)
│   └── assets/                 # Icon, animation, i18n files
├── config/                     # File cấu hình (giá token, chunking, ...)
├── tests/                      # Unit test & integration test
└── scripts/                    # Script đóng gói, build
```

---

## 6. Yêu cầu hệ thống

| Yêu cầu | Tối thiểu |
|---|---|
| OS | Windows 10+ (ưu tiên), có thể mở rộng macOS/Linux |
| RAM | 4 GB (Argos Translate cần ~1-2 GB khi chạy) |
| Disk | ~500 MB (bao gồm model Argos Translate) |
| GPU | Không yêu cầu (chạy CPU) |
| Mạng | Cần kết nối internet khi dùng AI Provider API |
