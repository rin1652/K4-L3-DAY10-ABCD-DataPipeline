from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, write_json

MIN_DOCUMENTS = 4
QUESTION_PLAN = (
    ("summary", 3),
    ("authors", 3),
    ("date", 2),
    ("categories", 2),
)


def _as_text_list(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(item).strip() for item in list(value) if str(item).strip()]


def _joined(row: pd.Series, joined_column: str, raw_column: str) -> str:
    joined = row.get(joined_column)
    if isinstance(joined, str) and joined.strip():
        return joined.strip()
    return compact_join(_as_text_list(row.get(raw_column)))


def _question(question_type: str, row: pd.Series) -> tuple[str, str]:
    title = str(row["title"]).strip()
    if question_type == "summary":
        return (
            f"What is the summary of the paper '{title}'?",
            first_sentence(str(row["summary"])),
        )
    if question_type == "authors":
        return (
            f"Who are the authors of the paper '{title}'?",
            _joined(row, "authors_joined", "authors"),
        )
    if question_type == "date":
        return (
            f"When was the paper '{title}' published?",
            str(row["published"]).strip(),
        )
    return (
        f"What categories does the paper '{title}' belong to?",
        _joined(row, "categories_joined", "categories") or str(row.get("primary_category", "")).strip(),
    )


@dataclass(frozen=True)
class TestSet:
    samples: list[dict[str, Any]]

    def __len__(self) -> int:
        return len(self.samples)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a 10-question evaluation set covering summary, authors, date, and categories."""
    required = {"paper_id", "title", "summary", "authors", "categories", "published"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing required columns for the test set: {missing}")
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} documents to build the test set, got {len(df)}")

    usable = df.dropna(subset=["paper_id", "title", "summary", "published"]).reset_index(drop=True)
    if len(usable) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} complete documents, got {len(usable)}")

    test_set: list[dict[str, Any]] = []
    cursor = 0
    for question_type, count in QUESTION_PLAN:
        for _ in range(count):
            row = usable.iloc[cursor % len(usable)]
            cursor += 1
            question, ground_truth = _question(question_type, row)
            if not ground_truth:
                raise ValueError(f"Empty ground truth for {question_type} on paper {row['paper_id']}")
            test_set.append(
                {
                    "id": f"eval_{len(test_set) + 1:03d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [str(row["paper_id"])],
                }
            )

    write_json(Path(output_path), test_set)
    return test_set


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    path = Path(output_path)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TestSet(samples=payload)
    return TestSet(samples=build_test_set(df, path))


def load_or_build_test_set(df: pd.DataFrame, output_path, refresh: bool = False) -> list[dict[str, Any]]:
    path = Path(output_path)
    if refresh or not path.exists():
        return build_test_set(df, path)
    return json.loads(path.read_text(encoding="utf-8"))
