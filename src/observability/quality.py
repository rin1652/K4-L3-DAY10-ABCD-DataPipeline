from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations.core.expectation_suite import ExpectationSuite

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the data quality gate using the Great Expectations 1.x API."""
    required_columns = {"paper_id", "title", "summary", "text_for_embedding"}
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns for quality checks: {missing_columns}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = ExpectationSuite(name=f"{report_name}_quality_suite")
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )
    for column in ("paper_id", "title", "text_for_embedding"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=column)
        )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="summary", min_value=30
        )
    )

    gx_result = batch.validate(suite)
    freshness = build_freshness_report(
        df,
        settings,
        settings.paths.freshness_report,
        write_report=True,
    )

    result: dict[str, Any] = {
        "success": bool(gx_result.success),
        "report_name": report_name,
        "run_at": datetime.now(UTC).isoformat(),
        "great_expectations": gx_result.to_json_dict(),
        "freshness": freshness,
        "freshness_warning": bool(freshness["stale_ratio"] > 0.25),
    }
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return result


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: str | Path,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    """Summarize publication freshness and optionally persist it as JSON."""
    if "published" not in df.columns:
        raise ValueError("Column 'published' is required for the freshness check")

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    run_date = pd.Timestamp.now(tz="UTC")
    age_days = (run_date - published).dt.days
    threshold = settings.freshness_threshold_days
    valid_age = age_days.dropna()
    stale_rows = int((valid_age > threshold).sum())
    total_rows = int(len(df))
    stale_ratio = stale_rows / total_rows if total_rows else 0.0
    latest = published.max()
    oldest = published.min()

    payload: dict[str, Any] = {
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "threshold_days": threshold,
        "stale_ratio_limit": 0.25,
        "is_fresh": stale_ratio <= 0.25,
        "warning": stale_ratio > 0.25,
    }
    if write_report:
        path = Path(report_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
