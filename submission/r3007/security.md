# Bảo mật khi làm việc

## 1. Ca USB: hết giờ, muốn chép lô về nhà làm tiếp
Tuyệt đối không được sao chép dữ liệu dự án ra USB, thẻ nhớ ngoài, hoặc gửi qua email cá nhân, lưu vào Google Drive/OneDrive cá nhân hay nhờ người quen làm hộ. Hành vi này vi phạm nghiêm trọng chính sách bảo mật thông tin (Data Leak Prevention - DLP) và các cam kết bảo mật NDA với đối tác. Các thiết bị và tài khoản cá nhân không có phần mềm giám sát an toàn (EDR), rất dễ bị nhiễm mã độc hoặc làm lộ lọt dữ liệu khách hàng. Khi hết giờ mà chưa hoàn thành công việc, giải pháp đúng đắn là báo cáo với trưởng nhóm (Team Lead/PM) để xin gia hạn tiến độ, hoặc sử dụng hệ thống máy ảo/VPN được công ty phê duyệt và cấp quyền truy cập từ xa an toàn qua xác thực đa yếu tố (MFA).

## 2. Năm việc: được hay không
1. Mở job được giao trên máy công ty: ĐƯỢC. Đây là môi trường làm việc chính thức, đã được cài đặt đầy đủ phần mềm bảo mật, kiểm soát truy cập và bảo vệ điểm cuối theo đúng quy chuẩn bảo mật doanh nghiệp.
2. Chụp màn hình gửi người quen: KHÔNG ĐƯỢC. Hành vi chụp màn hình dữ liệu hình ảnh hoặc nhãn gán rồi phát tán ra bên ngoài vi phạm thỏa thuận bảo mật dữ liệu khách hàng và có nguy cơ làm lộ bí mật dự án.
3. Chép lô ra USB: KHÔNG ĐƯỢC. Thiết bị lưu trữ cá nhân không được mã hóa, dễ thất lạc, có nguy cơ lây lan virus vào mạng nội bộ công ty và trực tiếp vi phạm chính sách cấm xuất dữ liệu trái phép.
4. Dán nhãn thật lên chatbot công cộng: KHÔNG ĐƯỢC. Các chatbot AI công cộng (như ChatGPT, Claude bản miễn phí) có thể lưu trữ và dùng dữ liệu người dùng nhập vào để tái huấn luyện mô hình, dẫn tới nguy cơ lộ lọt toàn bộ bộ dữ liệu độc quyền của dự án.
5. Đưa tài khoản CVAT cho đồng nghiệp: KHÔNG ĐƯỢC. Mỗi tài khoản gắn liền với định danh cá nhân để ghi nhận trách nhiệm, phân quyền và lưu vết lịch sử kiểm toán (audit log/lineage). Cho mượn tài khoản làm sai lệch truy vết người gán/người kiểm.

## 3. Ca khuôn mặt: thấy mặt người rõ trong lô, guideline yêu cầu làm mờ
Khi phát hiện khuôn mặt người nhìn rõ trong lô mà guideline yêu cầu phải làm mờ, hành động bắt buộc là đặt trạng thái lô là HOLD và báo cáo ngay lập tức cho người phụ trách dự án (Data Lead / Quality Manager).
Tuyệt đối không được tự ý xóa ảnh hoặc tự mở công cụ đồ họa cá nhân để bôi mờ mặt. Lý do là việc tự ý xóa ảnh sẽ làm sai lệch cấu trúc cảnh (scene) giả lập, làm gãy thứ tự liên tục của dữ liệu và phá hỏng manifest hash của toàn bộ lô bàn giao. Hơn nữa, việc làm mờ khuôn mặt phải tuân thủ thuật toán làm mờ chuẩn hóa đồng bộ của dự án (mức độ blur/pixelate chuẩn) để không làm sai lệch diện tích mask panoptic và ranh giới bounding box detection của người.
Ví dụ cụ thể trong lô r3007 của nhóm: Ảnh 000000006763 chụp hai người đàn ông mặc trang phục lịch sự có khuôn mặt nhìn rất rõ, và ảnh 000000001000 chụp đám đông người đi dạo trên đường phố. Cần HOLD lô và chuyển lại cho đội tiền xử lý chạy quy trình làm mờ khuôn mặt đạt chuẩn.
