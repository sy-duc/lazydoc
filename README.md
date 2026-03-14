# LazyDoc — Máy xay tài liệu

Ứng dụng desktop hỗ trợ tổng hợp và dịch thuật tài liệu đa định dạng sử dụng AI.

## Yêu cầu

- Python 3.10+
- Hệ điều hành: Windows 10+ (ưu tiên), macOS, Linux

## Cài đặt

### 1. Clone dự án

```bash
git clone <repo-url>
cd lazydoc
```

### 2. Tạo môi trường ảo

```bash
python -m venv venv
```

### 3. Kích hoạt môi trường ảo

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python src/main.py
```

## Cấu trúc dự án

```
lazydoc/
├── docs/                       # Tài liệu dự án
├── src/
│   ├── main.py                 # Entry point
│   ├── ui/                     # Giao diện PySide6
│   ├── modules/                # Module nghiệp vụ
│   │   ├── summarizer/         # Module tổng hợp
│   │   ├── translator/         # Module dịch thuật
│   │   └── glossary/           # Module bảng thuật ngữ
│   ├── providers/              # AI Provider (Gemini, OpenAI, Claude)
│   ├── processors/             # File Processor (extract nội dung)
│   ├── core/                   # Core services (config, db, i18n, encryption)
│   └── assets/                 # Icon, animation, file ngôn ngữ
├── config/                     # File cấu hình
├── tests/                      # Unit test
└── scripts/                    # Script đóng gói
```

## Chạy test

```bash
pytest tests/
```
