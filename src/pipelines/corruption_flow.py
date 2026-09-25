from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_json, write_text
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_build_test_set
from ingestion.cleaning import build_clean_dataframe, save_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from retrieval.index import LocalEmbeddingIndex

RAG_METRICS = [
    ("Retrieval hit rate", "retrieval_hit_rate"),
    ("Mean token F1", "mean_token_f1"),
    ("Judge accuracy", "judge_accuracy"),
    ("Mean judge score", "mean_judge_score"),
]


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

    # B: index each state into its own Chroma collection and score it on the same frozen test set.
    rag = evaluate_rag_states(settings, baseline_df, corrupted_df, repaired_df)
    baseline_profile["rag"] = rag["baseline"]
    corrupted_profile["rag"] = rag["corrupted"]
    repaired_profile["rag"] = rag["repaired"]

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


def evaluate_rag_states(
    settings: Settings,
    baseline_df: pd.DataFrame,
    corrupted_df: pd.DataFrame,
    repaired_df: pd.DataFrame,
) -> dict[str, dict[str, Any]]:
    """Build papers-baseline / papers-corrupted / papers-repaired and evaluate each one.

    The test set is built from the baseline (trusted) data and then frozen, so all three
    states answer the exact same questions and only the indexed data differs.
    """
    paths = settings.paths
    load_or_build_test_set(baseline_df, paths.eval_testset, refresh=settings.refresh_test_set)

    states = {
        "baseline": (baseline_df, paths.embeddings_json, paths.baseline_metrics, paths.baseline_answers),
        "corrupted": (corrupted_df, paths.corrupted_embeddings_json, paths.corrupted_metrics, paths.corrupted_answers),
        "repaired": (repaired_df, paths.repaired_embeddings_json, paths.repaired_metrics, paths.repaired_answers),
    }
    summaries: dict[str, dict[str, Any]] = {}
    for state, (df, embeddings_path, metrics_path, answers_path) in states.items():
        index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
        bundle = evaluate_pipeline(settings, index, paths.eval_testset, metrics_path, answers_path)
        summaries[state] = {"collection": index.collection_name, **bundle.summary}
        print(f"[RAG] {state:<9} -> '{index.collection_name}' ({len(index.documents)} docs) "
              f"hit_rate={bundle.summary['retrieval_hit_rate']:.3f} "
              f"token_f1={bundle.summary['mean_token_f1']:.3f} "
              f"judge_acc={bundle.summary['judge_accuracy']:.3f}")
    return summaries


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
            "## RAG Quality",
            "",
            "| Metric | Baseline | Corrupted | Repaired |",
            "| --- | ---: | ---: | ---: |",
            *[
                rag_comparison_row(label, key, baseline_profile, corrupted_profile, repaired_profile)
                for label, key in RAG_METRICS
            ],
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


def rag_comparison_row(
    label: str,
    key: str,
    baseline_profile: dict[str, Any],
    corrupted_profile: dict[str, Any],
    repaired_profile: dict[str, Any],
) -> str:
    values = [f"{profile['rag'][key]:.3f}" for profile in (baseline_profile, corrupted_profile, repaired_profile)]
    return f"| {label} | {' | '.join(values)} |"


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
    for label, key in RAG_METRICS:
        print(rag_comparison_row(label, key, baseline_profile, corrupted_profile, repaired_profile))
