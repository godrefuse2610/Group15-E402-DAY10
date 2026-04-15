# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

User hoặc agent trả lời dựa trên context cũ, ví dụ refund window có thể vẫn dính `14 ngày làm việc`, hoặc pipeline nhìn có vẻ chạy xong nhưng dữ liệu nguồn đã stale dù snapshot publish vẫn mới. Một triệu chứng khác là artifact mới có `run_id` mới nhưng `latest_exported_at` trong manifest vẫn cũ.

---

## Detection

Các tín hiệu nên kiểm đầu tiên:
- `freshness_check=FAIL` trong manifest hoặc khi chạy `python etl_pipeline.py freshness --manifest ...`
- `expectation[...] FAIL` trong log pipeline
- `hits_forbidden=yes` trong `artifacts/eval/*.csv`, đặc biệt với `q_refund_window`
- Chênh lệch bất thường giữa `raw_records`, `cleaned_records`, `quarantine_records`

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/*.json` mới nhất | Xác nhận `run_id`, `cleaned_records`, `quarantine_records`, `latest_exported_at`, cờ `no_refund_fix` / `skipped_validate` |
| 2 | Chạy `python etl_pipeline.py freshness --manifest <manifest>` | Biết ngay trạng thái `PASS`, `WARN`, `FAIL` cho policy hiện tại; với contract mặc định `publish`, manifest mới thường PASS nếu vừa chạy xong |
| 3 | Mở `artifacts/quarantine/*.csv` cùng run | Xem record nào bị loại và vì sao, nhất là `unknown_doc_id`, `invalid_effective_date_format`, `stale_hr_policy_effective_date` |
| 4 | Mở `artifacts/logs/run_<run_id>.log` | Kiểm expectation nào fail và pipeline có dừng ở `PIPELINE_HALT` hay không |
| 5 | Chạy `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv` hoặc so sánh file eval sẵn có | Kiểm tra `hits_forbidden` và `top1_doc_expected` để biết lỗi đã chạm retrieval chưa |

---

## Mitigation

Tùy triệu chứng:
- Nếu `freshness=FAIL`: xác nhận policy đang đo `publish` hay `ingest`, rồi rerun pipeline với raw export mới hơn hoặc nới SLA nếu đây là snapshot lab có chủ đích; mọi thay đổi phải ghi rõ trong report.
- Nếu expectation `halt` fail: sửa raw hoặc cleaning rule rồi rerun; không dùng `--skip-validate` cho run nộp bài.
- Nếu eval có `hits_forbidden=yes`: chạy lại pipeline chuẩn không dùng `--no-refund-fix`, sau đó rerun eval để xác nhận context stale đã bị loại.
- Nếu inject-bad vừa được demo: rerun pipeline chuẩn để publish snapshot sạch trước khi grading.

---

## Prevention

Các biện pháp phòng ngừa nên ghi nhận:
- Duy trì freshness check ở cuối mỗi `run` và cho phép kiểm riêng bằng command `freshness`.
- Giữ `manifest` cho từng run để có lineage tối thiểu giữa raw, cleaned, quarantine và collection.
- Mở rộng expectation cho các failure mode mới, đặc biệt các lỗi ảnh hưởng trực tiếp đến retrieval.
- Theo dõi theo thứ tự ưu tiên: freshness -> volume -> schema -> lineage -> mới đến prompt/model.
- Chỉ publish snapshot đã qua expectation; dùng `--skip-validate` và `--no-refund-fix` riêng cho kịch bản inject có chủ đích.
