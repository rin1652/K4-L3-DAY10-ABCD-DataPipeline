# Group Report - Day 10: Data Pipeline & Data Observability

## 1. Thong tin bai nop

| Thong tin | Noi dung |
| --- | --- |
| Khoa/Lop | K4 |
| Ten nhom | ABCD |
| Repository | https://github.com/rin1652/K4-L3-DAY10-ABCD-DataPipeline |
| Ngay hoan thanh | 2026-09-25 |

## 2. Thanh vien va phan cong

| STT | Ho va ten | MSSV | Vai tro chinh | Module/deliverable so huu |
| ---: | --- | --- | --- | --- |
| 1 | Nguyen Dinh Phuc | 2A202602953 | Pipeline Lead + Data Foundation | `crossref.py`, `cleaning.py`, `corruption.py`, `corruption_flow.py`, clean/corrupted/repaired artifacts |
| 2 | Nguyen Khac Giap | 2A202602950 | RAG Specialist | `retrieval/`, ChromaDB, QA/retrieval, phase1 integration |
| 3 | Doan Tuan Long | 2A202602609 | Observability & Evaluation Lead | `quality.py`, `testset.py`, `metrics.py`, reports |

## 3. Tom tat ket qua

Nhom xay dung pipeline du lieu cho he thong RAG tren tap metadata bai bao Crossref. Pipeline co kha nang nap raw data tu Crossref hoac snapshot local, lam sach du lieu, tinh `age_days`, tao `text_for_embedding`, kiem tra chat luong bang Great Expectations 1.x va dua du lieu sach vao ChromaDB. Tren baseline, he thong danh gia benchmark va dat `retrieval_hit_rate = 1.000`.

Sau baseline, nhom co tinh tiem 6 dang loi du lieu de mo phong silent failure: mat ban ghi moi, summary rong, noise, title bi cat ngan, stale date va duplicate rows. Corrupted data co 19 unique paper IDs, 5 duplicate rows, 6 blank summaries va stale ratio tang len `0.2917`, vuot nguong 25%. Repair flow rebuild lai du lieu tu raw records dang tin cay, dua unique IDs ve 24, duplicate rows ve 0, blank summaries ve 0 va stale ratio ve `0.0417`.

## 4. Luong du lieu end-to-end

```text
Crossref API / local snapshot
    -> data/raw/crossref_response.json
    -> src/ingestion/crossref.py
    -> data/raw/crossref_records.json
    -> src/ingestion/cleaning.py
    -> data/clean/papers_clean.csv/json
    -> Great Expectations quality gate + freshness SLA
    -> ChromaDB papers-baseline
    -> benchmark evaluation
    -> corruption suite
    -> ChromaDB papers-corrupted
    -> repair from raw records
    -> ChromaDB papers-repaired
    -> comparison report + dashboard
```

## 5. Cau hinh va lenh chay

| Cau hinh | Gia tri |
| --- | --- |
| Python | 3.11 |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB |
| Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days |
| Corruption seed | 42 |

Baseline:

```bash
python script/run_phase1.py
```

Corruption/repair:

```bash
python script/run_corruption_flow.py
```

Frontend demo:

```bash
cd front_end
npm install
npm run dev
```

## 6. Artifact checklist

| Artifact | Duong dan | Trang thai |
| --- | --- | --- |
| Raw response | `data/raw/crossref_response.json` | Co |
| Raw records | `data/raw/crossref_records.json` | Co |
| Clean dataset | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Co |
| Corrupted dataset | `data/clean/papers_clean_corrupted.csv/json` | Co |
| Repaired dataset | `data/clean/papers_clean_repaired.csv/json` | Co |
| Test set | `data/eval/test_set.json` | Co |
| ChromaDB | `data/chroma/` | Co |
| Quality reports | `data/quality/` | Co |
| Baseline metrics | `data/results/baseline_metrics.json` | Co |
| Corruption log | `data/results/corruption_log.json` | Co |
| Corruption report | `data/reports/corruption_report.md` | Co |
| Phase 1 report | `data/reports/phase1_report.md` | Co khi chay `run_phase1.py` |
| Dashboard | `front_end/` | Co |

## 7. Ingestion va cleaning

Module `src/ingestion/crossref.py` parse payload Crossref thanh `PaperRecord`, gom cac truong `paper_id`, `title`, `summary`, `authors`, `categories`, `published`. DOI duoc chuan hoa, summary duoc xoa tag HTML/JATS, date duoc dua ve ISO `YYYY-MM-DD`. Neu API bi loi hoac bi rate limit, pipeline fallback ve snapshot local `data/raw/crossref_response.json`.

Module `src/ingestion/cleaning.py` tao clean dataframe. Cac buoc chinh:

- Chuan hoa title, summary, authors, categories.
- Tinh `age_days = (run_date - published).days`.
- Tao `authors_joined`, `categories_joined`, `summary_chars`.
- Tao `text_for_embedding` theo format Title / Authors / Published / Categories / Summary.
- Dedupe theo khoa `paper_id`.

## 8. Quality gate va freshness

| Check | Ky vong | Ket qua |
| --- | --- | --- |
| Row count | 5 den 5000 rows | Pass, 24 rows |
| Not null | `paper_id`, `title`, `text_for_embedding` | Pass |
| Unique key | `paper_id` unique | Pass tren baseline/repaired |
| Summary length | toi thieu 30 ky tu | Pass baseline |
| Freshness SLA | stale ratio <= 0.25 | Pass baseline/repaired |

Freshness baseline: latest published `2026-07-22`, oldest published `2026-03-28`, stale rows `1/24`, stale ratio `0.0417`, threshold `180 days`.

## 9. Evaluation baseline

| Metric | Gia tri | Nhan xet |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.000 | Lay dung tai lieu ground-truth |
| `mean_token_f1` | 0.238 | Cau tra loi heuristic ngan nen token overlap chua cao |
| `judge_accuracy` | 0.200 | Dung fallback heuristic khi khong dung API key |
| `mean_judge_score` | 1.400 | Co the cai thien bang LLM judge that |

## 10. Corruption scenarios

| Scenario | Mo ta | Rows anh huong |
| --- | --- | ---: |
| `drop_latest_records` | Xoa cac bai moi nhat | 5 |
| `blank_summary` | Xoa rong summary | 5 |
| `inject_text_noise` | Chen token rac vao summary/text | 5 |
| `truncate_title` | Cat ngan title | 5 |
| `stale_date` | Lui ngay cong bo 5 nam | 7 |
| `duplicate_rows` | Nhan doi rows giu cung `paper_id` | 5 |

## 11. So sanh baseline, corrupted va repaired

| Metric/signal | Baseline | Corrupted | Repaired | Nhan xet |
| --- | ---: | ---: | ---: | --- |
| Rows | 24 | 24 | 24 | Giu kich thuoc demo on dinh |
| Unique paper IDs | 24 | 19 | 24 | Duplicate lam giam ID duy nhat |
| Duplicate rows | 0 | 5 | 0 | Repair xoa trung lap |
| Blank summaries | 0 | 6 | 0 | Repair phuc hoi noi dung |
| Truncated titles | 0 | 5 | 0 | Corruption lam mat tin hieu title |
| Stale rows | 1 | 7 | 1 | Stale date lam vuot nguong freshness |
| Stale ratio | 0.0417 | 0.2917 | 0.0417 | Repair dua ve trang thai fresh |

Ket luan:

1. Corruption lam hong data contract va gay silent failure: code van chay nhung du lieu trong vector store kem tin cay hon.
2. Repair idempotent tu raw records giup phuc hoi cac signal quan trong ve baseline.

## 12. Dashboard demo

Nhom tao frontend trong `front_end/` de trinh bay Quality Gate, Freshness SLA, 6 corruption scenarios, bieu do/table Baseline vs Corrupted vs Repaired va Markdown report viewer.

## 13. Gioi han va huong cai thien

- Co the mo rong test set len nhieu cau hoi hon.
- LLM judge hien dung fallback heuristic khi khong co API key.
- Co the them pytest/CI de test ingestion, cleaning, quality va retrieval tu dong.
