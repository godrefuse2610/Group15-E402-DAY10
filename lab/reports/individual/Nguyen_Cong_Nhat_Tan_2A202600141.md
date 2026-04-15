# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Nguyễn Công Nhật Tân - 2A202600141
**Vai trò:** Ingestion Owner
**Ngày nộp:** 15/04/2026
**Độ dài yêu cầu:** Khoảng 400 từ

---

## 1. Tôi phụ trách phần nào?

**File / module:**
- `docs/data_contract.md`
- Chạy phần Khởi tạo Pipeline ở `etl_pipeline.py`

**Kết nối với thành viên khác:**
Tôi đảm nhận vai trò là nguồn vào (entrypoint) cho toàn bộ pipeline của nhóm bằng hành động đẩy dữ liệu thô (Raw Data). Kết quả của tôi `run_id=sprint1` với `raw_records = 10` sẽ là nguyên liệu thô để Cleaning Owner lấy tiếp từ đó viết rules phân loại rác và lưu trữ cách ly (Quarantine).

**Bằng chứng (commit / comment trong code):**
Đoạn log hệ thống dưới quyền kiểm soát của tôi thể hiện: 
`run_id=sprint1`, `raw_records=10`,  gồm file `manifest_sprint1.json` đã sinh tự động trong `artifacts/manifests/`.

---

## 2. Một quyết định kỹ thuật 

Trong quá trình quy hoạch bảng Source Map (trong `data_contract.md`), quyết định kỹ thuật quan trọng của tôi là thiết lập **"Failure Mode và Alert Metrics"** một cách thận trọng. Thay vì chỉ ghi chép nguồn dữ liệu đến từ đâu, tôi đã chọn gán rủi ro "File rỗng" cho PostgreSQL Database bằng cảnh báo `raw_records == 0`. Đối với hệ thống Internal Policy API, tôi thiết lập cảnh báo khi `HTTP status != 200` và tính toán đến cả `Rate Limit`. Điều này đảm bảo Ingestion Pipeline có thể cảnh báo lập tức (Fail-fast) cho Monitoring Owner ngay từ khâu tiếp nhận mà không phải chờ dữ liệu rác lan truyền hỏng các khối dưới.

---

## 3. Một lỗi hoặc anomaly đã xử lý 

Mặc dù được phân công là Ingestion, sau khi kích hoạt `python etl_pipeline.py run --run-id sprint1`, tôi đã quan sát và phát hiện ra một Anomaly ngay trên hệ thống Log của quy trình ở những bước cuối:
`freshness_check=FAIL {"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.285, "sla_hours": 24.0...`
Hệ thống báo cáo độ tươi (Freshness) của dữ liệu đã trễ đến hơn 120 giờ so với SLA (24 giờ). Tôi đã đánh dấu lại tình huống SLA violation này để Monitoring Owner có thể dựa vào file `manifest_sprint1.json` của tôi viết kịch bản `Runbook` cho việc dữ liệu quá lỗi hạn (Stale).

---

## 4. Bằng chứng trước / sau 

Vì vai trò Ingestion chỉ nằm tại bước nạp dữ liệu chứ không đụng tới logic Embed, tôi xin phép lấy bằng chứng đầu ra Log của ETL Pipeline do mình kích hoạt lần đầu làm mốc cơ sở:
`run_id=sprint1`
`raw_records=10`
`cleaned_records=6`
`quarantine_records=4`
Pipeline đã hoạt động suôn sẻ và lọc thành công 4 bản ghi lỗi, làm tiền đề để QA đánh giá trước/sau việc nạp dữ liệu.

---

## 5. Cải tiến tiếp theo 

Nếu có thêm 2 giờ làm Ingestion, tôi sẽ chuyển đổi quy trình nạp dữ liệu từ "Full Snapshot Override" (cụp toàn dataset) thành **Incremental Loading** (Nạp tăng dần). Hệ thống sẽ chỉ quét các bản ghi API mới sinh trong 24 giờ qua dựa trên `updated_at`, giảm thiểu băng thông mạng thay vì mỗi ngày đều chạy lại cả chục ngàn dòng CSV rác.
