# Mẫu cấu trúc file tổng hợp chi tiết (.md)

Đây là mẫu cấu trúc cho file `.md` chi tiết được tải về khi người dùng bấm button "Chi tiết".
AI sẽ tạo nội dung theo cấu trúc này.

---

```markdown
# Báo cáo tổng hợp tài liệu

- **Ngày tạo**: YYYY-MM-DD HH:mm
- **Số file xử lý**: N file
- **AI Provider**: Tên provider + model

---

## 1. Tổng quan chung

Mô tả tổng quan ý nghĩa, mục đích chung của toàn bộ tài liệu đầu vào.
Nêu rõ mối liên hệ giữa các file (hoặc ghi rõ nếu các file không liên quan nhau).

---

## 2. Phân tích từng file

### 2.1. [Tên file gốc]
- **Kích thước**: ...
- **Ngôn ngữ**: Tiếng Anh / Nhật / ... (bỏ qua nếu chỉ có tiếng Việt)
- **Loại tài liệu**: Báo cáo / Hợp đồng / Bảng dữ liệu / Thuyết trình / ...
- **Ý nghĩa**: File này nói về cái gì, phục vụ mục đích gì.
- **Nội dung chính**:
  - Điểm chính 1
  - Điểm chính 2
  - ...
- **Lưu ý đặc biệt**: (nếu có) Có biểu đồ mô tả XYZ, có hình ảnh thể hiện ABC, ...

(Lặp lại cho từng file)

---

## 3. Tổng hợp nội dung chi tiết

Tổng hợp chi tiết các thông tin quan trọng từ toàn bộ file.
Kết nối thông tin giữa các file liên quan, chỉ ra các điểm bổ sung hoặc mâu thuẫn (nếu có).

### 3.1. Chủ đề / Nội dung chính
- ...

### 3.2. Các số liệu / Dữ kiện quan trọng
- ...

### 3.3. Các vấn đề / Rủi ro được đề cập
- ...

---

## 4. Đề xuất hành động tiếp theo

Dựa trên nội dung các file, đề xuất những việc cần làm tiếp:
- [ ] Hành động 1 (ví dụ: "Cần dịch file X sang tiếng Việt")
- [ ] Hành động 2 (ví dụ: "File Y cần review bởi bộ phận pháp lý")
- [ ] Hành động 3 (ví dụ: "Cần bổ sung dữ liệu cho bảng Z")
- ...
```

---

## Ghi chú

- Các mục 3.1, 3.2, 3.3 trong phần "Tổng hợp nội dung chi tiết" là gợi ý. AI sẽ tự điều chỉnh các heading phù hợp với nội dung thực tế của các file đầu vào.
- Phần "Đề xuất hành động tiếp theo" sử dụng checkbox markdown để người dùng có thể theo dõi.
- Nếu các file không liên quan nhau, phần 3 sẽ tổng hợp riêng từng nhóm/file thay vì kết nối.
