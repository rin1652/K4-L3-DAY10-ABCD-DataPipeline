# Báo cáo cá nhân — Đoàn Tuấn Long

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đoàn Tuấn Long |
| MSSV | 2A202602609 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | ABCD |
| Vai trò chính | C — Observability & Evaluation Lead |
| Repository | https://github.com/rin1652/K4-L3-DAY10-ABCD-DataPipeline.git |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
| --- | --- | --- | --- | --- |
| Quality Gate GX 1.x + Freshness SLA | `src/observability/quality.py` | Dataframe clean | Báo cáo JSON trong `data/quality/` | Hoàn thành |
| Bộ đề 10 câu | `src/evaluation/testset.py` → `build_test_set` | Dataframe có `paper_id`, `title`, `summary`, `authors`, `categories`, `published` | `data/eval/test_set.json` | Hoàn thành |
| Hit Rate, Token F1, LLM Judge | `src/evaluation/metrics.py` → `evaluate_pipeline` | Test set + vector index | `*_metrics.json`, `*_answers.json` | Hoàn thành (chờ pipeline gọi) |
| Báo cáo Markdown | `src/observability/reporting.py` | Metrics, quality, freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành (chờ pipeline gọi) |

## 3. Kết quả theo vai trò

Đã sinh `data/eval/test_set.json`: 10 câu, gồm 3 `summary`, 3 `authors`, 2 `date`, 2 `categories`. Mỗi câu có `ground_truth` và `ground_truth_doc_ids`.

Số liệu baseline / corrupted / repaired chưa ghi ở đây vì `run_phase1.py` và `run_corruption_flow.py` chưa chạy xong. Kết luận metric chỉ điền sau khi có file trong `data/results/`.

## 4. Cách xác minh

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(len(ts))"
```

Kỳ vọng: in ra `10` sau khi A đã có `data/clean/papers_clean.json`.

## 5. Cam kết

- Nội dung phản ánh phần việc Observability & Evaluation, không nhận phần ingestion hay RAG index.
- Không ghi pipeline đã chạy thành công khi chưa có artifact metrics.
- Báo cáo không chứa API key.

**Họ và tên:** Đoàn Tuấn Long  
**Ngày xác nhận:** 2026-09-25
