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


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw Crossref records into the schema used by the vector index."""
    if not records:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df = pd.DataFrame([asdict(record) for record in records])

    df["paper_id"] = df["paper_id"].map(normalize_doi)
    df["title"] = df["title"].map(strip_markup)
    df["summary"] = df["summary"].map(strip_markup)
    df["primary_category"] = df["primary_category"].map(strip_markup)
    df["abs_url"] = df["abs_url"].fillna("").map(lambda value: normalize_whitespace(str(value)))
    df["pdf_url"] = df["pdf_url"].fillna("").map(lambda value: normalize_whitespace(str(value)))
    df["comment"] = df["comment"].fillna("").map(strip_markup)
    df["authors"] = df["authors"].map(clean_list)
    df["categories"] = df["categories"].map(clean_list)
    df["primary_category"] = [
        primary or (categories[0] if categories else "Unknown")
        for primary, categories in zip(df["primary_category"], df["categories"], strict=True)
    ]

    published = parse_dates(df["published"])
    updated = parse_dates(df["updated"]).fillna(published)
    run_day = as_utc_timestamp(run_date).normalize()
    df["age_days"] = (run_day - published).dt.days

    valid = (df["paper_id"] != "") & (df["title"] != "") & published.notna()
    df = df[valid].copy()
    published = published[valid]
    updated = updated[valid]

    df["published"] = published.dt.strftime("%Y-%m-%d")
    df["updated"] = updated.dt.strftime("%Y-%m-%d")
    df["age_days"] = df["age_days"].astype(int)
    df = refresh_derived_columns(df)

    df = df.sort_values(["paper_id", "updated"], ascending=[True, False])
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df[CLEAN_COLUMNS]


def refresh_derived_columns(df: pd.DataFrame, run_date: datetime | None = None) -> pd.DataFrame:
    """Rebuild helper columns after title/summary/authors/categories/published changed."""
    refreshed = df.copy()

    if run_date is not None:
        published = parse_dates(refreshed["published"])
        run_day = as_utc_timestamp(run_date).normalize()
        refreshed["published"] = published.dt.strftime("%Y-%m-%d")
        refreshed["age_days"] = (run_day - published).dt.days.fillna(0).astype(int)

    refreshed["title"] = refreshed["title"].fillna("").map(strip_markup)
    refreshed["summary"] = refreshed["summary"].fillna("").map(strip_markup)
    refreshed["authors"] = refreshed["authors"].map(clean_list)
    refreshed["categories"] = refreshed["categories"].map(clean_list)
    refreshed["authors_joined"] = refreshed["authors"].apply(lambda values: compact_join(values) or "Unknown")
    refreshed["categories_joined"] = refreshed["categories"].apply(lambda values: compact_join(values) or "Unknown")
    refreshed["summary_chars"] = refreshed["summary"].str.len().astype(int)
    refreshed["text_for_embedding"] = refreshed.apply(compose_text_for_embedding, axis=1)
    return refreshed


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


def clean_list(value: Any) -> list[str]:
    if value is None or isinstance(value, float):
        return []
    if isinstance(value, str):
        value = [value]

    cleaned: list[str] = []
    for item in value:
        text = normalize_whitespace(str(item or ""))
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def parse_dates(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce", utc=True).dt.normalize()


def as_utc_timestamp(value: datetime) -> pd.Timestamp:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return pd.Timestamp(value).tz_convert(UTC)


def save_dataframe(df: pd.DataFrame, csv_path, json_path) -> None:
    ensure_parent(csv_path)
    ensure_parent(json_path)
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)


def load_dataframe(json_path) -> pd.DataFrame:
    return pd.read_json(json_path, orient="records", dtype=False, convert_dates=False)
