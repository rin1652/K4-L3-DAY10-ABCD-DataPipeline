# Individual Report - Nguyen Dinh Phuc

## 1. Thong tin ca nhan

| Thong tin | Noi dung |
| --- | --- |
| Ho va ten | Nguyen Dinh Phuc |
| MSSV | 2A202602953 |
| Khoa/Lop | K4 |
| Ten nhom | ABCD |
| Vai tro chinh | Pipeline Lead + Data Foundation |
| Repository | https://github.com/rin1652/K4-L3-DAY10-ABCD-DataPipeline |
| Ngay hoan thanh | 2026-09-25 |

## 2. Vai tro va pham vi cong viec

Em phu trach phan nen du lieu cua pipeline. Phan viec cua em dam bao du lieu co lineage ro rang tu raw data sang clean data, sau do tao corrupted data de thu nghiem va repair lai tu raw records dang tin cay.

| Module/deliverable | File/ham phu trach | Input | Output | Trang thai |
| --- | --- | --- | --- | --- |
| Crossref ingestion | `src/ingestion/crossref.py` | Crossref API/local snapshot | `data/raw/crossref_records.json` | Hoan thanh |
| Data cleaning | `src/ingestion/cleaning.py` | Raw `PaperRecord` | `data/clean/papers_clean.csv/json` | Hoan thanh |
| Corruption suite | `src/ingestion/corruption.py` | Clean dataframe | Corrupted dataframe + `corruption_log.json` | Hoan thanh |
| Repair flow | `src/pipelines/corruption_flow.py` | Raw records + corrupted data | Repaired data + comparison report | Hoan thanh |
| Demo support | `front_end/` | JSON/Markdown artifacts | Dashboard trinh bay | Ho tro them |

## 3. Ket qua theo vai tro

| Nhiem vu | Artifact lien quan | Ket qua | Cach xac minh |
| --- | --- | --- | --- |
| Nap raw records | `data/raw/crossref_records.json` | 24 bai bao | `fetch_source_records()` |
| Lam sach du lieu | `data/clean/papers_clean.json` | 24 rows sach | `build_clean_dataframe()` |
| Tao text cho embedding | cot `text_for_embedding` | Format Title/Authors/Published/Categories/Summary | Xem clean dataset |
| Tiem loi data | `data/results/corruption_log.json` | 6 corruption scenarios | `corrupt_clean_dataframe()` |
| Repair idempotent | `data/clean/papers_clean_repaired.json` | 24 rows, 24 unique IDs | `script/run_corruption_flow.py` |
| Bao cao comparison | `data/reports/corruption_report.md` | So sanh 3 trang thai | Markdown report |

## 4. Giai thich ky thuat

### Van de can giai quyet

RAG phu thuoc vao du lieu trong vector database. Neu du lieu bi thieu, bi trung, qua cu, summary rong hoac title bi cat ngan, he thong co the van chay nhung cau tra loi se kem hon. Day la silent failure. Phan viec cua em tao nen pipeline du lieu co the truy vet va co the phuc hoi.

### Cach trien khai

`crossref.py` parse Crossref payload thanh `PaperRecord`. Cac truong quan trong gom DOI, title, summary, authors, categories va published date. DOI duoc chuan hoa, summary duoc xoa tag HTML/JATS, date duoc dua ve ISO `YYYY-MM-DD`. Neu API that bai, pipeline fallback ve `data/raw/crossref_response.json`.

`cleaning.py` nhan raw records va tao clean dataframe. Em tinh `age_days`, tao `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`, sau do dedupe theo `paper_id`.

`corruption.py` tiem 6 dang loi du lieu co seed co dinh. `corruption_flow.py` khong sua truc tiep file corrupted ma repair bang cach build lai tu `data/raw/crossref_records.json`.

## 5. Lenh xac minh

Kiem tra ingestion:

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Da nap {len(r)} bai bao')"
```

Ket qua: `Da nap 24 bai bao`.

Kiem tra cleaning:

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean thanh cong {len(df)} dong')"
```

Ket qua: `Clean thanh cong 24 dong`.

Kiem tra corruption/repair:

```bash
python script/run_corruption_flow.py
```

Ket qua chinh:

```text
Rows: 24 -> 24 -> 24
Unique IDs: 24 -> 19 -> 24
Duplicates: 0 -> 5 -> 0
Blank summaries: 0 -> 6 -> 0
Stale ratio: 0.0417 -> 0.2917 -> 0.0417
```

## 6. Quyet dinh ky thuat quan trong

Quyet dinh quan trong nhat la cach repair du lieu. Co hai cach:

1. Sua truc tiep tren corrupted dataset.
2. Rebuild lai clean dataset tu raw records dang tin cay.

Em chon cach thu hai vi dam bao idempotent. Nghia la chay repair mot lan hay nhieu lan thi ket qua van giong nhau. Cach nay cung giu lineage ro rang: raw -> clean -> corrupted -> repaired.

Bang chung la sau repair:

- Unique paper IDs ve 24.
- Duplicate rows ve 0.
- Blank summaries ve 0.
- Stale ratio ve 0.0417.

## 7. Loi/blocker da xu ly

### Loi push GitHub

- Trieu chung: `rejected main -> main (fetch first)`.
- Nguyen nhan: Remote `main` co commit moi hon local.
- Cach xu ly: `git fetch`, `git pull --rebase origin main`, resolve conflict, push lai.
- Ket qua: Push thanh cong len `origin/main`.

### Loi report phase1

- Trieu chung: `run_phase1.py` fail o buoc tao report.
- Nguyen nhan: `src/observability/reporting.py` con TODO/chu ky ham chua khop.
- Cach xu ly: Implement `generate_phase1_report()` va `generate_corruption_report()`.
- Ket qua: `data/reports/phase1_report.md` duoc sinh thanh cong khi chay baseline pipeline.

## 8. Hieu biet ve luong end-to-end

Du lieu di tu Crossref hoac snapshot local vao `crossref.py`, sau do duoc parse thanh raw records. `cleaning.py` tao clean dataset va `text_for_embedding`. Clean dataset duoc dua vao ChromaDB de RAG truy van. Evaluation set gom cac cau hoi co ground-truth document IDs; retrieval hit rate do xem ket qua truy van co lay dung tai lieu ground-truth hay khong.

Quality checks kiem tra du lieu co dung schema va day du hay khong, con freshness monitoring kiem tra du lieu co qua cu hay khong. Baseline, corrupted va repaired phai dung cung test set de so sanh cong bang. Repair thanh cong khi data quality va metric quay ve gan baseline.

## 9. Phan tich ket qua

| Metric/signal | Baseline | Corrupted | Repaired | Nhan xet |
| --- | ---: | ---: | ---: | --- |
| Rows | 24 | 24 | 24 | So dong giu on dinh de demo |
| Unique paper IDs | 24 | 19 | 24 | Duplicate lam giam ID duy nhat |
| Duplicate rows | 0 | 5 | 0 | Repair xoa trung lap |
| Blank summaries | 0 | 6 | 0 | Repair phuc hoi summary |
| Truncated titles | 0 | 5 | 0 | Corruption lam mat tin hieu title |
| Stale rows | 1 | 7 | 1 | Stale date lam du lieu bi cu |
| Stale ratio | 0.0417 | 0.2917 | 0.0417 | Corrupted vuot nguong 25%, repaired ve fresh |

Ket luan:

1. Corruption lam data quality xau di va tao nguy co silent failure.
2. Repair tu raw records phuc hoi du lieu ve trang thai sach, co the tai lap.

## 10. Dieu hoc duoc

1. Data lineage quan trong vi giup biet du lieu den tu dau va co the rebuild khi bi loi.
2. RAG khong chi phu thuoc model ma phu thuoc rat lon vao chat luong du lieu.
3. Idempotent repair tot hon sua tay vi dam bao ket qua on dinh va de kiem chung.

## 11. Huong cai thien

- Mo rong test set tu 5 len 10+ cau hoi.
- Them pytest/CI de test tu dong ingestion, cleaning va corruption.
- Dung LLM judge that trong moi truong co API key rieng, khong commit secret.
- Them drift/freshness dashboard theo thoi gian.

## 12. Cam ket

- [x] Noi dung bao cao phan anh dung phan viec vai tro A.
- [x] Cac ket luan deu co artifact/metric doi chieu.
- [x] Bao cao khong chua API key, token hoac secret.
- [x] Co the giai thich luong raw -> clean -> corrupted -> repaired.

**Ho va ten:** Nguyen Dinh Phuc
**Ngay xac nhan:** 2026-09-25
