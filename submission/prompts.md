# Dùng AI

| # | Ai dùng | Công cụ | Prompt (tóm tắt) | AI sai ở đâu | Nhóm kiểm lại thế nào |
|---|---|---|---|---|---|
| 1 | Cả nhóm | Antigravity AI | Viết `validator/validate.py` bắt 9 lỗi luật và sinh candidates | Ban đầu chỉ cắt từ đầu tiên của tên lớp nhiều từ (như `dining table` thành `dining`), gây ra nhiều cảnh báo swap giả | Sửa hàm đọc `classes.txt` dùng `split(' ', 1)` để giữ nguyên tên lớp đầy đủ, kiểm tra lại với `runs/clean` không còn cảnh báo giả |
| 2 | Cả nhóm | Antigravity AI | Đề xuất thuật toán phát hiện `bbox_drift` và `instance_merge` | AI đề xuất chỉ dùng IoU hộp bbox, dẫn đến đám đông người bị báo nhầm là lỗi gộp và lệch box | Tinh chỉnh điều kiện kết hợp diện tích mask panoptic, tỷ lệ kích thước hộp và khoảng cách tâm chuẩn hóa, kiểm tra bằng mắt từng ảnh |
| 3 | Cả nhóm | Antigravity AI | Tạo bộ hồ sơ bàn giao lô v2 gồm `manifest.csv`, `label_summary.csv`, `truyvet.csv` | Ban đầu đưa cả 80 lớp vào `label_summary.csv` với count=0 khiến lệnh kiểm tra H9 bị fail | Lọc chỉ giữ các lớp thực sự xuất hiện trong v2 theo đúng cách tính của `check_handover.py`, đóng gói lại và chạy test đạt 17/17 PASS |
