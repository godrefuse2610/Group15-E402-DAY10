# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy export CSV | Batch file export từ hệ nguồn | File rỗng, thiếu cột, `doc_id` lạ, ngày sai format | Theo dõi `raw_records`, `quarantine_records`, expectation `effective_date_iso_yyyy_mm_dd` |
| Canonical text docs trong `data/docs/` | File-based ingest theo `doc_id` logic | Sai version, stale nội dung, không đồng bộ với export | So sánh `doc_id`, review `hits_forbidden` trong eval và `quality_rules` |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | ID ổn định sau clean, dùng để upsert vào Chroma |
| doc_id | string | Có | Khóa logic tài liệu nguồn như `policy_refund_v4`, `hr_leave_policy` |
| chunk_text | string | Có | Nội dung chunk sau clean, không được rỗng và tối thiểu 8 ký tự |
| effective_date | date | Có | Chuẩn hóa sang ISO `YYYY-MM-DD` trước khi publish |
| exported_at | datetime | Có | Mốc thời gian export dùng cho freshness |

---

## 3. Quy tắc quarantine vs drop

Record fail rule clean không bị xóa im lặng mà đi vào `artifacts/quarantine/*.csv` để giữ bằng chứng. Các lỗi hiện có gồm `unknown_doc_id`, `missing_effective_date`, `invalid_effective_date_format`, `stale_hr_policy_effective_date`, `missing_chunk_text`, `duplicate_chunk_text`.

Nhóm hiện dùng chiến lược:
- Quarantine mọi record không đủ tin cậy để publish.
- Chỉ embed dữ liệu từ `artifacts/cleaned/*.csv`.
- Nếu cần phục hồi record từ quarantine thì phải sửa rule hoặc sửa nguồn raw rồi rerun pipeline, không merge tay vào cleaned output.

Owner review là `group15-monitoring-docs`; quyết định cuối cùng phải đồng bộ với owner phần cleaning/quality vì thay đổi quarantine có thể làm đổi `cleaned_records`, eval và freshness evidence.

---

## 4. Phiên bản & canonical

Source of truth cho refund là `data/docs/policy_refund_v4.txt` với `doc_id=policy_refund_v4`. Rule clean đang sửa marker stale `14 ngày làm việc` về `7 ngày làm việc` trước khi publish.

Source of truth cho leave policy là `data/docs/hr_leave_policy.txt`; bản có `effective_date < 2026-01-01` được xem là stale và bị quarantine. Đây là cách pipeline tránh để agent Day 09 đọc nhầm bản HR 2025 thay vì bản 2026.

Freshness hiện được đo tại mốc `publish` theo contract `sla_hours=24`, nên command `freshness` mặc định dùng `run_timestamp` để đánh giá snapshot vừa publish có còn trong SLA không. Nếu cần phân tích độ cũ của dữ liệu nguồn, nhóm có thể đổi policy sang `ingest`; khi đó check sẽ dùng `latest_exported_at` và artifact mẫu sẽ cho thấy dữ liệu nguồn đã stale từ `2026-04-10T08:00:00`.
