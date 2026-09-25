
## Phân công

| Người | Vai trò | File phụ trách |
|---|---|---|
| **A** | **Trưởng nhóm, Pipeline Lead + Data Foundation** | `src/core/config.py`, `src/core/utils.py`, `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` |
| **Nguyễn Khắc Giáp** | **RAG Specialist** (kiêm ghép luồng Phase 1) | `src/retrieval/embeddings.py`, `src/retrieval/index.py`, `src/retrieval/qa.py`, `src/retrieval/agent.py`, `src/retrieval/llm.py`, `src/pipelines/phase1.py`, `script/run_phase1.py` |
| **C** | **Observability & Evaluation Lead** | `src/observability/quality.py` (GX 1.x + Freshness SLA), `src/observability/reporting.py`, `src/evaluation/testset.py`, `src/evaluation/metrics.py`, `docs/TEAM.md`, `report/group_report.md` |

## Việc của từng người theo checkpoint

| CP | A | B | C |
|---|---|---|---|
| **CP0** (0–30') | Tạo `.env`, `config.py`/`utils.py`, viết `parse_crossref_payload()` có fallback về snapshot local → tải đủ 24 bài | Cài môi trường, tải sẵn model `all-MiniLM-L6-v2`, dựng khung ChromaDB | Cài môi trường, đọc `RUBRIC.md`, dựng khung GX ephemeral context |
| **CP1** (30–65') | `build_clean_dataframe`: loại trùng theo `paper_id`, tính `age_days`, ghép `text_for_embedding` | Viết `embeddings.py` và `index.py` dựa trên schema clean đã thống nhất | Viết 4 Expectations, Freshness SLA (quá 25% bài có `age_days > 180` thì `is_fresh=False`) |
| **CP2** (65–95') | Review lại dữ liệu clean, bắt đầu viết `corruption.py` | Nạp 24 docs vào collection `papers-baseline`, viết QA agent | `testset.py` sinh 10 câu hỏi thuộc 4 nhóm; `metrics.py` (Hit Rate, Token F1) |
| **CP3** (95–120') | Kiểm tra các artifact sinh ra | **Ghép `phase1.py`**, chạy `run_phase1.py` | Sinh `baseline_metrics.json` và `phase1_report.md` |
| **CP4** (120–165') | Hoàn thiện 6 kịch bản tiêm lỗi, ghi `corruption_log.json` | Tạo collection `papers-corrupted`, chạy RAG trên dữ liệu lỗi | Chứng minh GX/Freshness phát cảnh báo, đo `corrupted_metrics.json` |
| **CP5** (165–210') | **Ghép `corruption_flow.py`**, viết repair idempotent từ raw (chạy 2 lần phải cho kết quả như nhau) | Tạo collection `papers-repaired`, đo lại RAG | Viết `corruption_report.md` so sánh 3 cột: Baseline, Corrupted, Repaired |
| **CP6** (210–240') | Chạy demo trên terminal, trả lời câu hỏi về tính idempotent và lineage | Trả lời câu hỏi về embedding/vector | Trình bày bảng 3 trạng thái và hiện tượng Silent Failure, trả lời câu hỏi về GX và SLA |

## Nguyên tắc phối hợp
- **Chốt schema clean ở phút thứ 35**, trước khi bắt đầu CP1. A công bố danh sách cột (`paper_id`, `title`, `summary`, `published`, `age_days`, `text_for_embedding`…) để B và C code song song mà không phải chờ.
- **Khối lượng:** A nhiều việc nhất trong CP4–CP5, B nhiều nhất trong CP2–CP3, C đều trong suốt buổi. Người nào rảnh thì giúp người đang ở phần gấp nhất.
- **Commit:** mỗi người tự commit phần của mình lên `main`. Cả 3 phải xuất hiện trong Contributors và mỗi người **tự nộp link repo lên LMS**.
- Mỗi người viết báo cáo cá nhân `report/<MSSV>_HoTen.md`.

Bạn có muốn mình điền bảng này vào [docs/TEAM.md](docs/TEAM.md), thay cho bảng 4 người hiện có, không? Chỉ cần gửi mình họ tên, MSSV và email của 3 người.