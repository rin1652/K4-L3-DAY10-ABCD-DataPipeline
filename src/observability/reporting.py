from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "n/a"
    return str(value)


def _metric_rows(metrics: dict[str, Any]) -> str:
    keys = (
        "samples",
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    )
    lines = ["| Metric | Value |", "| --- | ---: |"]
    for key in keys:
        if key in metrics:
            lines.append(f"| `{key}` | {_fmt(metrics[key])} |")
    ragas = metrics.get("ragas")
    if ragas is not None:
        lines.append(f"| `ragas` | {_fmt(ragas)} |")
    return "\n".join(lines)


def _quality_rows(quality: dict[str, Any]) -> str:
    results = quality.get("great_expectations", {}).get("results", [])
    if not results:
        return f"- Quality gate success: `{quality.get('success')}`"
    lines = ["| Expectation | Success | Observed |", "| --- | --- | --- |"]
    for item in results:
        config = item.get("expectation_config", {})
        observed = item.get("result", {}).get("observed_value", "")
        lines.append(
            f"| `{config.get('type', 'unknown')}` | {item.get('success')} | {_fmt(observed)} |"
        )
    return "\n".join(lines)


def _freshness_block(freshness: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- Latest published: `{_fmt(freshness.get('latest_published'))}`",
            f"- Oldest published: `{_fmt(freshness.get('oldest_published'))}`",
            f"- Stale rows: `{_fmt(freshness.get('stale_rows'))}` / `{_fmt(freshness.get('total_rows'))}`",
            f"- Stale ratio: `{_fmt(freshness.get('stale_ratio'))}` (limit `{_fmt(freshness.get('stale_ratio_limit', 0.25))}`)",
            f"- Threshold days: `{_fmt(freshness.get('threshold_days'))}`",
            f"- is_fresh: `{freshness.get('is_fresh')}`",
            f"- Warning: `{freshness.get('warning')}`",
        ]
    )


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
    answers: list[dict[str, Any]] | None = None,
) -> None:
    """Write the baseline markdown report from source, metrics, quality, freshness, and optional answers."""
    source_lines = "\n".join(f"- `{key}`: {_fmt(value)}" for key, value in source_summary.items()) or "- n/a"
    answer_rows = []
    for item in (answers or [])[:5]:
        answer_rows.append(
            "| {id} | {kind} | {hit} | {f1:.3f} | {score} |".format(
                id=item.get("id", ""),
                kind=item.get("question_type", item.get("type", "")),
                hit=item.get("retrieval_hit", ""),
                f1=float(item.get("token_f1", 0.0)),
                score=(item.get("judge") or {}).get("score", ""),
            )
        )

    body = f"""# Phase 1 - Baseline Report

## Source

{source_lines}

## Retrieval and evaluation

{_metric_rows(metrics)}

## Data quality

Quality gate success: `{quality.get("success")}`

{_quality_rows(quality)}

## Freshness SLA

{_freshness_block(freshness)}
"""
    if answer_rows:
        body += "\n## Sample Answers\n\n"
        body += "| ID | Type | Retrieval hit | Token F1 | Judge score |\n"
        body += "| --- | --- | ---: | ---: | ---: |\n"
        body += "\n".join(answer_rows) + "\n"
    write_text(Path(report_path), body)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the three-state comparison: baseline vs corrupted vs repaired."""
    metric_keys = (
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    )
    rows = ["| Metric | Baseline | Corrupted | Repaired |", "| --- | ---: | ---: | ---: |"]
    for key in metric_keys:
        rows.append(
            "| `{key}` | {base} | {corrupted} | {repaired} |".format(
                key=key,
                base=_fmt(baseline_metrics.get(key)),
                corrupted=_fmt(corrupted_metrics.get(key)),
                repaired=_fmt(repaired_metrics.get(key)),
            )
        )
    rows.append(
        "| Quality gate success | n/a | {corrupted} | {repaired} |".format(
            corrupted=_fmt(corrupted_quality.get("success")),
            repaired=_fmt(repaired_quality.get("success")),
        )
    )
    rows.append(
        "| Freshness `is_fresh` | n/a | {corrupted} | {repaired} |".format(
            corrupted=_fmt(corrupted_freshness.get("is_fresh")),
            repaired=_fmt(repaired_freshness.get("is_fresh")),
        )
    )
    rows.append(
        "| Freshness warning | n/a | {corrupted} | {repaired} |".format(
            corrupted=_fmt(corrupted_freshness.get("warning")),
            repaired=_fmt(repaired_freshness.get("warning")),
        )
    )

    body = f"""# Corruption Report - Baseline vs Corrupted vs Repaired

Silent failure means the RAG agent still answers after bad data lands. The quality gate and freshness SLA are the signals that should fire before that data is served.

## Three-state comparison

{chr(10).join(rows)}

## Corrupted data quality

Quality gate success: `{corrupted_quality.get("success")}`

{_quality_rows(corrupted_quality)}

### Corrupted freshness

{_freshness_block(corrupted_freshness)}

## Repaired data quality

Quality gate success: `{repaired_quality.get("success")}`

{_quality_rows(repaired_quality)}

### Repaired freshness

{_freshness_block(repaired_freshness)}
"""
    write_text(Path(report_path), body)
