# Phase 1 - Baseline Report

## Source

- `source_api`: Crossref REST API
- `mode`: offline snapshot (data/raw/crossref_response.json)
- `query`: agentic retrieval augmented generation large language model
- `filter`: from-pub-date:2026-03-29,has-abstract:true
- `raw_records`: 24
- `clean_rows`: 24
- `run_date_utc`: 2026-09-25 09:19
- `embedding_model`: sentence-transformers/all-MiniLM-L6-v2
- `chroma_collection`: papers-baseline
- `llm`: gemini/gemini-2.5-flash

## Retrieval and evaluation

| Metric | Value |
| --- | ---: |
| `samples` | 10 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |
| `ragas` | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |

## Data quality

Quality gate success: `True`

| Expectation | Success | Observed |
| --- | --- | --- |
| `expect_table_row_count_to_be_between` | True | 24 |
| `expect_column_values_to_not_be_null` | True |  |
| `expect_column_values_to_be_unique` | True |  |
| `expect_column_values_to_not_be_null` | True |  |
| `expect_column_values_to_not_be_null` | True |  |
| `expect_column_value_lengths_to_be_between` | True |  |

## Freshness SLA

- Latest published: `2026-07-22`
- Oldest published: `2026-03-28`
- Stale rows: `1` / `24`
- Stale ratio: `0.0417` (limit `0.2500`)
- Threshold days: `180`
- is_fresh: `True`
- Warning: `False`

## Sample Answers

| ID | Type | Retrieval hit | Token F1 | Judge score |
| --- | --- | ---: | ---: | ---: |
| eval_001 | summary | True | 1.000 | 5 |
| eval_002 | summary | True | 1.000 | 5 |
| eval_003 | summary | True | 1.000 | 5 |
| eval_004 | authors | True | 1.000 | 5 |
| eval_005 | authors | True | 1.000 | 5 |
