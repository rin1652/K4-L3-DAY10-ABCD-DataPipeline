from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import html
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
REQUEST_TIMEOUT_SECONDS = 30
_TAG_RE = re.compile(r"<[^>]+>")
_DOI_PREFIX_RE = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)


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


def strip_markup(value: str | None) -> str:
    """Remove JATS/HTML tags + entities and collapse whitespace."""
    if not value:
        return ""
    return normalize_whitespace(html.unescape(_TAG_RE.sub(" ", str(value))))


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    return _DOI_PREFIX_RE.sub("", str(value).strip()).lower()


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        value = next((item for item in value if item), "")
    return strip_markup(value)


def _date_parts_to_iso(block: dict[str, Any] | None) -> str:
    """Crossref date: {"date-parts": [[YYYY, MM, DD]]} or {"date-time": "..."}; missing month/day -> 01."""
    if not block:
        return ""
    parts = (block.get("date-parts") or [[]])[0] or []
    if parts and parts[0]:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        day = int(parts[2]) if len(parts) > 2 and parts[2] else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    date_time = block.get("date-time")
    return str(date_time)[:10] if date_time else ""


def _first_date(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _date_parts_to_iso(item.get(key))
        if value:
            return value
    return ""


def _parse_authors(raw_authors: list[dict[str, Any]] | None) -> list[str]:
    authors: list[str] = []
    for author in raw_authors or []:
        name = author.get("name") or " ".join(part for part in (author.get("given"), author.get("family")) if part)
        name = normalize_whitespace(name or "")
        if name and name not in authors:
            authors.append(name)
    return authors


def _pdf_url(item: dict[str, Any], fallback: str) -> str:
    for link in item.get("link") or []:
        if "pdf" in str(link.get("content-type", "")).lower() and link.get("URL"):
            return str(link["URL"])
    return fallback


def parse_crossref_item(item: dict[str, Any]) -> PaperRecord | None:
    paper_id = normalize_doi(item.get("DOI"))
    title = _first_text(item.get("title"))
    summary = strip_markup(item.get("abstract"))
    published = _first_date(item, ("published", "published-print", "published-online", "issued", "created"))
    if not paper_id or not title or not summary or not published:
        return None

    categories = [normalize_whitespace(subject) for subject in item.get("subject") or [] if subject and subject.strip()]
    updated = _first_date(item, ("updated", "deposited", "indexed", "created")) or published
    abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")
    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=summary,
        authors=_parse_authors(item.get("author")),
        categories=categories,
        primary_category=categories[0] if categories else "Uncategorized",
        published=published,
        updated=max(updated, published),
        abs_url=abs_url,
        pdf_url=_pdf_url(item, abs_url),
        comment=f"Crossref record {paper_id}",
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = (payload.get("message") or {}).get("items") or []
    records: list[PaperRecord] = []
    skipped = 0
    for item in items:
        record = parse_crossref_item(item)
        if record is None:
            skipped += 1
            continue
        records.append(record)
    if skipped:
        logger.warning("Skipped %d Crossref items missing DOI/title/abstract/date.", skipped)
    return records


def _request_crossref(settings: Settings) -> dict[str, Any]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "sort": "published",
        "order": "desc",
    }
    headers = {"User-Agent": "day10-data-observability-lab/0.1 (educational use)"}
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(CROSSREF_WORKS_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
            if response.status_code in RETRYABLE_STATUS_CODES:
                raise requests.HTTPError(f"Crossref returned {response.status_code}", response=response)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
            delay = float(retry_after) if retry_after and str(retry_after).isdigit() else 2 ** attempt
            logger.warning("Crossref attempt %d/%d failed (%s); retrying in %.0fs.", attempt, MAX_ATTEMPTS, exc, delay)
            time.sleep(delay)
    raise RuntimeError(f"Crossref API unavailable after {MAX_ATTEMPTS} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Dual-mode ingestion.

    - REFRESH_SOURCE=1: call the live Crossref API (retry on 429/5xx) and preserve the raw response.
    - Otherwise, or when the API fails: replay the offline snapshot in `data/raw/crossref_response.json`.
    Either way the parsed records are written to `data/raw/crossref_records.json` (lineage).
    """
    paths = settings.paths
    payload: dict[str, Any] | None = None
    if settings.refresh_source:
        try:
            payload = _request_crossref(settings)
            write_json(paths.raw_api_response, payload)
            logger.info("Fetched live Crossref payload -> %s", paths.raw_api_response)
        except RuntimeError as exc:
            logger.warning("%s Falling back to offline snapshot.", exc)

    if payload is None:
        if not paths.raw_api_response.exists():
            raise FileNotFoundError(
                f"No offline snapshot at {paths.raw_api_response}; set REFRESH_SOURCE=1 with network access."
            )
        payload = read_json(paths.raw_api_response)

    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref payload produced zero valid records.")
    write_json(paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    payload = read_json(Path(path))
    if isinstance(payload, dict) and "message" in payload:
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError(f"Unsupported raw records format in {path}.")
    field_names = {field.name for field in fields(PaperRecord)}
    return [PaperRecord(**{key: row.get(key) for key in field_names}) for row in payload]
