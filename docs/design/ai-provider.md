# Thiết kế chi tiết — Module AI Provider

## 1. Tổng quan

Module AI Provider triển khai **Strategy Pattern** để cho phép chuyển đổi giữa các AI provider (Gemini, OpenAI, Claude) tại runtime. Module gồm 6 thành phần chính:

```
src/providers/
├── __init__.py              # Export công khai
├── base.py                  # Abstract interface + prompt builders
├── gemini_provider.py       # Triển khai cho Google Gemini
├── openai_provider.py       # Triển khai cho OpenAI
├── claude_provider.py       # Triển khai cho Anthropic Claude
├── token_counter.py         # Đếm token + tính chi phí realtime
└── provider_manager.py      # Quản lý vòng đời provider
```

---

## 2. Kiến trúc

### 2.1. Class Diagram

```
                    ┌───────────────────────┐
                    │    ProviderManager     │
                    │  (QObject, Singleton)  │
                    ├───────────────────────┤
                    │ - _current_provider   │
                    │ - _token_counter      │
                    │ - _db                 │
                    │ - _encryption         │
                    ├───────────────────────┤
                    │ + load_active_provider│
                    │ + switch_provider()   │
                    │ + validate_api_key()  │
                    │ + get_provider_status │
                    └──────────┬────────────┘
                               │ sở hữu
                    ┌──────────▼────────────┐
                    │     BaseProvider       │
                    │     (Abstract)         │
                    ├───────────────────────┤
                    │ + summarize()  *      │
                    │ + translate()  *      │
                    │ + describe_image() *  │
                    │ + validate_key()  *   │
                    │ # _build_*_prompt()   │
                    └──────────┬────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼──────┐
    │ GeminiProvider │ │OpenAIProvider│ │ClaudeProvider│
    │                │ │              │ │              │
    │ google-genai   │ │ openai SDK   │ │ anthropic    │
    │ SDK            │ │              │ │ SDK          │
    └────────────────┘ └──────────────┘ └──────────────┘
```

### 2.2. Data Flow

```
UI Layer (bấm Xay/Dịch)
    │
    ▼
ProviderManager.provider
    │
    ▼
BaseProvider.summarize() / translate() / describe_image()
    │  (Generator[StreamChunk])
    ▼
Yield từng StreamChunk ──► UI hiển thị typing effect
    │
    ▼
StreamChunk(is_final=True) chứa usage
    │
    ▼
TokenCounter.add_usage() ──► emit usage_updated ──► CostTracker UI
```

---

## 3. Chi tiết từng thành phần

### 3.1. BaseProvider (`base.py`)

**Vai trò**: Định nghĩa interface chung cho tất cả provider.

**Các method abstract** (bắt buộc triển khai):

| Method | Mô tả | Input | Output |
|---|---|---|---|
| `summarize()` | Tổng hợp nội dung | content, system_prompt | Generator[StreamChunk] |
| `translate()` | Dịch nội dung | content, target_lang, domain, style, context, glossary | Generator[StreamChunk] |
| `describe_image()` | Mô tả hình ảnh (vision) | image_data (bytes), prompt | Generator[StreamChunk] |
| `validate_key()` | Kiểm tra API key | — | bool |

**Các method helper** (đã triển khai sẵn trong base):

| Method | Mô tả |
|---|---|
| `_build_summarize_prompt()` | Tạo system + user prompt cho tổng hợp |
| `_build_translate_prompt()` | Tạo prompt cho dịch (kèm domain, style, glossary, context) |
| `_build_image_prompt()` | Tạo prompt cho vision |

**Thiết kế prompt dịch thuật**: Prompt được xây dựng từ nhiều phần tùy chọn:
- Ngôn ngữ đích (bắt buộc)
- Ngôn ngữ nguồn (tùy chọn, tự detect nếu không có)
- Domain/lĩnh vực chuyên môn
- Văn phong dịch
- Ngữ cảnh từ kết quả tổng hợp (context)
- Bảng thuật ngữ bắt buộc (glossary)

**Dataclass**:

- `StreamChunk`: Một phần nhỏ trong streaming response. Chứa `text`, `input_tokens`, `output_tokens`, `is_final`.
- `AIResponse`: Kết quả phản hồi đầy đủ (dùng khi cần ghép toàn bộ response).

### 3.2. GeminiProvider (`gemini_provider.py`)

**SDK**: `google-generativeai` (google.generativeai)

**Cách streaming hoạt động**:
1. Tạo `GenerativeModel` với `system_instruction` (cho summarize/translate).
2. Gọi `generate_content(stream=True)`.
3. Lặp qua response, mỗi chunk yield `StreamChunk(text=chunk.text)`.
4. Sau khi stream xong, đọc `response.usage_metadata` để lấy `prompt_token_count` và `candidates_token_count`.
5. Yield chunk cuối với `is_final=True` kèm usage.

**Đặc thù Gemini**:
- System prompt truyền qua `system_instruction` khi tạo model.
- Image truyền dạng `inline_data` (base64).
- Validate key bằng `genai.list_models()` (API nhẹ).

### 3.3. OpenAIProvider (`openai_provider.py`)

**SDK**: `openai` (OpenAI Python SDK)

**Cách streaming hoạt động**:
1. Tạo `OpenAI` client.
2. Gọi `chat.completions.create(stream=True, stream_options={"include_usage": True})`.
3. Lặp qua stream, yield text từ `chunk.choices[0].delta.content`.
4. Chunk cuối (khi `chunk.usage` không None) chứa `prompt_tokens` và `completion_tokens`.

**Đặc thù OpenAI**:
- System prompt qua message role `system`.
- Image truyền dạng `image_url` với data URL base64.
- `stream_options={"include_usage": True}` để nhận usage trong streaming.
- Validate key bằng `models.list()`.

### 3.4. ClaudeProvider (`claude_provider.py`)

**SDK**: `anthropic`

**Cách streaming hoạt động**:
1. Tạo `Anthropic` client.
2. Dùng context manager `messages.stream(...)`.
3. Lặp qua `stream.text_stream` để yield text.
4. Sau khi stream xong, gọi `stream.get_final_message()` để lấy usage.

**Đặc thù Claude**:
- System prompt truyền qua parameter `system` (không phải message).
- Image truyền dạng `source.type = "base64"`.
- Bắt buộc `max_tokens` trong mỗi request.
- Validate key bằng gửi request nhỏ (`max_tokens=1`).

### 3.5. TokenCounter (`token_counter.py`)

**Vai trò**: Đếm token tích lũy và tính chi phí realtime.

**Cách hoạt động**:
1. Nhận `add_usage(provider_name, model, input_tokens, output_tokens)` sau mỗi lần gọi API.
2. Đọc giá token từ `config.yaml` (USD per 1M tokens).
3. Tính chi phí: `cost = (tokens / 1_000_000) * price_per_1M`.
4. Cộng dồn vào `UsageStats`.
5. Emit signal `usage_updated(total_tokens, total_cost)` → UI CostTracker cập nhật.

**Hàm `estimate_tokens()`**: Ước tính token đơn giản cho chunking:
- ASCII: ~4 ký tự = 1 token
- Non-ASCII (Việt, CJK): ~2 ký tự = 1 token

### 3.6. ProviderManager (`provider_manager.py`)

**Vai trò**: Quản lý toàn bộ vòng đời provider.

**Chức năng chính**:

| Method | Mô tả |
|---|---|
| `load_active_provider()` | Đọc provider active từ DB, giải mã key, khởi tạo instance |
| `switch_provider(name)` | Chuyển provider active, cập nhật DB, khởi tạo instance mới |
| `validate_api_key(name, key)` | Tạo provider tạm, gọi validate_key() |
| `get_provider_status()` | Trả về trạng thái (has_key, is_active) cho tất cả provider |

**Luồng load provider**:
```
load_active_provider()
    │
    ├── Query DB: SELECT name, api_key_enc WHERE is_active=1
    │
    ├── Decrypt api_key_enc bằng EncryptionManager
    │
    ├── Khởi tạo provider class (GeminiProvider/OpenAIProvider/ClaudeProvider)
    │
    └── Gán vào self._current_provider
```

**Luồng switch provider**:
```
switch_provider("claude")
    │
    ├── Kiểm tra tên provider hợp lệ
    │
    ├── Query DB lấy api_key_enc
    │
    ├── UPDATE DB: is_active=0 cho tất cả, is_active=1 cho provider mới
    │
    ├── Khởi tạo provider instance mới
    │
    └── Emit signal provider_changed("claude")
```

---

## 4. Signals (Observer Pattern)

| Component | Signal | Params | Mục đích |
|---|---|---|---|
| `TokenCounter` | `usage_updated` | (int tokens, float cost) | UI CostTracker cập nhật realtime |
| `ProviderManager` | `provider_changed` | (str name) | UI Settings cập nhật provider hiện tại |
| `ProviderManager` | `validation_result` | (bool valid, str msg) | UI hiển thị kết quả validate key |

---

## 5. Streaming Protocol

Tất cả provider đều trả về `Generator[StreamChunk]`:

```
StreamChunk(text="Đây là ")         ← Text chunk 1
StreamChunk(text="nội dung ")       ← Text chunk 2
StreamChunk(text="tổng hợp.")      ← Text chunk 3
StreamChunk(                        ← Final chunk (usage)
    is_final=True,
    input_tokens=500,
    output_tokens=150,
)
```

**Quy ước**:
- Chunk có `text` ≠ "" → hiển thị typing effect.
- Chunk có `is_final=True` → kết thúc, lấy token usage.
- Chunk cuối có thể có `text` rỗng (chỉ chứa usage).

---

## 6. Kết nối UI (Step 4.3 + 4.4)

### 6.1. Luồng cấu hình API key qua Settings Dialog

```
Người dùng mở Settings Dialog
    │
    ├── Chọn provider (Gemini/OpenAI/Claude)
    │
    ├── Nhập API key mới
    │
    ├── Bấm "Lưu"
    │       │
    │       ├── Gọi ProviderManager.validate_api_key(name, key)
    │       │       │
    │       │       ├── Tạo provider tạm với key mới
    │       │       │
    │       │       └── Gọi API thật (list_models / messages.create)
    │       │               │
    │       │               ├── Thành công → lưu key mã hóa vào DB
    │       │               │
    │       │               └── Thất bại → hiện thông báo lỗi, không lưu
    │       │
    │       ├── Cập nhật is_active trong DB
    │       │
    │       └── ProviderManager.load_active_provider() → khởi tạo provider mới
    │
    └── Provider sẵn sàng cho Phase 5/6
```

### 6.2. Kết nối chi phí realtime

```
main.py
    │
    ├── Khởi tạo ProviderManager
    │
    └── MainWindow(provider_manager=...)
            │
            ├── _setup_provider_connections()
            │       │
            │       └── TokenCounter.usage_updated ──► CostTracker.update_cost
            │
            └── Khi Phase 5/6 gọi API:
                    │
                    ├── Provider yield StreamChunk(is_final=True, tokens...)
                    │
                    ├── TokenCounter.add_usage() → tính chi phí
                    │
                    └── Emit usage_updated → CostTracker hiển thị realtime
```

### 6.3. Các file UI đã sửa

| File | Thay đổi |
|---|---|
| `main.py` | Khởi tạo ProviderManager, truyền vào MainWindow |
| `main_window.py` | Nhận ProviderManager, kết nối TokenCounter → CostTracker |
| `settings_dialog.py` | Validate API key bằng gọi API thật trước khi lưu, reload provider sau khi lưu |
| `vi.json` / `en.json` | Thêm key i18n: `validating`, `validation_failed` |

---

## 7. Bảo mật

- API key **chỉ tồn tại ở dạng plaintext trong memory** (sau khi giải mã).
- **Không log** API key — chỉ log tên provider và model.
- API key truyền trực tiếp vào SDK client, không lưu file.
- EncryptionManager sử dụng Fernet (AES-128-CBC) với key derive từ machine ID.

---

## 7. Testing

Tất cả test sử dụng **mock** để không gọi API thật:

| File test | Số test | Nội dung |
|---|---|---|
| `test_base.py` | 21 | Interface, dataclass, prompt builders |
| `test_providers.py` | 14 | Mock SDK cho từng provider (streaming, validate) |
| `test_token_counter.py` | 11 | Tính chi phí, signal, reset |
| `test_provider_manager.py` | 16 | Load/switch/validate, DB interaction |
| **Tổng** | **66** | |
