from __future__ import annotations

import math
import random
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json
from ingestion.cleaning import refresh_derived_columns

SEED = 42
DROP_LATEST_FRACTION = 0.20
BLANK_SUMMARY_FRACTION = 0.25
NOISE_FRACTION = 0.25
TRUNCATE_TITLE_FRACTION = 0.25
TRUNCATED_TITLE_CHARS = 7
STALE_DATE_FRACTION = 0.35
STALE_SHIFT_DAYS = 365 * 5
DUPLICATE_FRACTION = 0.20
NOISE_TOKENS = ["#@!$", "~~%^&", "qz9$$x", "@@##", "NULL_TOKEN", "|/|\\|", "&&**", "xkcd###"]


def _pick(rng: random.Random, df: pd.DataFrame, fraction: float) -> list[int]:
    count = max(1, math.ceil(len(df) * fraction))
    return sorted(rng.sample(list(df.index), min(count, len(df))))


def _inject_noise(text: str, rng: random.Random) -> str:
    """Interleave junk tokens every ~3 words so both embeddings and extracted answers degrade."""
    words = text.split()
    noisy: list[str] = []
    for position, word in enumerate(words):
        if position % 3 == 0:
            noisy.append(rng.choice(NOISE_TOKENS))
        noisy.append(word)
    return " ".join(noisy)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply 6 deterministic (seeded) corruption scenarios to a clean dataframe and log each one."""
    rng = random.Random(SEED)
    corrupted = df.copy().reset_index(drop=True)
    log: list[dict[str, Any]] = []

    def record(scenario: str, description: str, rows: pd.DataFrame | list[str], **params: Any) -> None:
        paper_ids = rows if isinstance(rows, list) else rows["paper_id"].tolist()
        log.append(
            {
                "scenario": scenario,
                "description": description,
                "affected_rows": len(paper_ids),
                "affected_paper_ids": paper_ids,
                "params": params,
            }
        )

    # 1. Drop latest records (lost fresh data).
    drop_count = max(1, math.ceil(len(corrupted) * DROP_LATEST_FRACTION))
    latest = corrupted.sort_values(["published", "paper_id"], ascending=[False, True]).head(drop_count)
    corrupted = corrupted.drop(index=latest.index).reset_index(drop=True)
    record("drop_latest_records", "Removed the newest papers (fresh data never landed).", latest,
           fraction=DROP_LATEST_FRACTION)

    # 2. Blank summary (empty scrape).
    rows = _pick(rng, corrupted, BLANK_SUMMARY_FRACTION)
    record("blank_summary", "Summary replaced by an empty string.", corrupted.loc[rows],
           fraction=BLANK_SUMMARY_FRACTION)
    corrupted.loc[rows, "summary"] = ""

    # 3. Inject text noise into the summary (flows into text_for_embedding on rebuild).
    rows = _pick(rng, corrupted, NOISE_FRACTION)
    record("inject_text_noise", "Junk symbol tokens interleaved every 3 words of the summary.", corrupted.loc[rows],
           fraction=NOISE_FRACTION, tokens=NOISE_TOKENS)
    corrupted.loc[rows, "summary"] = [_inject_noise(text, rng) for text in corrupted.loc[rows, "summary"]]

    # 4. Truncate title.
    rows = _pick(rng, corrupted, TRUNCATE_TITLE_FRACTION)
    record("truncate_title", f"Title cut to the first {TRUNCATED_TITLE_CHARS} characters.", corrupted.loc[rows],
           fraction=TRUNCATE_TITLE_FRACTION, max_chars=TRUNCATED_TITLE_CHARS)
    corrupted.loc[rows, "title"] = corrupted.loc[rows, "title"].str[:TRUNCATED_TITLE_CHARS]

    # 5. Stale date: shift published back so the record looks old (age_days shifts by the same amount).
    rows = _pick(rng, corrupted, STALE_DATE_FRACTION)
    record("stale_date", f"Published date moved back {STALE_SHIFT_DAYS} days.", corrupted.loc[rows],
           fraction=STALE_DATE_FRACTION, shift_days=STALE_SHIFT_DAYS)
    shifted = pd.to_datetime(corrupted.loc[rows, "published"]) - pd.Timedelta(days=STALE_SHIFT_DAYS)
    corrupted.loc[rows, "published"] = shifted.dt.strftime("%Y-%m-%d")
    corrupted.loc[rows, "age_days"] = corrupted.loc[rows, "age_days"].astype(int) + STALE_SHIFT_DAYS

    # 6. Duplicate rows (double ingestion). Duplicate enough rows to keep the lab smoke test at 24 rows.
    duplicate_count = max(1, len(df) - len(corrupted))
    rows = sorted(rng.sample(list(corrupted.index), min(duplicate_count, len(corrupted))))
    record("duplicate_rows", "Rows appended a second time with the same paper_id.", corrupted.loc[rows],
           requested_fraction=DUPLICATE_FRACTION, duplicate_count=len(rows))
    corrupted = pd.concat([corrupted, corrupted.loc[rows]], ignore_index=True)

    # 7. Rebuild text_for_embedding and other derived columns from the corrupted fields.
    corrupted = refresh_derived_columns(corrupted)

    # 8. Persist the corruption log.
    write_json(
        output_log_path,
        {
            "generated_at": now_utc().isoformat(),
            "seed": SEED,
            "input_rows": len(df),
            "output_rows": len(corrupted),
            "scenarios": log,
        },
    )
    return corrupted
