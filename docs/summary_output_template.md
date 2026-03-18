# Mẫu cấu trúc file tổng hợp chi tiết (.md)

Đây là mẫu cấu trúc cho file `.md` chi tiết được tải về khi người dùng bấm button "Chi tiết".
AI sẽ tạo nội dung theo cấu trúc này.

**Triết lý**: Báo cáo phải giúp người đọc hiểu mọi thứ mà KHÔNG cần đọc file gốc, không cần tra Google. AI không chỉ tóm tắt mà phải **phân tích, bổ sung kiến thức, và đề xuất hành động**.

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
- **Bổ sung kiến thức**: Giải thích thuật ngữ, khái niệm, quy trình nào mà file đề cập
  nhưng chưa rõ ràng. Bỏ qua mục này nếu nội dung đã đủ rõ.
- **Lưu ý đặc biệt**: (nếu có) Có biểu đồ mô tả XYZ, có hình ảnh thể hiện ABC, ...

(Lặp lại cho từng file)

---

## 3. Tổng hợp nội dung chi tiết

Tổng hợp chi tiết các thông tin quan trọng từ toàn bộ file.
Kết nối thông tin giữa các file liên quan, chỉ ra các điểm bổ sung hoặc mâu thuẫn (nếu có).
Giải thích những phần mơ hồ dựa trên kiến thức chuyên môn.
Nếu các file giao việc/yêu cầu hành động → liệt kê rõ ràng.

### 3.1. Chủ đề / Nội dung chính
- ...

### 3.2. Các số liệu / Dữ kiện quan trọng
- ...

### 3.3. Các vấn đề / Rủi ro được đề cập
- ...

---

## 4. Đề xuất và hướng đi tiếp theo

Dựa trên nội dung phân tích:
- **Việc cần làm**: (nếu tài liệu giao việc) liệt kê cụ thể từng bước.
- **Giải pháp/hướng tiếp cận**: (nếu tài liệu nêu vấn đề) đề xuất cách giải quyết.
- **Câu hỏi cần làm rõ**: (nếu có điểm mơ hồ, thiếu thông tin, mâu thuẫn)
  yêu cầu người dùng xác nhận lại với người gửi tài liệu.
- **Tài liệu nên tìm hiểu thêm**: (nếu cần) gợi ý hướng nghiên cứu bổ sung.

- [ ] Hành động 1
- [ ] Hành động 2
- [ ] ...
```

---

## Ghi chú

- Các mục 3.1, 3.2, 3.3 trong phần "Tổng hợp nội dung chi tiết" là gợi ý. AI sẽ tự điều chỉnh các heading phù hợp với nội dung thực tế của các file đầu vào.
- Phần "Đề xuất và hướng đi tiếp theo" sử dụng checkbox markdown để người dùng có thể theo dõi.
- Nếu các file không liên quan nhau, phần 3 sẽ tổng hợp riêng từng nhóm/file thay vì kết nối.
- Mục "Bổ sung kiến thức" trong phần 2 chỉ xuất hiện khi file đề cập nội dung cần giải thích thêm.
