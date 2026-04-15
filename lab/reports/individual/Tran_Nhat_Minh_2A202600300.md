# Báo Cáo Cá Nhân — Lab Day 10: Data Pipeline & Observability

**Họ và tên:** Trần Nhật Minh — 2A202600300
**Vai trò:** Embed & Idempotency Owner
**Ngày nộp:** 15/04/2026
**Độ dài yêu cầu:** 400–650 từ

---

## 1. Tôi phụ trách phần nào?

**File / module:**

- `etl_pipeline.py` → hàm `cmd_embed_internal()` (dòng 137–207): toàn bộ logic upsert + prune ChromaDB
- `eval_retrieval.py`: script đánh giá retrieval trước/sau theo keyword
- `grading_run.py`: sinh JSONL chấm điểm 3 câu grading
- `tests/test_embed_owner.py`: 4 bài kiểm thử tự động xác nhận idempotency và eval output

**Kết nối với thành viên khác:**

Tôi nhận `cleaned_*.csv` từ Cleaning Owner và đẩy vào ChromaDB collection `day10_kb`. Sau khi embed hoàn tất, Monitoring Owner đọc các trường `embed_collection_count_after` và `embed_prune_removed` trong manifest để xác nhận publish boundary. File `artifacts/eval/grading_run.jsonl` tôi sinh ra là đầu ra chấm điểm cuối cùng của cả nhóm.

**Bằng chứng:**

Run `run_id=2026-04-15T09-08Z` ghi nhận đầy đủ trong `artifacts/manifests/manifest_2026-04-15T09-08Z.json`:
`embed_snapshot_rows=6`, `embed_upserted=6`, `embed_collection_count_before=0`, `embed_prune_removed=0`, `embed_collection_count_after=6`.

---

## 2. Một quyết định kỹ thuật

Quyết định quan trọng nhất tôi đưa ra là chiến lược **upsert + prune** để đảm bảo idempotency thay vì xóa toàn bộ collection rồi insert lại. Cụ thể, mỗi lần publish, hàm `cmd_embed_internal` thực hiện ba bước:

1. Lấy `prev_ids` — tập hợp tất cả vector id đang có trong collection.
2. Tính `drop = prev_ids − chunk_ids_của_snapshot_hiện_tại` và gọi `col.delete(ids=drop)` để xóa đúng các id lạc hậu.
3. Upsert toàn bộ snapshot mới theo `chunk_id` (không tạo bản sao nếu id đã tồn tại).

Lý do tôi không chọn "delete-all rồi insert": nếu pipeline bị ngắt giữa hai bước, collection sẽ trống hoàn toàn và grading JSONL sẽ trả về rỗng. Chiến lược upsert + prune an toàn hơn và đảm bảo `hits_forbidden=false` ổn định qua nhiều lần chạy — mấu chốt của observability layer. Bài kiểm thử `test_embed_rerun_stays_idempotent` trong `tests/test_embed_owner.py` xác nhận: chạy hai lần liên tiếp cùng dữ liệu → `second["pruned_ids"] == 0`, `final_collection_count == 2`, collection không phình ra.

---

## 3. Một lỗi / anomaly đã xử lý

Sau khi chạy `python etl_pipeline.py run --run-id sprint2`, tôi kiểm tra manifest và phát hiện `manifest_sprint2.json` **thiếu hoàn toàn các trường embed** (`embedding_model`, `embed_snapshot_rows`, `embed_collection_count_after`…). Pipeline vẫn in `PIPELINE_OK` và exit 0, nhưng index Chroma thực tế trống.

Nguyên nhân: module `chromadb` chưa được cài trong venv đang active tại thời điểm chạy — `cmd_embed_internal` trả về `None` ngay ở dòng 142–143, và `cmd_run` tiếp tục ghi manifest mà không có khối embed. Log có dòng `ERROR: chromadb chưa cài` nhưng pipeline không exit sớm.

Fix: kích hoạt đúng venv (`source .venv/bin/activate`) rồi chạy `pip install -r requirements.txt`. Chạy lại với `run-id=sprint2-rerun` và kiểm tra log — lần này xuất hiện `embed_upsert count=6 collection=day10_kb`. Run `2026-04-15T09-08Z` là lần chạy chuẩn đầu tiên có đủ tất cả trường embed trong manifest.

---

## 4. Bằng chứng trước / sau

Từ `artifacts/eval/before_after_eval.csv` (chạy sau khi pipeline sạch, `run_id=2026-04-15T09-08Z`):

| scenario | question_id | contains_expected | hits_forbidden | top1_doc_expected |
|----------|-------------|:-----------------:|:--------------:|:-----------------:|
| after_fix | q_refund_window | yes | no | — |
| after_fix | q_leave_version | yes | no | yes |

`q_refund_window` trả về "7 ngày làm việc" trong top-1 preview, không còn "14 ngày" xuất hiện trong top-k (`hits_forbidden=no`). `q_leave_version` truy hồi đúng `hr_leave_policy` làm top-1 (`top1_doc_expected=yes`), xác nhận version 2026 (12 ngày phép) đã thay thế hoàn toàn version cũ (10 ngày) ra khỏi index.

---

## 5. Cải tiến tiếp theo

Nếu có thêm 2 giờ, tôi sẽ bổ sung kịch bản `inject_bad` vào eval: chạy `etl_pipeline.py run --no-refund-fix --skip-validate`, lưu eval ra `artifacts/eval/before_inject_bad.csv` với `--scenario inject_bad`. Như vậy nhóm sẽ có so sánh hai chiều thật sự — dòng `inject_bad` với `hits_forbidden=yes` đặt cạnh `after_fix` với `hits_forbidden=no` — thay vì bằng chứng một chiều như hiện tại.
