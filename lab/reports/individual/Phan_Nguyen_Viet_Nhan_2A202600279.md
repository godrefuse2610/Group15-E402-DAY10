# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phan Nguyễn Việt Nhân  
**Vai trò:** Cleaning & Quality Owner  
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** **400–650 từ**

---

## 1. Tôi phụ trách phần nào?

Trong lab này tôi đảm nhận vai trò Cleaning và Quality Owner, tức là chịu trách nhiệm chính cho module `transform/cleaning_rules.py` và `quality/expectations.py`. Cụ thể, tôi viết thêm ba rule mới cho Sprint 2 là R7 `strip_invisible_unicode`, R8 `quarantine_missing_exported_at` và R9 `normalize_doc_id_case`, đồng thời bổ sung hai expectation E7 và E8 vào bộ kiểm tra tự động.

Tôi kết nối với bạn phụ trách Ingestion để thống nhất schema đầu vào của `policy_export_dirty.csv`, đảm bảo trường `exported_at` luôn có mặt trước khi dữ liệu qua tay tôi. Bạn phụ trách Embed cũng phải chờ tôi xác nhận cleaned CSV đạt toàn bộ expectation PASS trước khi upsert vào ChromaDB. Bằng chứng cụ thể nằm ở phần header comment trong `cleaning_rules.py` dòng 8 đến 10 ghi rõ tên rule và tác giả nhóm.

---

## 2. Một quyết định kỹ thuật

Quyết định tôi cân nhắc lâu nhất là đặt severity cho E7 `no_invisible_chars_in_chunk_text` là halt thay vì warn.

Ban đầu tôi định để warn vì ký tự vô hình nghe có vẻ nhỏ nhặt, không ảnh hưởng ngữ nghĩa. Nhưng sau khi thử inject một dòng BOM vào cuối `policy_refund_v4`, tôi nhận ra vấn đề thực sự nằm ở chỗ khác: nếu R7 bị bỏ qua hoặc chạy sai thứ tự, BOM làm cho hai chunk có nội dung giống hệt nhau trở thành hai key khác nhau trong bước dedup, dẫn đến cả hai đều lọt vào cleaned. Kết quả là vector store nhận thêm một chunk trùng lặp, làm lệch kết quả top-k retrieval. Đây không còn là vấn đề mỹ quan mà là vấn đề tính đúng đắn của index.

Tôi quyết định đặt halt để pipeline dừng hẳn trước bước embed nếu R7 bị vô hiệu hoá hoặc bỏ sót, thay vì để lỗi âm thầm lan vào ChromaDB mà không ai hay.

---

## 3. Một lỗi đã xử lý

Trong lần chạy đầu tiên với `run_id=sprint2`, tôi thấy `quarantine_records=4` nhưng lại không tìm thấy dòng nào có `reason=duplicate_chunk_text` trong file `quarantine_sprint2.csv`. Tôi kiểm tra lại thứ tự các rule và phát hiện R7 đang được gọi sau bước dedup, không phải trước. Điều đó có nghĩa là BOM vẫn còn trong chuỗi khi hàm `_norm_text` tính key, nên chunk trùng không bị nhận diện.

Expectation E7 phát hiện triệu chứng ở bề mặt, nhưng log dòng `chunks_with_invisible_chars=0` lại PASS vì tôi nhầm tưởng R7 đã chạy rồi. Sau khi trace lại luồng trong `clean_rows`, tôi chuyển lời gọi `_strip_invisible_unicode` lên ngay đầu vòng lặp, trước mọi kiểm tra khác. Kết quả là `run_id=2026-04-15T08-56Z` đã ghi đúng một dòng `duplicate_chunk_text` vào quarantine, còn E7 vẫn PASS vì cleaned không còn ký tự vô hình nào.

---

## 4. Bằng chứng trước / sau

Hai dòng quarantine dưới đây trích từ `artifacts/quarantine/quarantine_2026-04-15T08-56Z.csv`, run_id `2026-04-15T08-56Z`:

    2,policy_refund_v4,...,2026-02-01,2026-04-10T08:00:00,duplicate_chunk_text,
    7,hr_leave_policy,...,2025-01-01,2026-04-10T08:00:00,stale_hr_policy_effective_date,2025-01-01

Cùng run đó, log ghi `cleaned_records=6` và `quarantine_records=4`. Tám expectation đều PASS. So với lần chạy sprint1 trước khi có R7 và R8, số dòng vào cleaned là như nhau nhưng lần đó thiếu hẳn dòng `missing_exported_at` trong quarantine vì R8 chưa tồn tại, tức là dữ liệu thiếu lineage vẫn lọt qua.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ ghi thêm một trường `rules_applied` vào manifest, liệt kê đúng tên và phiên bản của từng cleaning rule đã chạy trong lượt đó. Hiện tại manifest chỉ ghi `run_id` và số lượng record, nên khi so sánh hai run khác nhau tôi không biết ngay run nào có R7 hay không nếu không đọc lại code. Có trường này thì audit trở nên rất nhanh.
