# Ý tưởng

## Bối cảnh
Tôi có ý tưởng làm một tool LazyDoc có kết hợp sử dụng AI để làm các công việc sau:

AI tổng hợp thông tin từ nhiều loại thông tin đầu vào:
Ném hết file vào tool
extract thông tin
cơ chế thống kế token và tiền dự kiến để nếu tốn nhiều tiền quá thì bỏ
Dùng AI tổng hợp thông tin thành file .md
Cho phép chọn ngôn ngữ file tổng hợp. File đầu vào thì ngôn ngữ gì cũng được

## Tổng quan

1. Tổng hợp thông tin từ nhiều loại tài liệu đầu vào
- Input:
    - Một đống các file thông tin không cố định cấu trúc, định dạng, ngôn ngữ

- Output:
    Tổng hợp thông tin để tôi hiểu ý nghĩa, mong muốn được mô tả trong các file.

2. Hỗ trợ dịch tài liệu
    - Chỉ định 1 hoặc nhiều file trong đóng file input để dịch sang ngôn ngữ đích yêu cầu mà vẫn giữ format (gồm cả các case phức tạp: merge, shapes, nhiều sheet. không cần dịch image hay biểu đồ)
    - Dịch thông minh có ngữ cảnh, sát nghĩa

## Chi tiết yêu cầu

- Thiết kế theo dạng module, để sau này có thể thêm chức năng khác vào hệ thống dễ dàng. Tạm thời có 2 module trên.
- Dễ dàng đóng gói, sử dụng trên nhiều máy.
- Sử dụng cho người dùng cá nhân.

### Màn hình chính

- Một hoạt ảnh đơn giản kiểu “máy xay tài liệu”:
    ```
    file → thả vào miệng máy
    ↓
    bấm nút
    ↓
    máy rung rung / quay
    ↓
    ra output document tổng hợp
    ```

- Có 1 bảng hiển thị danh sách tên file đã cho vào:
    - Mỗi file kèm các icon chức năng: xóa, checked
    - Có cột status hiển thị icon trạng thái: v nếu file đã đọc và xử lý, x nếu xử lý file gặp lỗi

- Có cơ chế dự đoán số tiền nếu tổng hợp hoặc dịch thuật các file đã chọn trong bảng khi request API AI.

- Khi bấm nút xay các file input trên máy đã checked trong bảng:
    Hiển thị trạng thái vui nhộn giống Claude Code. Ví dụ: Extracting..., Analysing..., v.v.

- Hiển thị tóm tắt thông tin tổng hợp output sau khi bấm nút xay các file input trên máy:
    - Hiển thị tổng quan ý nghĩa, mục đích tổng hợp lại của toàn bộ file
        - Nếu các file không có thông tin không liên quan gì với nhau thì cũng báo.
    - Hiển thị ý nghĩa, mục đích của từng file vào thêm 1 cột trên bảng phía trên
        - Hiển thị kèm cả ngôn ngữ mà file đó đang sử dụng. Chỉ tập trung tài liệu không phải tiếng Việt
            - Ví dụ file đó có tiếng Anh, tiếng Nhật, v.v. thì báo file có tiếng Anh / Nhật để người dùng còn request dịch file nếu cần.
            - Nếu chỉ tiếng Việt thì không cần báo
    - Các file có case đặc biệt như có cả ảnh, biểu đồ, shapes, v.v. thì cũng cần tổng hợp thông tin xem nó mô tả gì.

- Trước hoặc sau khi xay các file input:
    - Cho phép checked một hoặc nhiều file và chọn button "Dịch" để chuyển sang dialog module Dịch tài liệu
    - Nếu đã xay tài liệu, cần có cơ chế lưu tạm nào đó để khi Dịch không phải xử lý lại việc extract, v.v.

- Có icon setting để mở dialog module setting API key sử dụng.
- Có thêm các button "Hướng dẫn", "Thông tin"
- Góc UI chỉ cần icon x đóng UI, không cần icon phóng to hay thu nhỏ.

### Dialog setting API key

- Hiển thị label tên AI đang sử dụng hiện tại. Mặc định Gemini API.
- Hiển thị selectbox danh sách các AI khác kèm vùng nhập API key.
- Click button "Chọn" để lưu lại việc chuyển đổi AI sử dụng.
    - Nếu AI đó chưa nhập key thì báo lỗi, không cho Lưu
    - Nếu AI đó đã nhập key từ trước và lưu trong file cấu hình rồi thì vẫn cho Lưu bình thường.
    - Cần cẩn thận tránh lộ key.

### Dialog module dịch thuật

- Hiển thị danh sách tên file cần dịch
- Ngôn ngữ đích dạng selectbox để chọn (tạm thời cho phép chọn tiếng Việt, Anh, Nhật)
- Các button "Bảng thuật ngữ", "Dịch", "Mở rộng"

- Button Bảng thuật ngữ:
    - Click hiển thị dialog cho phép thêm thủ công thuật ngữ vào Bảng
    - Mục đích bảng này là để một số thuật ngữ mong muốn sẽ chỉ dịch theo từ đã mapping
    - Sử dụng được 2 chiều. Nghĩa là khi đã tạo ra 2 từ mapping trong bảng thuật ngữ thì khi dịch chỉ cần phát hiện từ muốn dịch trùng 1 thuật ngữ và ngôn ngữ đích trùng thuật ngữ mapping thì đều có thể sử dụng.

- Button "Mở rộng":
    - Hiển thị thêm vùng mở rộng, đẩy các button xuống dưới
    - Vùng mở rộng:
        - Domain: danh sách các radio để chọn xem tài liệu thuộc về lĩnh vực gì. Default chọn option "Mặc định"
        - Văn phong: danh sách các radio để chọn phong cách dịch (Báo cáo / Súc tích / Bay bổng / v.v.). Default chọn option "Mặc định"
        - Chế độ dịch: 2 radio "Mặc định" (dịch theo model offline free không quan tâm ngữ cảnh), "Thông minh" (sử dụng API AI dịch kèm ngữ cảnh + domain + văn phong)

- Button "Dịch":
    Hiển thị trạng thái loading % đang dịch.

### Dialog bảng thuật ngữ (thuộc module Dịch thuật)

- Hiển thị selectbox chọn loại ngôn ngữ (Việt, Anh, Nhật) và vùng nhập thuật ngữ.
- Button Lưu để thêm / sửa thuật ngữ đã nhập.
- Cho phép tìm thuật ngữ đã thêm.
- Không cần hiển thị toàn bộ thuật ngữ trong bảng ở dialog này. Chỉ hiển thị các thuật ngữ tìm kiếm kèm icon xóa.
- Mỗi người dùng là 1 bảng thuật ngữ riêng biệt.
- Có button import, export csv để chia sẻ bảng thuật ngữ của mình cho người khác
