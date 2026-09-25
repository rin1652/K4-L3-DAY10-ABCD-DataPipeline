# Báo cáo cá nhân — Nguyễn Khắc Giáp

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Khắc Giáp |
| MSSV | 2A202602950 |
| Khóa/Lớp | K4-L3-DAY10 |
| Tên nhóm | ABCD |
| Vai trò chính | B — RAG Specialist (kiêm tích hợp luồng Phase 1) |
| Repository | https://github.com/rin1652/K4-L3-DAY10-ABCD-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Embedding MiniLM | `src/retrieval/embeddings.py` → `MiniLMEmbeddings` | Chuỗi `text_for_embedding` | Vector 384 chiều, đã chuẩn hóa L2 | Hoàn thành |
| Vector index ChromaDB | `src/retrieval/index.py` → `LocalEmbeddingIndex.build/load/search/lookup` | Clean dataframe của A | Collection Chroma + manifest `data/embeddings/*.json` | Hoàn thành |
| QA theo ngữ cảnh | `src/retrieval/qa.py` → `answer_question` | Câu hỏi + index | `AnswerResult` (answer, doc IDs, contexts) | Hoàn thành |
| Agent dùng tool + LLM | `src/retrieval/agent.py`, `src/retrieval/llm.py` | Settings + index | Agent LangChain với 2 tool `semantic_search_papers`, `lookup_paper` | Hoàn thành |
| Luồng baseline end-to-end | `src/pipelines/phase1.py` → `main` | Raw records | Clean data, collection `papers-baseline`, test set, metrics, `phase1_report.md` | Hoàn thành |
| RAG cho 3 trạng thái (CP4–CP5) | `src/pipelines/corruption_flow.py` → `evaluate_rag_states` | 3 dataframe baseline/corrupted/repaired | 3 collection Chroma + khối `rag` trong `*_metrics.json` + bảng "RAG Quality" | Hoàn thành |

Phần của tôi nằm giữa A (Data Foundation — cung cấp clean dataframe) và C (Observability & Evaluation — dùng `LocalEmbeddingIndex` và `answer_question` trong `evaluate_pipeline` để tính metric).

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Merge nhánh `dev/long` vào `main`, xử lý conflict `cleaning.py` | Long / A | Giữ bản có `save_dataframe` và `refresh_derived_columns` để `phase1`, `corruption_flow`, `corruption.py` không bị lỗi import (commit `cbb15f8`) |
| Phát hiện `main` mất `load_or_build_test_set` và test set còn 5 câu | C | Báo lại nhóm; sau đó `testset.py` được khôi phục về bản 10 câu (`ab8e846`) |
| Sửa bug `TypeError` trong `LocalEmbeddingIndex.__init__` khi `documents=None` | A | Commit `b1ad277` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Ghép luồng Phase 1: ingest → clean → quality gate → index → test set → evaluate → report | `src/pipelines/phase1.py` | Console in đủ `[1/7]` → `[7/7]` | `python script/run_phase1.py` |
| Index 24 tài liệu vào `papers-baseline` | `retrieval/index.py` | `[4/7] Indexed 24 documents into Chroma collection 'papers-baseline'` | Log Phase 1 |
| Sửa LLM judge thất bại âm thầm | `retrieval/llm.py` | Judge trả về lý giải thật từ LLM thay vì heuristic fallback | Trường `judge.reasoning` trong `data/results/*_answers.json` |
| Tạo 3 collection tách biệt và đo RAG cho từng trạng thái | `pipelines/corruption_flow.py` → `evaluate_rag_states` | `papers-baseline`, `papers-corrupted`, `papers-repaired` | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

Output cụ thể do phần việc của tôi tạo ra: bảng **RAG Quality** trong `data/reports/corruption_report.md`, cho thấy hit rate giảm từ 1.000 xuống 0.500 khi dữ liệu bị tiêm lỗi và phục hồi về 1.000 sau repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Agent chỉ tốt bằng dữ liệu nằm trong vector store. Phần RAG phải (1) biến clean data thành các vector có thể tìm kiếm được, (2) trả lời câu hỏi dựa trên tài liệu tìm được, và (3) cho phép so sánh khách quan cùng một hệ thống RAG trên 3 phiên bản dữ liệu khác nhau mà không để chúng lẫn vào nhau.

### Cách triển khai

- **Embedding:** dùng `sentence-transformers/all-MiniLM-L6-v2` với `normalize_embeddings=True`, nên cosine similarity tương đương tích vô hướng. Model được cache bằng `lru_cache` để 3 lần build index không phải tải lại.
- **Index:** mỗi dòng clean thành một document với `record_id = "{paper_id}::{vị trí}"`. ID có thêm vị trí vì dữ liệu corrupted có dòng trùng `paper_id`; nếu chỉ dùng `paper_id` thì Chroma sẽ báo trùng ID. Collection tạo với `hnsw:space = cosine`, và điểm trả về là `score = 1 − distance`. Mỗi lần build sẽ xóa rồi tạo lại collection, nên chạy lại bao nhiêu lần kết quả vẫn như nhau (idempotent).
- **Tên collection theo trạng thái:** `_derive_collection_name` ánh xạ đường dẫn manifest sang `papers-baseline` / `papers-corrupted` / `papers-repaired`, nên pipeline chỉ cần truyền đúng `embeddings_path`.
- **QA:** nếu câu hỏi chứa tên bài báo trong dấu `'...'` thì ưu tiên tra cứu chính xác theo title (`lookup`), sau đó ghép với kết quả semantic search đã loại trùng. Câu trả lời lấy từ metadata của tài liệu đứng đầu, tùy loại câu hỏi (authors / date / categories / câu đầu của summary).
- **Quality gate trước khi index:** trong `phase1.py`, nếu `run_data_quality_checks` trả về `success=False` thì pipeline dừng với `RuntimeError` và không nạp dữ liệu vào Chroma. Dữ liệu xấu không bao giờ tới được serving layer.
- **Agent demo:** chạy trong `try/except`. Nếu thiếu key hoặc LLM lỗi thì chỉ ghi warning, không làm hỏng baseline.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Dataframe có `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `abs_url`, `pdf_url`, `text_for_embedding` |
| Output | Collection Chroma trong `data/chroma/`; manifest `data/embeddings/papers_embeddings{,_corrupted,_repaired}.json`; `AnswerResult` cho mỗi câu hỏi |
| Module phụ thuộc | `ingestion/cleaning.py` (A), `core/config.py` |
| Module sử dụng output | `evaluation/metrics.py` → `evaluate_pipeline` (C), `observability/reporting.py` (C) |
| Điều kiện lỗi cần xử lý | Quality gate fail → không index; collection chưa tồn tại → `search` báo lỗi rõ ràng; LLM không khả dụng → agent demo bị bỏ qua mà không làm dừng pipeline |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Phase 1 in đủ 7 bước; corruption flow sinh bảng so sánh RAG cho 3 collection.
- **Kết quả thực tế:** Phase 1 in `[4/7] Indexed 24 documents into Chroma collection 'papers-baseline'` và `[6/7] Baseline hit_rate=1.000 token_f1=1.000 judge_acc=1.000` (test set 10 câu). Bảng RAG Quality có đủ 3 cột (mục 8).
- **Artifact/log:** `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh chất lượng RAG trên dữ liệu sạch, dữ liệu lỗi và dữ liệu đã phục hồi.
- **Các phương án đã cân nhắc:**
  1. Dùng một collection duy nhất, xóa rồi nạp lại dữ liệu cho từng trạng thái.
  2. Tách 3 collection riêng (`papers-baseline`, `papers-corrupted`, `papers-repaired`) trong cùng một Chroma persistent store.
- **Phương án đã chọn:** Tách 3 collection, và cả 3 được đánh giá trên **cùng một test set đã đóng băng**, sinh từ dữ liệu baseline.
- **Lý do:** Với một collection, chạy trạng thái sau sẽ ghi đè trạng thái trước, nên không thể kiểm tra lại hay demo song song. Tách collection giúp cô lập hoàn toàn không gian vector: khác biệt metric chỉ đến từ dữ liệu, không đến từ câu hỏi hay thứ tự chạy. Chi phí lưu trữ thêm không đáng kể (24 tài liệu × 3).
- **Bằng chứng quyết định phù hợp:** Bảng RAG Quality cho thấy cùng code, cùng test set 10 câu, chỉ đổi collection thì hit rate đi từ 1.000 xuống 0.500 rồi về 1.000.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Pipeline vẫn chạy xong và in `judge_acc=1.000`, nhưng log có 10 dòng `POST https://api.openai.com/v1/chat/completions "HTTP/1.1 400 Bad Request"`. Agent demo báo: `Function tools with reasoning_effort are not supported for <model> in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort to 'none'.`
- **Lệnh hoặc bước tái hiện:** `LLM_PROVIDER=openai` với một reasoning model, rồi chạy `uv run python script/run_phase1.py`.
- **Nguyên nhân gốc:** Judge dùng `with_structured_output`, tức function calling. Reasoning model không cho dùng function tool qua Chat Completions API và cũng không nhận tham số `temperature`. `_judge_answer` bắt mọi exception rồi âm thầm chuyển sang heuristic dựa trên token-F1, nên `judge_accuracy` thực chất chỉ là token F1. Đây chính là một **Silent Failure** ngay trong tầng đánh giá.
- **Cách xử lý:** Trong `build_llm` cho provider `openai`: bật `use_responses_api=True` và bỏ `temperature` với reasoning model (o-series, gpt-5+). Trong `run_agent_question`: lấy `.text` vì Responses API trả `content` dạng list các block.
- **Cách xác minh sau khi sửa:** Chạy lại Phase 1: không còn lỗi 400. Trường `judge.reasoning` chứa lý giải thật (ví dụ *"The model answer matches the reference authors: …"*) thay cho chuỗi "Fallback heuristic judge used…". Agent demo trả lời đúng tác giả và nội dung bài báo.
- **Điều học được:** Một metric trông "hoàn hảo" chưa chắc đã đúng. Code đánh giá có fallback thì phải ghi lại khi fallback được dùng, nếu không nó sẽ che giấu lỗi giống hệt cách dữ liệu bẩn che giấu lỗi của agent.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** `crossref.py` lấy dữ liệu từ API (hoặc snapshot offline khi mất mạng / bị 429) và lưu raw vào `data/raw/`. `cleaning.py` chuẩn hóa text, tính `age_days`, loại trùng theo `paper_id` và ghép `text_for_embedding`. Quality gate GX kiểm tra dataframe; chỉ khi pass thì `LocalEmbeddingIndex.build` mới encode bằng MiniLM và nạp vào Chroma.
2. **Evaluation set:** mỗi câu hỏi có `ground_truth` (đáp án) và `ground_truth_doc_ids` (bài báo đúng). Retrieval hit = có ít nhất một doc ID đúng trong top-k kết quả, dùng để đo retriever. Token F1 và LLM judge so câu trả lời với `ground_truth`, dùng để đo câu trả lời.
3. **Quality checks và freshness:** quality checks (GX) kiểm tra *cấu trúc/tính hợp lệ* của từng batch: số dòng, null, unique `paper_id`, độ dài text. Freshness đo *độ mới* của cả tập: tỷ lệ bài có `age_days > 180` không được vượt 25%. Dữ liệu có thể hợp lệ hoàn toàn nhưng vẫn quá cũ.
4. **Cùng test set cho 3 trạng thái:** để biến duy nhất thay đổi là dữ liệu. Nếu sinh lại câu hỏi từ dữ liệu lỗi thì câu hỏi cũng "lỗi theo", và metric sẽ không phản ánh sự suy giảm.
5. **Repair thành công khi:** `papers_clean_repaired.json` khớp profile baseline (24 dòng, 24 ID duy nhất, 0 duplicate, 0 summary rỗng) và metric RAG trên `papers-repaired` trở về bằng baseline.

## 8. Phân tích kết quả

### Metrics chính

Nguồn: bảng RAG Quality trong `data/reports/corruption_report.md` và các file `data/results/{corrupted,repaired}_metrics.json`, cùng test set 10 câu.

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.500 | 1.000 | Suy giảm mạnh nhất: một nửa số câu không còn tìm được bài báo đúng trong top-4 |
| `mean_token_f1` | 1.000 | 0.765 | 1.000 | Giảm ít hơn hit rate: nhiều câu vẫn trả lời gần đúng nhờ metadata của bài trùng/gần giống |
| `judge_accuracy` | 1.000 | 0.800 | 1.000 | Judge "dễ dãi" hơn hit rate, nên nhìn riêng judge sẽ đánh giá thấp mức hỏng |
| `mean_judge_score` | 5.0 | 3.8 | 5.0 | Phục hồi hoàn toàn sau repair |
| Profile dữ liệu (duplicate / summary rỗng / title bị cắt) | 0 / 0 / 0 | 5 / 6 / 5 | 0 / 0 / 0 | Repair xóa sạch cả 3 loại lỗi |
| Freshness (`stale_ratio`, SLA ≤ 25%) | 1/24 | 7/24 = 29.2% | 1/24 = 4.2% | Corrupted vượt ngưỡng SLA 25% do kịch bản `stale_date` |

Ghi chú: artifact quality report riêng cho trạng thái corrupted chưa được commit, nên tôi không ghi kết quả GX cho cột Corrupted.

### Kết luận từ số liệu

1. Tiêm 6 lỗi (drop 5 bản ghi mới nhất, 5 summary rỗng, 5 chèn nhiễu, 5 title bị cắt, 7 ngày bị lùi, 5 dòng trùng) → freshness vượt SLA (29.2% > 25%) và có 5 `paper_id` trùng → hit rate giảm từ 1.000 xuống 0.500, judge accuracy từ 1.000 xuống 0.800.
2. Repair bằng cách build lại từ `data/raw/crossref_records.json` → profile về 24/24 ID duy nhất, 0 duplicate, stale 1/24 → cả 4 metric RAG về lại đúng mức baseline.

**Corruption ảnh hưởng rõ nhất:** theo phân tích cơ chế (chưa tách riêng từng kịch bản để đo), `drop_latest_records` và `truncate_title` ảnh hưởng mạnh nhất tới retrieval. Bài bị drop không còn trong index nên câu hỏi về nó chắc chắn miss. Title bị cắt làm `lookup` theo tên chính xác thất bại, nên QA phải dựa hoàn toàn vào semantic search. Dòng trùng chiếm chỗ trong top-4 nên đẩy bài đúng ra ngoài.

**Kết quả khác với kỳ vọng:** judge accuracy (0.800) cao hơn nhiều so với hit rate (0.500). Giả thuyết: khi bài đúng bị miss, top-1 thường là bài có nội dung gần giống (corpus có nhiều bài "Advanced Perspectives on …" gần trùng nội dung), nên câu trả lời vẫn gần đúng. Để kiểm chứng, cần xem `corrupted_answers.json` theo từng câu. File này chưa có trên repo nên tôi chưa kết luận được.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** tính idempotent đến từ việc *build lại từ nguồn tin cậy* (raw snapshot, xóa rồi tạo lại collection), không phải từ việc sửa tại chỗ.
2. **Observability:** quality gate phải đặt *trước* bước index, và chính tầng đánh giá cũng cần được giám sát. Judge fallback âm thầm là một silent failure y hệt dữ liệu bẩn.
3. **Ảnh hưởng tới RAG agent:** hỏng dữ liệu làm retrieval giảm một nửa, nhưng câu trả lời vẫn trôi chảy và judge vẫn cho 80% đúng. Nếu chỉ nhìn câu trả lời thì rất khó phát hiện.

### Nếu có thêm thời gian

Chạy lại corruption flow **từng kịch bản một** (6 lần, mỗi lần chỉ bật một lỗi) để đo mức giảm hit rate do riêng từng lỗi, thay vì chỉ có tác động gộp. Kèm theo đó, ghi thêm cờ `judge_fallback_used` vào metrics để phát hiện ngay khi LLM judge không khả dụng.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Khắc Giáp
**Ngày xác nhận:** 2026-09-25
