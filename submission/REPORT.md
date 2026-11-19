# Báo cáo nhóm <<XX>>

## 1. Số liệu luyện tập
- F1 theo seed 3007 (rule / cross_check / overall): 1.0 / 0.9 / 0.9
- Truy vết F1: tier_a 1.0 · tier_b 1.0 · notify 1.0
- Số ứng viên trên lô sạch (`--no-faults`, pool calib 50 ảnh): ~15 ứng viên (chủ yếu là người che khuất nhau trong đám đông hoặc đồ vật nhỏ chồng lên nhau trên bàn).
- Hàng đợi trên seed luyện tập: 13 ảnh cần xem tay sau khi lọc nhiễu.
- Ngưỡng đã chọn và cách chọn (không dùng `_private`):
  + Đối chiếu dựa trên hình học và cặp lớp dễ nhầm:
  + `class_swap` / `category_swap`: IoU > 0.45 với cặp lớp dễ nhầm (`CONFUSABLE`), hoặc IoU > 0.70 với các cặp lớp bất kỳ.
  + `missing_box`: segment thing có diện tích mask ≥ 1500 pixel và không có box detection nào có IoU > 0.05.
  + `bbox_drift`: box chiếm diện tích ≥ 0.5% ảnh và độ lệch tâm chuẩn hóa theo kích thước box trong khoảng [0.12, 0.35].
  + `instance_merge`: 1 segment thing phủ trọn 2 box detection cùng lớp riêng biệt (IoU giữa 2 box < 0.1).

## 2. Vì sao báo hết ứng viên làm F1 giảm?
- COCO tự nhiên vốn có độ lệch tự nhiên giữa bounding box detection và panoptic mask (do vật bị che khuất một phần, đám đông người/xe đứng chen chúc, góc nhìn khuất).
- Nếu chỉ ghép thô bằng IoU và tự động báo toàn bộ các cặp lệch làm lỗi, trên 250 ảnh sẽ sinh ra hơn 180 ứng viên báo lỗi.
- Vì metric đánh giá là rank F1 = 2 * (P * R) / (P + R), việc báo thừa (False Positives) sẽ kéo Precision tụt dốc nghiêm trọng (từ ~0.9 xuống chỉ còn ~0.2 - 0.3), kéo theo F1 tổng giảm từ 0.9 xuống chỉ còn khoảng 0.6. Trong bài lab này, báo thừa bị trừ điểm tương đương với bỏ sót lỗi. Do đó bắt buộc phải xem ảnh bằng mắt để loại bỏ các trường hợp lệch tự nhiên.

## 3. Quyết định và lineage
- QC v1: 19/250 lỗi (tỷ lệ 7.6% > ngưỡng 2.0% cho phép) ⇒ Quyết định HOLD.
- Huấn luyện R-021: Training run R-021 đã được huấn luyện trên lô v1 có chứa 19 lỗi dữ liệu (bao gồm cả ảnh rò rỉ phân chia train/val, nhãn sai lớp, lệch box). Việc bàn giao lô sửa v2 không tự động sửa tri thức của model đã học từ trước, do đó model R-021 bắt buộc phải được đánh giá lại hoặc train lại (`review_or_retrain`) trên lô sạch v2.

## 4. Hash chứng minh gì, không chứng minh gì?
- Hash chứng minh: Tính toàn vẹn của tệp dữ liệu (Data Integrity). Chứng minh tệp không bị sửa đổi, hỏng hóc trong quá trình truyền tải, lưu trữ và đúng phiên bản đã được phê duyệt tại thời điểm tạo manifest.
- Hash KHÔNG chứng minh: Tính đúng đắn về ngữ nghĩa của dữ liệu (Data Correctness/Quality). Một bức ảnh bị gán nhãn sai lớp (ví dụ xe ô tô cá nhân bị gán nhãn xe bus) hoặc box bị vẽ lệch hoàn toàn vẫn có thể có mã SHA256 hoàn toàn hợp lệ.

## 5. Truy vết
- Tiêu chí:
  + Tầng a: Ảnh nằm trong các cảnh team AI nêu (`scene_197`, `scene_309`), thuộc job theo guideline cũ (v1.2), và có ít nhất 1 box detection thuộc lớp bị đổi quy tắc (`bottle`).
  + Tầng b: Các ảnh khác trong lô cũng thuộc job guideline v1.2 và có box `bottle`, nhưng chưa được team AI phát hiện/báo cáo.
  + Notify: Mã annotator và reviewer phụ trách các job chứa ảnh tầng a và b (để thông báo đào tạo lại và rà soát nhãn).
- Vì sao lấy guideline theo job mà không theo metadata ảnh: Vì metadata ở từng ảnh có thể chính là lỗi `guideline_mismatch` (ảnh bị ghi nhầm phiên bản guideline). Phiên bản guideline tại thời điểm giao việc được chốt ở cấp độ job trong `jobs.csv`.

## 6. Bug hoặc điểm chưa rõ trong lab (nếu có)
- Không có. Quy trình kiểm tra định dạng và chấm điểm bằng `check_handover.py` và `score_findings.py` hoạt động nhất quán, chính xác.
