from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from html import unescape
import logging
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)

CROSSREF_WORKS_URL = "https://api.crossref.org/works"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
REQUEST_TIMEOUT_SECONDS = 20
DOI_PREFIX_RE = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into normalized paper records."""
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []

    for item in items:
        paper_id = normalize_doi(item.get("DOI"))
        title = normalize_whitespace(first_text(item.get("title")))
        summary = strip_markup(item.get("abstract") or item.get("summary"))
        published = first_crossref_date(item, ("published", "published-print", "published-online", "issued", "created"))

        if not paper_id or not title or not published:
            continue

        categories = clean_list(item.get("subject") or [])
        abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=parse_authors(item.get("author") or []),
                categories=categories,
                primary_category=categories[0] if categories else "Unknown",
                published=published,
                updated=first_crossref_date(item, ("deposited", "indexed", "created")) or published,
                abs_url=abs_url,
                pdf_url=extract_pdf_url(item) or abs_url,
                comment=normalize_whitespace(str(item.get("publisher") or "")),
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records with offline fallback to data/raw/crossref_response.json."""
    payload: dict[str, Any] | None = None

    if settings.refresh_source:
        try:
            payload = request_crossref_payload(settings)
            write_json(settings.paths.raw_api_response, payload)
        except Exception as exc:
            logger.warning("Crossref API unavailable (%s). Falling back to local snapshot.", exc)

    if payload is None:
        payload = read_json(settings.paths.raw_api_response)

    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref payload produced zero valid records.")

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized raw records, or parse a saved Crossref response snapshot."""
    payload = read_json(Path(path))
    if isinstance(payload, dict) and "message" in payload:
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError(f"Unsupported raw records format in {path}.")

    field_names = {field.name for field in fields(PaperRecord)}
    records: list[PaperRecord] = []
    for row in payload:
        values = {key: row.get(key) for key in field_names}
        values["paper_id"] = normalize_doi(values.get("paper_id"))
        values["title"] = normalize_whitespace(str(values.get("title") or ""))
        values["summary"] = strip_markup(values.get("summary"))
        values["authors"] = clean_list(values.get("authors") or [])
        values["categories"] = clean_list(values.get("categories") or [])
        values["primary_category"] = normalize_whitespace(str(values.get("primary_category") or "")) or "Unknown"
        values["published"] = normalize_iso_date(values.get("published"))
        values["updated"] = normalize_iso_date(values.get("updated")) or values["published"]
        values["abs_url"] = str(values.get("abs_url") or "")
        values["pdf_url"] = str(values.get("pdf_url") or values["abs_url"])
        values["comment"] = normalize_whitespace(str(values.get("comment") or ""))
        records.append(PaperRecord(**values))
    return records


def request_crossref_payload(settings: Settings) -> dict[str, Any]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "published",
        "order": "desc",
    }
    headers = {"User-Agent": "day10-data-pipeline-lab/1.0 (educational use)"}
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_WORKS_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(f"Crossref returned HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(attempt)

    raise RuntimeError(f"Crossref API unavailable after {MAX_ATTEMPTS} attempts: {last_error}")


def normalize_doi(value: Any) -> str:
    doi = normalize_whitespace(str(value or ""))
    return DOI_PREFIX_RE.sub("", doi).lower()


def strip_markup(value: Any) -> str:
    text = unescape(str(value or ""))
    text = TAG_RE.sub(" ", text)
    return normalize_whitespace(text)


def first_text(value: Any) -> str:
    if isinstance(value, list):
        return str(next((item for item in value if item), ""))
    return str(value or "")


def parse_authors(raw_authors: list[dict[str, Any]]) -> list[str]:
    authors: list[str] = []
    for author in raw_authors:
        name = author.get("name") or " ".join(
            part for part in (author.get("given"), author.get("family")) if part
        )
        cleaned = normalize_whitespace(str(name or ""))
        if cleaned and cleaned not in authors:
            authors.append(cleaned)
    return authors


def first_crossref_date(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        date_value = crossref_date_to_iso(item.get(key))
        if date_value:
            return date_value
    return ""


def crossref_date_to_iso(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    if value.get("date-time"):
        return normalize_iso_date(value["date-time"])

    parts = (value.get("date-parts") or [[]])[0] or []
    if not parts:
        return ""

    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        day = int(parts[2]) if len(parts) > 2 and parts[2] else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (TypeError, ValueError):
        return ""


def normalize_iso_date(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return text[:10]


def clean_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return [cleaned for item in value if (cleaned := normalize_whitespace(str(item)))]


def extract_pdf_url(item: dict[str, Any]) -> str:
    for link in item.get("link") or []:
        content_type = str(link.get("content-type", "")).lower()
        if "pdf" in content_type and link.get("URL"):
            return str(link["URL"])
    return ""
