# Corruption Flow Report

## Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Rows | 24 | 24 | 24 |
| Unique paper IDs | 24 | 19 | 24 |
| Duplicate rows | 0 | 5 | 0 |
| Blank summaries | 0 | 6 | 0 |
| Truncated titles | 0 | 5 | 0 |
| Stale rows | 1 | 7 | 1 |

## Corruption Scenarios

- `drop_latest_records`: 5 rows
- `blank_summary`: 5 rows
- `inject_text_noise`: 5 rows
- `truncate_title`: 5 rows
- `stale_date`: 7 rows
- `duplicate_rows`: 5 rows

## Repair

Repair is idempotent because it rebuilds the clean dataset from `data/raw/crossref_records.json` instead of mutating the corrupted file in place.
