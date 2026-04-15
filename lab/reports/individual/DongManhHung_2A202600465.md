# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Đồng Mạnh Hùng - 2A202600465  
**Vai trò:** Monitoring
**Ngày nộp:** 15/04/2026  
**Độ dài yêu cầu:** Khoảng 500 từ

---

## 1. Tôi phụ trách phần nào?

**File / module:**
- `monitoring/freshness_check.py`
- `docs/runbook.md`
- `docs/pipeline_architecture.md`
- `docs/data_contract.md`
- `contracts/data_contract.yaml`

**Kết nối với thành viên khác:**
Tôi phụ trách phần Monitoring, tức là theo dõi trạng thái của pipeline sau khi dữ liệu đã đi qua bước clean, validate và publish. Công việc của tôi không nằm ở sửa dữ liệu bẩn trực tiếp mà nằm ở việc xác định dữ liệu có còn mới hay không, biết run nào vừa publish, biết khi nào cần kiểm tra `manifest`, `quarantine`, `log` và `eval`. Kết quả phần của tôi nối trực tiếp với Ingestion Owner và Cleaning/Quality Owner, vì khi `freshness` hoặc evidence trong artifact có vấn đề thì tôi là người khoanh vùng trước rồi chuyển lại đúng owner xử lý.

**Bằng chứng (commit / comment trong code):**
Tôi đã cập nhật logic freshness và tài liệu liên quan. Bằng chứng trực tiếp là file `monitoring/freshness_check.py` hiện đã đọc policy từ `contracts/data_contract.yaml` thay vì hard-code mốc thời gian; ngoài ra các file `docs/runbook.md`, `docs/pipeline_architecture.md` và `docs/data_contract.md` đã được điền nội dung theo artifact thật của repo.

---

## 2. Một quyết định kỹ thuật

Quyết định kỹ thuật quan trọng nhất của tôi là chọn đo freshness theo đúng policy trong contract thay vì mặc định luôn dùng `latest_exported_at`. Trong `contracts/data_contract.yaml`, nhóm khai báo `freshness.measured_at: "publish"` và `sla_hours: 24`, nên về mặt nghiệp vụ, snapshot vừa publish phải được đánh giá theo `run_timestamp` của manifest. Tuy nhiên code cũ trong `freshness_check.py` lại ưu tiên `latest_exported_at`, làm cho cả những manifest vừa chạy xong vẫn bị `FAIL` chỉ vì dữ liệu nguồn cũ.

Tôi đã sửa phần này để `check_manifest_freshness()` đọc policy từ contract, hỗ trợ cả `publish` và `ingest`, rồi chọn đúng timestamp tương ứng. Với cách làm này, monitoring không chỉ “chạy được” mà còn bám đúng hợp đồng dữ liệu. Đây là quyết định quan trọng vì nếu đo sai boundary thì dashboard và runbook đều dẫn nhóm đến chẩn đoán sai.

---

## 3. Một lỗi hoặc anomaly đã xử lý

Anomaly tôi xử lý là việc command freshness đang báo fail dù pipeline vừa publish snapshot mới. Triệu chứng tôi quan sát được là khi chạy:

`python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_2026-04-15T09-11Z.json`

kết quả cũ trả về `FAIL` với timestamp `latest_exported_at = 2026-04-10T08:00:00`. Sau khi đọc kỹ project, tôi nhận ra đây không phải bug dữ liệu mà là bug logic monitoring: contract đo ở mốc `publish`, còn code lại đo theo `ingest`.

Sau khi fix, cùng manifest đó cho kết quả:

`PASS {"measured_at": "publish", "checked_timestamp": "2026-04-15T09:12:12.918486+00:00", "age_hours": 0.559, "sla_hours": 24.0}`

Tôi cũng kiểm tra thêm trường hợp đo theo `ingest` thì vẫn ra `FAIL`, nghĩa là monitoring hiện đã phân biệt đúng hai góc nhìn: snapshot publish mới và dữ liệu nguồn stale.

---

## 4. Bằng chứng trước / sau

Before:

`FAIL {'measured_at': 'ingest', 'checked_timestamp': '2026-04-10T08:00:00', 'age_hours': 121.762, 'sla_hours': 24.0, 'reason': 'freshness_sla_exceeded'}`

After:

`PASS {"measured_at": "publish", "checked_timestamp": "2026-04-15T09:12:12.918486+00:00", "age_hours": 0.559, "sla_hours": 24.0}`

Run/evidence tôi dùng là manifest `manifest_2026-04-15T09-11Z.json`. Tôi cũng đồng bộ phần giải thích này vào `docs/runbook.md` và `docs/pipeline_architecture.md` để các thành viên khác khi đọc artifact biết tại sao một run có thể pass ở boundary publish nhưng vẫn cảnh báo stale nếu soi theo ingest.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi muốn mở rộng monitoring theo hướng đo 2 boundary rõ ràng trong cùng một lần chạy: `ingest_freshness` và `publish_freshness`. Như vậy manifest sẽ cho thấy ngay dữ liệu nguồn có stale không, đồng thời snapshot vừa publish có đúng SLA vận hành không. Đây cũng là bước hợp lý để nối sang alerting thật thay vì chỉ xem log hoặc CLI output.
