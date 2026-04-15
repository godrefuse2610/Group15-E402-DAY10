# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Phan Anh Ly Ly - 2A202600421
**Vai trò:** Docs Owner
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** **400–650 từ** 

---

## 1. Tôi phụ trách phần nào? (80–120 từ)

**File / module:**
Tôi đóng vai trò Docs Owner của nhóm. Trách nhiệm của tôi bao gồm:
- Viết, định dạng và hoàn thiện tổng hợp các file kiến trúc luồng dữ liệu (Docs), bao gồm: `docs/pipeline_architecture.md`, `docs/data_contract.md`, và `docs/quality_report.md`.
- Lắp ráp dữ liệu vận hành (Metrics) vào `reports/group_report.md`.
- Đảm bảo tính minh bạch Data Observability bằng cách đánh giá mức độ vi phạm SLA Freshness qua `freshness_check.py`.

**Kết nối với thành viên khác:**
Tôi làm việc trực tiếp với Ingestion Owner (để đọc input `manifest.json` và phân tích lỗi `latest_exported_at`) và Cleaning Owner (tập hợp bằng chứng về tỉ lệ fail/pass metrics, trích xuất dữ liệu eval). Từ đó, tôi quy đổi các logs kĩ thuật thành báo cáo chất lượng Quality Report minh bạch để giảng viên và team Day 09 có thể vận hành AI agent.

**Bằng chứng (commit / comment trong code):**
Đóng góp chính nằm ở nội dung các file Markdown trong thư mục `docs/`. Tracking commit tập trung vào `group_report.md` và `quality_report.md` (chứa minh chứng Eval Results). Đã hoàn thành xử lý nội dung log: `freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.253, "sla_hours": 24.0}`.

---

## 2. Một quyết định kỹ thuật (100–150 từ)

Trong việc đánh giá Freshness và Observability, quyết định lớn nhất là thiết lập bộ SLA cho freshness của DB. Với bối cảnh một chatbot nội bộ, việc quy định độ tươi mới về chính sách phụ thuộc vào `latest_exported_at` trên nguồn CSV Data (thời điểm trích xuất). Tôi và Ingestion Owner quyết định setup hệ thống cảnh báo Freshness Check dưới mốc SLA tiêu chuẩn 24h. 

Bởi vì AI Agent (Lab 09) hoàn toàn phụ thuộc vào hệ sinh thái dữ liệu được nạp, sự lỗi thời của "ngày công 2026" / "quy trình hoàn tiền 7 hay 14 ngày" sẽ gây thảm hoạ trực tiếp trên giao tiếp User. Nếu `age_hours` (tính từ độ trễ lúc export trừ đi time pipeline processing hiện tại) lớn hơn `sla_hours`, hệ thống Monitoring trong kịch bản Lab sẽ tự động thả warning flag trong log manifest `FAIL "reason": "freshness_sla_exceeded"`. Tôi ưu tiên cảnh báo dưới hình thức `FAIL` (Logging) thay vì `halt` cứng pipeline, vì dù dữ liệu cũ, team đôi lúc vẫn muốn chạy thử để trích xuất report trước khi gọi các bộ phận liên quan sửa Raw DB.

---

## 3. Một lỗi hoặc anomaly đã xử lý (100–150 từ)

**Triệu chứng:**
Lúc theo dõi luồng Inject lỗi Sprint 3 (`--no-refund-fix` & `--skip-validate`), bộ truy vấn Retrieval từ CSV hiển thị kết quả truy xuất cho policy HR bị bất thường, trả về văn bản chứa mốc "14 ngày" làm việc thay vì 7 ngày. Đây là vi phạm Rule nghiêm trọng. 

**Detection & Diagnosis:**
Qua việc đối soát `artifacts/eval/before_inject_bad.csv` (CSV chứa dữ liệu corrupt bypass), quan sát thấy với câu hỏi `q_refund_window`, AI context window (top-k) ghi nhận thông tin tài liệu `policy_refund_v4` có chứa policy sai lệch, tham số `hits_forbidden` trả về bằng `yes`. Nguyên nhân là luồng Cleaning chưa được kích hoạt, Rule Quarantine cho dòng chứa "14 ngày làm việc" chưa lọc sạch record lỗi, đẩy "Corrupt data vector" vào database `day10_kb`.

**Mitigation:**
Xóa Collection hiện hữu. Khởi động lại Command `python etl_pipeline.py run` bật cờ block Expectation halt. Chạy lại Fresh Retrieval `eval_retrieval.py` xuất output mới `after_fix_final.csv`, chỉ số `hits_forbidden` trở lại `no`.

---

## 4. Bằng chứng trước / sau (80–120 từ)

Trích dẫn minh chứng ảnh hưởng lỗi từ DB đến Vector Space AI:
- `before_inject_bad.csv` (run_id=inject-bad): 
Dữ liệu Vector dính chuỗi 14 ngày. Cột `hits_forbidden` báo lỗi `yes`. Document bị thả vào agent bao gồm nội dung: "Yêu cầu được gửi trong vòng 14 ngày làm việc kể từ thời điểm..."
- `after_fix_final.csv` (run_id=2026-04-15T08-14Z): 
Expectation filter hoạt động. Chuỗi 14 ngày bị cô lập (quarantine). Data Top 1 context trả về: "Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận..." — `hits_forbidden` trở về mức chuẩn `no`.

---

## 5. Cải tiến tiếp theo (40–80 từ)

Nếu có thêm 2 giờ, tôi sẽ tập trung viết script kết nối API Webhook của MS Teams hoặc Slack channel cho phần Freshness Check Monitoring. Nếu age_hours > SLA 24h, script `freshness_check.py` sẽ ping webhook, chủ động đẩy tín hiệu Red Alert gửi kèm run_id tới hộp thư Ops Team thay vì chỉ ghim passive alert vào file json/log tĩnh. Điều này tăng cường Data Observability.
