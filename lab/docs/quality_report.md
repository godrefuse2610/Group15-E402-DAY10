# Quality report — Lab Day 10 (Nhóm 15)

**run_id:** 2026-04-15T08-14Z  
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (Baseline) | Sau (Pipeline Run) | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Đã ingest toàn bộ dữ liệu mẫu. |
| cleaned_records | N/A | 6 | Data hợp lệ. |
| quarantine_records | N/A | 4 | Đã bắt được các vi phạm (VD: version cũ, thiếu metadata). |
| Expectation halt? | N/A | Không | Pipeline chạy thành công, không bị halt. |

---

## 2. Before / after retrieval (bắt buộc)

> Bằng chứng từ `artifacts/eval/before_inject_bad.csv` (inject lỗi) và `artifacts/eval/after_fix_final.csv` (đã fix).

**Câu hỏi then chốt:** refund window (`q_refund_window`)  
**Trước (Inject Bad):** `policy_refund_v4|it_helpdesk_faq|policy_refund_v4` | Yêu cầu được gửi trong vòng 14 ngày làm việc... | hits_forbidden=yes (Vẫn còn chứa dữ liệu stale 14 ngày).
**Sau (Đã fix):** `policy_refund_v4|it_helpdesk_faq|policy_refund_v4` | Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng. | hits_forbidden=no (Pipeline đã loại bỏ thông tin stale 14 ngày thành công).

**Merit (khuyến nghị):** versioning HR — `q_leave_version` (`contains_expected`, `hits_forbidden`, cột `top1_doc_expected`)

**Trước (Inject Bad):** `contains_expected=yes`, `hits_forbidden=no`.  
**Sau (Đã fix):** `contains_expected=yes`, `hits_forbidden=no`, `top1_doc_expected=yes`. Khẳng định chính sách 2026 với 12 ngày phép. Pipeline đã loại trừ các chunk policy HR cũ (trước 2026-01-01) ổn định.

---

## 3. Freshness & monitor

> Kết quả lập lịch / đánh giá Freshness từ file logs.

**Kết quả check:** freshness_check=FAIL `{"latest_exported_at": "2026-04-10T08:00:00", "age_hours": 120.253, "sla_hours": 24.0, "reason": "freshness_sla_exceeded"}` 

**Giải thích:** Nhóm chọn SLA freshness 24h đối với việc thu nạp policy. Do `latest_exported_at` ở mốc quá khứ (5 ngày trước), pipeline đã cảnh báo FAIL. Tính năng này đóng vai trò chốt chặn quan trọng nhằm tránh để hệ thống RAG phục vụ bộ dữ liệu quá hạn.

---

## 4. Corruption inject (Sprint 3)

Nhóm đã sử dụng cờ `--no-refund-fix` để kiểm tra độ nhạy của pipeline. Dữ liệu với "14 ngày hoàn tiền" đã vượt qua khỏi block cleaning, đi thẳng vào Vector Store và khiến đánh giá chất lượng `eval` báo `hits_forbidden=yes`. Việc này chứng minh pipeline nếu không có Expectation Suite và Cleaning Rule đầy đủ sẽ lan truyền trực tiếp dữ liệu xấu lên tầng Agent.

---

## 5. Hạn chế & việc chưa làm

- Freshness checking hiện mới chỉ có log trên hệ thống. 
- Chưa tích hợp với các bot alert (như Slack/Teams) khi Expectation Suite halt hoặc cảnh báo mức độ warn.
