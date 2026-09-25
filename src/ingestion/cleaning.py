from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, ensure_parent, normalize_whitespace
from ingestion.crossref import PaperRecord, normalize_doi, strip_markup

CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def compose_text_for_embedding(row: dict[str, Any] | pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )


def refresh_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute helper columns that depend on title/summary/authors/categories/published."""
    df = df.copy()
    df["authors_joined"] = df["authors"].apply(lambda items: compact_join(items or []))
    df["categories_joined"] = df["categories"].apply(lambda items: compact_join(items or []))
    df["summary_chars"] = df["summary"].fillna("").str.len().astype(int)
    df["text_for_embedding"] = df.apply(compose_text_for_embedding, axis=1)
    return df


def _clean_list(values: Any) -> list[str]:
    if values is None or isinstance(values, float):
        return []
    if isinstance(values, str):
        values = [values]
    cleaned: list[str] = []
    for value in values:
        item = normalize_whitespace(str(value or ""))
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _to_date(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce", utc=True).dt.normalize()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df = pd.DataFrame([asdict(record) for record in records])

    # 1. Normalize text fields (JATS/HTML tags, entities, whitespace).
    df["paper_id"] = df["paper_id"].map(normalize_doi)
    for column in ("title", "summary", "primary_category", "abs_url", "pdf_url", "comment"):
        df[column] = df[column].map(strip_markup)
    df["authors"] = df["authors"].map(_clean_list)
    df["categories"] = df["categories"].map(_clean_list)
    df["primary_category"] = [
        primary or (categories[0] if categories else "Uncategorized")
        for primary, categories in zip(df["primary_category"], df["categories"], strict=True)
    ]

    # 2. Parse dates; 3. age_days relative to the run date.
    published = _to_date(df["published"])
    updated = _to_date(df["updated"]).fillna(published)
    run_day = pd.Timestamp(run_date if run_date.tzinfo else run_date.replace(tzinfo=UTC)).tz_convert(UTC).normalize()
    df["age_days"] = (run_day - published).dt.days

    # 5a. Filter rows that cannot be served to the RAG index.
    valid = (df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "") & published.notna()
    df, published, updated = df[valid].copy(), published[valid], updated[valid]
    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")
    df["age_days"] = df["age_days"].astype(int)

    # 4. Helper columns + text_for_embedding.
    df = refresh_derived_columns(df)

    # 5b. Deduplicate on paper_id, keeping the most recently updated version.
    df = df.sort_values(["paper_id", "updated"], ascending=[True, False]).drop_duplicates("paper_id", keep="first")

    # 6. Newest first, stable tie-break on paper_id.
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df[CLEAN_COLUMNS]


def save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    ensure_parent(csv_path)
    ensure_parent(json_path)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def load_dataframe(json_path) -> pd.DataFrame:
    return pd.read_json(json_path, orient="records", dtype=False, convert_dates=False)
