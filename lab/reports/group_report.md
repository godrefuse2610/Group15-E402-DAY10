# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Group 15  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Nguyễn Công Nhật Tân | Ingestion / Raw Owner | tan2610.og@gmail.com |
| Phan Nguyễn Việt Nhân | Cleaning & Quality Owner | nhanphannv@gmail.com |
| Trần Nhật Minh | Embed & Idempotency Owner | neko.rmit@gmail.com |
| Đồng Mạnh Hùng | Monitoring | hunghung12092005@gmail.com |
| Phan Anh Ly Ly | Docs Owner | lylyphan1104@gmail.com |

**Ngày nộp:** 15/04/2026 
**Repo:** godrefuse2610/Group15-E402-DAY10  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Pipeline tổng quan (150–200 từ)

**Tóm tắt luồng:**
Pipeline được xây dựng để đảm bảo toàn vẹn dữ liệu từ đầu vào cho đến khi dữ liệu được embedding vào Vector Database, phục vụ cho mô hình RAG của hệ thống. Dữ liệu Raw được xuất từ dạng CSV chứa văn bản thô, bao gồm các lỗi trộn lẫn, ngày hiệu lực sai quy chuẩn thiết kế, ký tự ẩn không nhìn thấy bằng mắt thường, và version policy đã lỗi thời.
Đầu tiên, hệ thống Ingestion nạp source `policy_export_dirty.csv`. Tầng Transform sau đó thực hiện quá trình Clean, sử dụng hàm deduplication, sửa quy đổi định dạng Date YYYY-MM-DD an toàn, fix policy thời gian refund, và mở rộng thêm 3 bộ luật đặc biệt để xử lý Unicode BOM ẩn, force lower-case document IDs và xác minh bắt buộc timestamps.
Dữ liệu sai lập tức được cách ly vào thư mục `quarantine`, chỉ phần dữ liệu 'sạch' đi qua Expectation Suite. Sau khi chạy validation thành công, các chunk hoàn chỉnh được tiến hành Embed Snapshot ổn định bằng kỹ thuật Upsert vào Chroma DB `day10_kb`. Cuối cùng hệ thống giám sát cảnh báo Freshness Check dựa trên metadata manifest SLA được thiết lập.

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**
`python etl_pipeline.py run` (Luồng chuẩn: xử lý stale data, validation, embedding).

---

## 2. Cleaning & expectation (150–200 từ)

Nhóm đã sử dụng các rule baseline bao gồm allowlist doc_id, chuyển đổi ngày ISO, bắt stale version của HR, và rule fix lỗi refund. Bên cạnh đó, nhóm đã hoàn thiện triển khai ≥3 Cleaning Rule mới phối hợp với ≥2 Expectation kiểm thử để chặn rủi ro dữ liệu triệt để.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| **R7 + E7**: `strip_invisible_unicode` & Check Invisible | Nếu bị dính Zero-width chars, file dedup hỏng. Embed Vector bẩn sinh ra kết quả chunk vector lạ. | Khi inject `\ufeff` BOM vào file raw, `E7` (halt) báo Fail ngăn chặn embed bẩn. Sau chạy fix qua `R7`, expectation Pass. | `run_2026-04-15T08-14Z.log`: expectation `no_invisible_chars_in_chunk_text` (halt) báo chunks len=0. |
| **R8**: `quarantine_missing_exported_at` | Dữ liệu không ghi rõ timestamp export được phép chạy thẳng vào Vector DB, không verify freshness được. | Dòng không chứa `exported_at` bị đánh dấu và lưu log vào file `quarantine_2026-04-15T08-14Z.csv`. | Quarantine log size: `quarantine_records: 4`. |
| **E8**: `min_doc_id_diversity` | Có khả năng xoá quá lố tay dẫn đến DB cạn kiệt kiến thức hệ thống. | Thiết lập Expectation mức (warn) kiểm tra tối thiểu 3 Docs có trong data. | `run_2026-04-15T08-14Z.log`: Expectation check đa dạng tài liệu trả kết quả `cleaned_records: 6`. |

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**
Triển khai Inject thử nghiệm lỗi với cờ `--no-refund-fix`. Cảnh báo Expectation `refund_no_stale_14d_window` lập tức kích hoạt với cờ severity `halt`, đình chỉ hoàn toàn quá trình sinh dữ liệu embedding lên Database. Để xử lý, chạy lại script không mang cờ bypass (`python etl_pipeline.py run`).

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

**Kịch bản inject:**
Để tiến hành Inject mô phỏng dữ liệu nhiễu vào model Vector và mô phỏng tác động làm sai lệch retrieval của AI Agent, nhóm đã chạy `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`. Các expectation validation hoàn toàn bị bypass, chunk với thông tin sai lệch "14 ngày làm việc" thay vì "7 ngày làm việc" đã được embed trực tiếp. Kết quả được snapshot và ghi vào `artifacts/eval/before_inject_bad.csv`. 

**Kết quả định lượng (từ CSV / bảng):**
Từ CSV test, với kịch bản câu hỏi "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền..." (`q_refund_window`), kết quả Retrieve Output hiển thị ra `contains_expected: yes` nhưng đồng thời phát sinh `hits_forbidden: yes`. Câu trả lời bao gồm tệp `"Yêu cầu được gửi trong vòng 14 ngày làm việc..."`. Việc này thể hiện rõ RAG Agent đã tham chiếu chính sách không có hiệu lực, dẫn đến tư vấn sai lệch cho khách hàng trên Production.

Sau khi pipeline được sửa lại (`after_fix_final.csv`), hệ thống lập tức cảnh báo lỗi ở khâu pipeline và block dữ liệu lỗi xuất hiện. Lúc này kết quả CSV ghi nhận Top-1 Preview là văn bản đúng `"Yêu cầu được gửi trong vòng 7 ngày làm việc..."`, tham số `hits_forbidden` trở lại status `no` tuyệt đối. Tương tự với HR Leave 2026 Policy, tài liệu cũ đã được xóa đảm bảo truy vấn được policy version mới nhất (trả về đúng 12 ngày cho rule version 2026).

---

## 4. Freshness & monitoring (100–150 từ)

Freshness Monitoring là yếu tố then chốt quản lý vòng đời bộ sưu tập Vector. Nhóm cài đặt SLA quy định tính tươi của tài liệu theo chuẩn 24 giờ. Metric đối soát thông qua field `latest_exported_at` ở cuối manifest để tính biến `age_hours` so với thực tế hiện hành. Tại lần test `run_id=2026-04-15T08-14Z`, báo cáo đánh giá **FAIL**. Lý do: timestamp của dữ liệu export ghi dưới nhãn (`2026-04-10T08:00:00`) - độ trễ dữ liệu thực tế tại thời điểm quét đạt hơn `120h` (>24h SLA). Log `freshness_sla_exceeded` cung cấp tín hiệu kịp thời báo cho Ops Team cần lập tức liên hệ Admin update export mới nếu không muốn agent AI trả lời sai ngữ cảnh thực tiễn.

---

## 5. Liên hệ Day 09 (50–100 từ)

Dữ liệu được làm sạch và embed đóng vai trò là "Data Storage Base" trực tiếp nuôi các Tool Retrieve từ Multi-agent Day 09 (VD: IT FAQ Agent, HR Agent). Việc chúng ta quy chuẩn và thanh lọc dữ liệu Stale (như nghỉ phép cũ, rules cũ) ở layer Database giúp tiết kiệm chi phí Model Prompt Injection, hạn chế Over-engineering cho Prompts khi mà Agent bị nhồi nhét tài liệu nhiễu loạn. Vector đã sạch thì LLM Agent làm suy luận nội tại đơn giản và an toàn với Hallucinations hơn.

---

## 6. Rủi ro còn lại & việc chưa làm

- Cảnh báo Freshness mới check thụ động và lưu log. Trong tương lai cần Alert Trigger qua Webhook.
- Database Metadata cần tối ưu index cho retrieval nhanh hơn khi lượng policy ngày càng khổng lồ.
