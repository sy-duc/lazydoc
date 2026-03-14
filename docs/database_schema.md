# LazyDoc — Thiết kế Database (SQLite)

## 1. Tổng quan

Sử dụng **một file SQLite duy nhất** (`lazydoc.db`) lưu trong thư mục dữ liệu ứng dụng (AppData trên Windows).
Không cần cài đặt database server, phù hợp ứng dụng cá nhân.

---

## 2. Sơ đồ bảng

```
┌──────────────┐     ┌──────────────────┐
│  ai_provider │     │     glossary     │
├──────────────┤     ├──────────────────┤
│ id (PK)      │     │ id (PK)          │
│ name         │     │ lang_from        │
│ api_key_enc  │     │ term_from        │
│ is_active    │     │ lang_to          │
│ created_at   │     │ term_to          │
│ updated_at   │     │ created_at       │
└──────────────┘     │ updated_at       │
                     └──────────────────┘

┌──────────────┐
│   settings   │
├──────────────┤
│ key (PK)     │
│ value        │
│ updated_at   │
└──────────────┘
```

---

## 3. Chi tiết từng bảng

### 3.1. `ai_provider` — Quản lý AI Provider

Lưu thông tin và API key (đã mã hóa) của từng provider.

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | ID tự tăng |
| `name` | TEXT | UNIQUE NOT NULL | Tên provider (gemini, openai, claude) |
| `api_key_enc` | TEXT | NULL | API key đã mã hóa (Fernet). NULL nếu chưa nhập |
| `is_active` | INTEGER | NOT NULL DEFAULT 0 | 1 = đang được chọn sử dụng. Chỉ 1 provider active tại một thời điểm |
| `created_at` | TEXT | NOT NULL | Thời điểm tạo (ISO 8601) |
| `updated_at` | TEXT | NOT NULL | Thời điểm cập nhật cuối (ISO 8601) |

**Dữ liệu khởi tạo mặc định:**

| name | is_active |
|---|---|
| gemini | 1 |
| openai | 0 |
| claude | 0 |

**Lưu ý bảo mật:**
- `api_key_enc` được mã hóa bằng Fernet (symmetric encryption).
- Key mã hóa derive từ machine-specific identifier (không hardcode).
- Khi hiển thị trên UI: chỉ hiện `***...***` + 4 ký tự cuối.

---

### 3.2. `glossary` — Bảng thuật ngữ

Lưu mapping thuật ngữ giữa các cặp ngôn ngữ. Hỗ trợ hai chiều.

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | ID tự tăng |
| `lang_from` | TEXT | NOT NULL | Mã ngôn ngữ nguồn (vi, en, ja) |
| `term_from` | TEXT | NOT NULL | Thuật ngữ nguồn |
| `lang_to` | TEXT | NOT NULL | Mã ngôn ngữ đích (vi, en, ja) |
| `term_to` | TEXT | NOT NULL | Thuật ngữ đích |
| `created_at` | TEXT | NOT NULL | Thời điểm tạo (ISO 8601) |
| `updated_at` | TEXT | NOT NULL | Thời điểm cập nhật cuối (ISO 8601) |

**Ràng buộc:**
- UNIQUE(`lang_from`, `term_from`, `lang_to`) — mỗi thuật ngữ chỉ có 1 mapping cho mỗi cặp ngôn ngữ.

**Cơ chế hai chiều:**
- Khi tra cứu thuật ngữ để dịch từ ngôn ngữ A → B:
  - Tìm trong bảng record có `lang_from = A, lang_to = B`.
  - **Đồng thời** tìm record có `lang_from = B, lang_to = A` rồi đảo ngược (`term_to` ↔ `term_from`).
- Không lưu trùng 2 chiều — chỉ lưu 1 record, tra cứu cả 2 hướng.

**Index:**
```sql
CREATE INDEX idx_glossary_lookup
ON glossary(lang_from, lang_to, term_from);

CREATE INDEX idx_glossary_reverse
ON glossary(lang_to, lang_from, term_to);
```

**Format CSV import/export:**
```csv
lang_from,term_from,lang_to,term_to
en,Machine Learning,vi,Học máy
en,Artificial Intelligence,ja,人工知能
vi,Cơ sở dữ liệu,en,Database
```

---

### 3.3. `settings` — Cài đặt ứng dụng

Lưu các cài đặt dạng key-value.

| Cột | Kiểu | Ràng buộc | Mô tả |
|---|---|---|---|
| `key` | TEXT | PRIMARY KEY | Tên cài đặt |
| `value` | TEXT | NOT NULL | Giá trị (JSON string nếu cần lưu object) |
| `updated_at` | TEXT | NOT NULL | Thời điểm cập nhật cuối (ISO 8601) |

**Các key dự kiến:**

| Key | Giá trị mặc định | Mô tả |
|---|---|---|
| `app_language` | `"vi"` | Ngôn ngữ giao diện |
| `active_provider` | `"gemini"` | Provider đang sử dụng (redundant với `ai_provider.is_active` nhưng truy xuất nhanh hơn) |

---

## 4. Migration

- Sử dụng bảng `schema_version` để theo dõi phiên bản database.
- Khi ứng dụng khởi động: kiểm tra version → chạy migration nếu cần.

```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
```

---

## 5. File cấu hình (ngoài SQLite)

Các giá trị ít thay đổi, người dùng sửa trực tiếp bằng text editor, lưu trong file `config.yaml` hoặc `config.json`:

| Cấu hình | Mô tả | Ví dụ |
|---|---|---|
| `pricing.<provider>.<model>.input` | Giá token input (USD per 1M tokens) | `0.15` |
| `pricing.<provider>.<model>.output` | Giá token output (USD per 1M tokens) | `0.60` |
| `chunking.chunk_size` | Kích thước mỗi chunk (tokens) | `100000` |
| `chunking.overlap_size` | Kích thước overlap giữa các chunk (tokens) | `500` |
| `downloads_dir` | Thư mục tải về (mặc định auto-detect) | `null` (auto) |
