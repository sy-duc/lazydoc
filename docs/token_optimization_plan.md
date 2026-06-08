# Kế hoạch tối ưu xử lý & token cho API call

Tài liệu này mô tả phương án tối ưu chi phí và trải nghiệm cho hai module gọi AI Provider trong LazyDoc: **Summary (Xay)** và **Translate (Dịch — chế độ Smart)**.

---

## 1. Bối cảnh & mục tiêu

### 1.1. Vấn đề hiện tại

Pipeline tại hai module gọi AI đang chạy theo kiểu "brute-force" — extract toàn bộ file rồi đẩy thẳng vào API mà không có bước xác nhận với người dùng:

- **Summary**: [summary_worker.py](../src/modules/summarizer/summary_worker.py) extract → estimate token sơ bộ → chunking nếu vượt ngưỡng → gọi AI nhiều lần (1 lần cuối + N lần pre-summarize chunk + M lần mô tả ảnh).
- **Translate (smart mode)**: [translate_worker.py](../src/modules/translator/translate_worker.py) extract → batch theo sheet/section/slide → gọi AI cho từng batch.

Người dùng **không biết trước**:

- Tổng số token sẽ tiêu, quy ra USD/VND bao nhiêu.
- Mất bao lâu để xử lý.
- Có bao nhiêu API call phát sinh (đặc biệt khi file có nhiều hình ảnh nhúng).

Hệ quả: với file lớn hoặc file nhiều ảnh, người dùng dễ "vô tình" tốn chi phí cao mà không có cơ hội cân nhắc.

### 1.2. Mục tiêu

- **Minh bạch chi phí**: hiển thị ước tính tổng cost (USD/VND) + thời gian + số API call **trước khi** bắt đầu tiêu tốn API budget.
- **Trao quyền dừng**: người dùng xác nhận trước khi pipeline chạy.
- **Áp dụng đồng đều**: cả Summary và Translate (smart mode) đều dùng chung một confirmation dialog modal.
- **Giảm noise đầu vào**: lọc nội dung rác đơn giản trước khi đếm và gửi AI.

### 1.3. Phạm vi

| Trong phạm vi (phase này) | Ngoài phạm vi |
|---|---|
| Pre-flight estimation cho Summary | RAG-based Q&A với file lớn |
| Pre-flight estimation cho Translate (smart mode) | Two-phase Overview → Deep dive |
| Cải thiện độ chính xác token estimation | UI chọn section theo mục lục |
| Smart filtering — chỉ filter an toàn (Tier 1) | Rolling summary cho file cực lớn |
| Batch ảnh khi provider hỗ trợ | Filter có rủi ro mất data (nén bảng lớn, dedup cross-file) |
|  | Prompt caching (không đáng với Gemini default) |
|  | Translate chế độ default (Argos) — không gọi API |

---

## 2. Giải pháp chính: Pre-flight Estimation + User Confirmation

### 2.1. Luồng xử lý mới

**Summary (Xay)**

```
User checked file → bấm "Xay"
    ↓
Extract toàn bộ file đã chọn (không gọi AI)
    ↓
[MỚI] Estimate cost:
    - Đếm token input (text + tables + shapes)
    - Đếm số ảnh → ước tính cost vision API
    - Ước tính output token (chỉ dùng nội bộ để tính total cost)
    - Tính USD từ pricing trong config.yaml
    - Ước tính thời gian + số API call
    ↓
[MỚI] Hiển thị ConfirmationDialog (modal)
    ↓
"Tiếp tục" → vào pipeline summary hiện tại
"Hủy"      → dọn dẹp, giữ extract cache, không tốn API
```

**Translate (Dịch — chế độ Smart)**

```
User checked file → mở dialog Dịch thuật → chọn ngôn ngữ → bấm "Dịch"
    ↓
Extract toàn bộ file (nếu chưa có cache từ Summary)
    ↓
[MỚI] Estimate cost (giống Summary, heuristic output khác)
    ↓
[MỚI] Hiển thị ConfirmationDialog (dùng chung dialog modal với Summary)
    ↓
"Tiếp tục" → pipeline translate hiện tại
"Hủy"      → không tốn API
```

**Lưu ý**: Chế độ dịch **default (Argos)** không gọi API → bỏ qua estimation, chạy thẳng.

### 2.2. Cơ chế estimation

#### Token đầu vào

- Text/tables/shapes: dùng [`estimate_tokens()`](../src/providers/token_counter.py#L40) — cần cải thiện độ chính xác (xem [mục 3.1](#31-tăng-độ-chính-xác-token-estimation)).
- System prompt cố định: tính sẵn dựa trên template (~800 token cho Summary, ~300 token cho Translate smart).
- Mỗi ảnh: cộng thêm token tương ứng theo provider:
  - Gemini: ~258 token/ảnh.
  - Claude: tính theo công thức `(width × height) / 750`.
  - OpenAI gpt-4o: ~85 token base + 170/tile (low/high detail).

#### Token đầu ra (ước tính nội bộ, không hiển thị UI)

| Module | Heuristic | Lý do |
|---|---|---|
| Summary | `min(input × 0.20, 8000)` | Báo cáo chi tiết thường ~15-25% input, cap để tránh ước tính sai khi input cực lớn |
| Translate | `input × 1.10` | Bản dịch hơi dài hơn bản gốc, dao động theo cặp ngôn ngữ |

Đây là phần ước tính kém chính xác nhất (sai số ±50%) — vì vậy **không break down ra UI**, chỉ dùng để cộng vào tổng cost cuối cùng.

#### Số API call dự kiến

- **Summary**: `1 (báo cáo chính) + số ảnh + số chunk (nếu chunking)`.
- **Translate**: tổng số batch theo chiến lược gom batch ở [requirement_spec.md §4.6](./requirement_spec.md).

#### Chi phí USD

```
input_cost  = input_tokens  × pricing.input  / 1_000_000
output_cost = output_tokens × pricing.output / 1_000_000   (nội bộ)
image_cost  = image_count   × image_unit_cost
total_cost  = input_cost + output_cost + image_cost
```

Giá lấy từ [`pricing.{provider}.{model}`](../config/config.yaml). Quy ra VND theo `usd_to_vnd` cùng file.

#### Thời gian

Heuristic ban đầu: `~8 giây × số API call`. Hiển thị dạng dải để phản ánh sai số network/load. Tinh chỉnh sau khi có data thực tế từ logging.

### 2.3. UI Dialog xác nhận

**Vị trí thống nhất**: cả Summary và Translate dùng **cùng một modal dialog** (`ConfirmationDialog`).

- Summary: popup sau khi extract xong, trước khi bắt đầu summary pipeline.
- Translate: popup sau khi extract xong (gọi từ trong dialog Dịch thuật), trước khi `TranslateWorker` chạy.

**Bố cục**:

```
┌─ Ước tính chi phí ─────────────────────────────┐
│                                                 │
│  Số file:           3 file                      │
│  Dung lượng:        45 MB                       │
│  Số ảnh:            4 (sẽ gọi vision API)       │
│  Số API call:       ~5                          │
│                                                 │
│  Provider:          Gemini 2.5 Flash            │
│  Chi phí ước tính:  ~$0.42 (~10,800 VND)        │
│  Thời gian:         ~30-90 giây                 │
│                                                 │
│  ⚠ Đây là ước tính. Chi phí thực tế hiển thị    │
│    realtime khi đang chạy.                       │
│                                                 │
│  [☐] Không hỏi lại nếu chi phí < $0.10          │
│                                                 │
│               [ Hủy ]    [ Tiếp tục ]           │
└─────────────────────────────────────────────────┘
```

**Logic hiển thị**:

- Mặc định: luôn hiển thị.
- Nếu user đã tick "Không hỏi lại nếu chi phí < $X" trong lần trước và chi phí ước tính lần này dưới ngưỡng → bỏ qua dialog, vào thẳng pipeline.
- Ngưỡng cấu hình trong [config.yaml](../config/config.yaml):
  ```yaml
  confirmation:
    enabled: true
    skip_threshold_usd: 0.10
  ```

---

## 3. Cải tiến phụ trợ

### 3.1. Tăng độ chính xác token estimation — Self-calibration

Heuristic hiện tại (`4 chars/token ASCII, 2 chars/token non-ASCII`) sai lệch 15–30%. Thay vì tinh chỉnh thủ công, dùng cơ chế **tự hiệu chỉnh dựa trên data thực**: sau mỗi session thành công, so sánh token ước tính với token thực từ API response, cập nhật hệ số vào config.

#### Cấu trúc config

Thêm vào [config/config.yaml](../config/config.yaml):

```yaml
calibration:
  sessions_count: 0     # số session đã dùng để hiệu chỉnh
  gemini:
    input_ratio: 1.0    # actual / estimated, mặc định 1.0 (không hiệu chỉnh)
  claude:
    input_ratio: 1.0
  openai:
    input_ratio: 1.0
```

#### Cơ chế hoạt động

**Trước session**: nhân estimate với `input_ratio` từ config:

```python
raw_estimate = estimate_tokens(content)
ratio = config.get(f"calibration.{provider}.input_ratio", 1.0)
calibrated_estimate = int(raw_estimate * ratio)
```

**Sau session thành công** (không Stop, không lỗi): so sánh actual với estimated rồi cập nhật hệ số bằng **Exponential Moving Average**:

```python
ALPHA = 0.15   # 1 session ảnh hưởng 15% → ổn định sau ~15-20 session

def update_calibration(provider, actual_tokens, estimated_tokens):
    if estimated_tokens == 0:
        return
    ratio = max(0.5, min(2.0, actual_tokens / estimated_tokens))  # clamp outlier
    old_ratio = config.get(f"calibration.{provider}.input_ratio", 1.0)
    new_ratio = ALPHA * ratio + (1 - ALPHA) * old_ratio
    config.set(f"calibration.{provider}.input_ratio", round(new_ratio, 4))
    config.set("calibration.sessions_count",
               config.get("calibration.sessions_count", 0) + 1)
```

#### Tốc độ hội tụ

| Số session | Mức độ hiệu chỉnh | Sai số ước tính |
|---|---|---|
| 0 | Chưa hiệu chỉnh (ratio = 1.0) | ±20-30% |
| 5 | Bắt đầu cải thiện | ±10-15% |
| 15-20 | Ổn định | ±5-8% |

#### Điểm hook vào code hiện tại

- Actual tokens đã có sẵn qua signal `cost_updated` tại [summary_worker.py:626](../src/modules/summarizer/summary_worker.py#L626) và translate worker tương tự.
- Chỉ cập nhật khi `summary_completed(success=True)` / `all_completed` của translate — tránh session bị Stop giữa chừng làm lệch hệ số.

### 3.2. Smart content filtering — chỉ Tier 1 (an toàn)

Chỉ áp dụng các filter **đơn giản, không gây mất thông tin**:

| Filter | Áp dụng cho | Phức tạp | Rủi ro |
|---|---|---|---|
| Skip dòng/cột toàn rỗng | Excel | Thấp | Rất thấp |
| Skip sheet trống hoàn toàn | Excel | Thấp | Rất thấp |
| Skip slide trống (không text/shape/note) | PowerPoint | Thấp | Rất thấp |
| Skip dòng kẻ trang trí (`---`, `===`, ...) | Word, TXT | Thấp | Rất thấp |
| Skip page number độc lập | Word | Thấp | Thấp |

**Không làm trong phase này** (vì rủi ro mất thông tin hoặc phức tạp):

- Nén bảng lớn thành "mẫu + thống kê" — user không biết AI bỏ sót dòng giữa.
- Detect duplicate sections cross-file — có thể merge nhầm.
- Skip header/footer lặp — có thể chứa thông tin quan trọng (ngày tháng, mã số).
- Skip dòng lặp header (filter view Excel) — cần heuristic phức tạp.

Cấu hình:

```yaml
filtering:
  enabled: true   # cờ tắt để debug khi cần
```

### 3.3. Batch ảnh

Hiện tại mỗi ảnh = 1 API call riêng trong [`_describe_image`](../src/modules/summarizer/summary_worker.py#L355). Một số provider hỗ trợ multi-image trong 1 call — gom theo capability:

| Provider | Multi-image | Đề xuất |
|---|---|---|
| Gemini | Có | Gom tối đa 5 ảnh/call, prompt: "Mô tả từng ảnh theo thứ tự, đánh số 1, 2, 3..." |
| Claude | Có | Tương tự Gemini |
| OpenAI gpt-4o | Có | Tương tự |

Lợi ích:
- Giảm số API call → giảm latency overhead.
- Giảm token system prompt bị lặp.
- Phải bóc tách response theo số thứ tự ảnh.

---

## 4. Lộ trình triển khai

### Phase 1 — Pre-flight foundation (ưu tiên cao)

1. Tạo module `src/core/cost_estimator.py` — hàm `estimate_processing_cost(contents, provider, mode)` trả về dataclass `CostEstimate{api_calls, usd, vnd, seconds}`.
2. Tạo dialog dùng chung `src/ui/dialogs/confirmation_dialog.py`.
3. Tích hợp vào luồng Summary: chèn giữa `extract` và `start_summary` trong `MainWindow`.
4. Tích hợp vào dialog Translate: gọi cùng confirmation dialog trước khi `TranslateWorker` chạy.
5. Thêm config `confirmation.skip_threshold_usd` + xử lý logic skip.
6. Test với file thực tế, đo độ lệch estimation so với cost thực tế.

### Phase 2 — Token estimation chính xác hơn

1. Tinh chỉnh heuristic `estimate_tokens()` dựa trên test corpus tiếng Việt + tiếng Anh + bảng + code.
2. (Tùy chọn) Tích hợp `count_tokens` API per-provider, dùng cho file lớn nơi độ chính xác quan trọng.

### Phase 3 — Smart filtering (Tier 1)

1. Implement filter cho Excel (empty rows/cols, empty sheet).
2. Implement filter cho PowerPoint (empty slide).
3. Implement filter cho Word/TXT (dòng kẻ trang trí, page number độc lập).

### Phase 4 — Batch ảnh

1. Implement multi-image API call cho Gemini/Claude/OpenAI.
2. Bóc tách response theo số thứ tự ảnh.

---

## 5. Tham chiếu

- Đặc tả Summary: [requirement_spec.md §3](./requirement_spec.md)
- Đặc tả Translate: [requirement_spec.md §4](./requirement_spec.md)
- Cấu hình giá token: [config/config.yaml](../config/config.yaml)
- Token counter hiện tại: [src/providers/token_counter.py](../src/providers/token_counter.py)
- Summary pipeline: [src/modules/summarizer/summary_worker.py](../src/modules/summarizer/summary_worker.py)
- Translate pipeline: [src/modules/translator/translate_worker.py](../src/modules/translator/translate_worker.py)
