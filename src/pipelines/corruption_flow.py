from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_json, write_text
from ingestion.cleaning import build_clean_dataframe, save_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records


def main() -> None:
    """Run A-owned corruption and idempotent repair flow from trusted raw records."""
    settings = load_settings()
    run_date = datetime.now(UTC)

    raw_records = load_raw_records(settings.paths.raw_records_json)
    baseline_df = build_clean_dataframe(raw_records, run_date)
    save_dataframe(baseline_df, settings.paths.clean_csv, settings.paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    save_dataframe(corrupted_df, settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)

    repaired_df = build_clean_dataframe(raw_records, run_date)
    save_dataframe(repaired_df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)

    baseline_profile = profile_dataframe(baseline_df, settings.freshness_threshold_days)
    corrupted_profile = profile_dataframe(corrupted_df, settings.freshness_threshold_days)
    repaired_profile = profile_dataframe(repaired_df, settings.freshness_threshold_days)

    write_json(settings.paths.corrupted_metrics, corrupted_profile)
    write_json(settings.paths.repaired_metrics, repaired_profile)
    write_text(
        settings.paths.comparison_report,
        build_report(
            baseline_profile=baseline_profile,
            corrupted_profile=corrupted_profile,
            repaired_profile=repaired_profile,
            corruption_log=read_json(settings.paths.corruption_log),
        ),
    )

    print("Tín hiệu hoàn thành: Corruption flow A đã chạy xong")
    print_comparison_table(baseline_profile, corrupted_profile, repaired_profile)
    print(f"Report: {settings.paths.comparison_report}")


def profile_dataframe(df: pd.DataFrame, freshness_threshold_days: int) -> dict[str, Any]:
    duplicate_rows = int(df.duplicated("paper_id").sum()) if "paper_id" in df.columns else 0
    blank_summary_rows = int((df["summary"].fillna("").str.len() == 0).sum()) if "summary" in df.columns else 0
    truncated_title_rows = int((df["title"].fillna("").str.len() < 10).sum()) if "title" in df.columns else 0
    stale_rows = int((df["age_days"].fillna(0).astype(int) > freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    total_rows = int(len(df))
    unique_paper_ids = int(df["paper_id"].nunique()) if "paper_id" in df.columns else 0

    return {
        "rows": total_rows,
        "unique_paper_ids": unique_paper_ids,
        "duplicate_rows": duplicate_rows,
        "blank_summary_rows": blank_summary_rows,
        "truncated_title_rows": truncated_title_rows,
        "stale_rows": stale_rows,
        "stale_ratio": stale_rows / total_rows if total_rows else 0.0,
    }


def build_report(
    baseline_profile: dict[str, Any],
    corrupted_profile: dict[str, Any],
    repaired_profile: dict[str, Any],
    corruption_log: dict[str, Any],
) -> str:
    scenarios = corruption_log.get("scenarios", [])
    scenario_lines = [
        f"- `{item['scenario']}`: {item['affected_rows']} rows"
        for item in scenarios
    ]

    return "\n".join(
        [
            "# Corruption Flow Report",
            "",
            "## Comparison",
            "",
            "| Metric | Baseline | Corrupted | Repaired |",
            "| --- | ---: | ---: | ---: |",
            comparison_row("Rows", "rows", baseline_profile, corrupted_profile, repaired_profile),
            comparison_row("Unique paper IDs", "unique_paper_ids", baseline_profile, corrupted_profile, repaired_profile),
            comparison_row("Duplicate rows", "duplicate_rows", baseline_profile, corrupted_profile, repaired_profile),
            comparison_row("Blank summaries", "blank_summary_rows", baseline_profile, corrupted_profile, repaired_profile),
            comparison_row("Truncated titles", "truncated_title_rows", baseline_profile, corrupted_profile, repaired_profile),
            comparison_row("Stale rows", "stale_rows", baseline_profile, corrupted_profile, repaired_profile),
            "",
            "## Corruption Scenarios",
            "",
            *scenario_lines,
            "",
            "## Repair",
            "",
            "Repair is idempotent because it rebuilds the clean dataset from `data/raw/crossref_records.json` instead of mutating the corrupted file in place.",
            "",
        ]
    )


def comparison_row(
    label: str,
    key: str,
    baseline_profile: dict[str, Any],
    corrupted_profile: dict[str, Any],
    repaired_profile: dict[str, Any],
) -> str:
    return f"| {label} | {baseline_profile[key]} | {corrupted_profile[key]} | {repaired_profile[key]} |"


def print_comparison_table(
    baseline_profile: dict[str, Any],
    corrupted_profile: dict[str, Any],
    repaired_profile: dict[str, Any],
) -> None:
    rows = [
        ("Rows", "rows"),
        ("Unique IDs", "unique_paper_ids"),
        ("Duplicates", "duplicate_rows"),
        ("Blank summaries", "blank_summary_rows"),
        ("Truncated titles", "truncated_title_rows"),
        ("Stale rows", "stale_rows"),
    ]
    print("| Metric | Baseline | Corrupted | Repaired |")
    print("| --- | ---: | ---: | ---: |")
    for label, key in rows:
        print(f"| {label} | {baseline_profile[key]} | {corrupted_profile[key]} | {repaired_profile[key]} |")
