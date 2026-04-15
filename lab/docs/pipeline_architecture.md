# Kiến trúc pipeline — Lab Day 10

**Nhóm:** Group 15  
**Cập nhật:** 2026-04-15

---

## 1. Sơ đồ luồng (bắt buộc có 1 diagram: Mermaid / ASCII)

```text
data/raw/policy_export_dirty.csv
  -> etl_pipeline.py run
  -> transform/cleaning_rules.py
     -> artifacts/cleaned/cleaned_<run_id>.csv
     -> artifacts/quarantine/quarantine_<run_id>.csv
  -> quality/expectations.py
     -> halt nếu có expectation severity=halt fail
  -> embed snapshot vào Chroma collection day10_kb
  -> artifacts/manifests/manifest_<run_id>.json
  -> monitoring/freshness_check.py
  -> serving cho retrieval Day 08/09 và eval_retrieval.py
```

Điểm đo freshness hiện đọc policy từ contract và mặc định dùng mốc `publish`, tức `run_timestamp` trong manifest. Nếu nhóm đổi sang `ingest`, check sẽ dùng `latest_exported_at`. `run_id` xuất hiện trong log, tên file artifact và metadata embed. `quarantine` là ranh giới publish, vì record ở đó không được phép đi tiếp sang Chroma.

---

## 2. Ranh giới trách nhiệm

| Thành phần | Input | Output | Owner nhóm |
|------------|-------|--------|--------------|
| Ingest | `data/raw/policy_export_dirty.csv` | raw rows trong memory + `raw_records` | Ingestion / Raw Owner |
| Transform | raw rows | `cleaned.csv`, `quarantine.csv` | Cleaning & Quality Owner |
| Quality | cleaned rows | expectation results, halt/warn decision | Cleaning & Quality Owner |
| Embed | cleaned rows hợp lệ | Chroma collection `day10_kb` | Embed & Idempotency Owner |
| Monitor | manifest, logs, eval, quarantine | freshness status, runbook, docs, report evidence | Monitoring / Docs Owner |

---

## 3. Idempotency & rerun

Pipeline dùng `chunk_id` ổn định để `upsert` vào Chroma. Trước khi upsert, code prune những id không còn trong cleaned snapshot để tránh vector stale còn nằm lại sau các lần inject corruption. Điều này giúp rerun không làm collection phình ra và giữ ranh giới publish rõ ràng.

---

## 4. Liên hệ Day 09

Pipeline này làm sạch export trước khi publish sang collection `day10_kb`. Về mặt vai trò, nó đứng trước retrieval của Day 09: agent chỉ nên query collection đã qua clean, expectation và freshness check. Nếu tích hợp lại Day 09, nhóm có thể giữ collection riêng để tách môi trường lab nhưng logic vẫn là cùng một chuỗi ingestion -> publish -> retrieval.

---

## 5. Rủi ro đã biết

- Freshness mặc định đang đo tại boundary `publish`; nếu cần mô phỏng dữ liệu stale ở nguồn ingest, nhóm có thể chuyển policy sang `ingest` hoặc giải thích bằng evidence riêng.
- Freshness mới hỗ trợ 2 cách nhìn chính là `publish` và `ingest`, nhưng chưa có alerting tự động ngoài log/CLI.
- Alert channel mới là quy ước trong contract, chưa tích hợp Slack/email thật.
