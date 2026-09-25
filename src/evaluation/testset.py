from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TestSet:
    samples: list[dict[str, Any]]

    def __len__(self) -> int:
        return len(self.samples)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create five deterministic benchmark questions from cleaned papers."""
    required = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Missing columns for benchmark generation: {missing}")
    if len(df) < 2:
        raise ValueError("At least two papers are required to create the benchmark")

    rows = df.drop_duplicates("paper_id").reset_index(drop=True)
    first, second = rows.iloc[0], rows.iloc[1]

    def sample(sample_id: str, kind: str, question: str, truth: str, paper_ids: list[str]) -> dict[str, Any]:
        return {
            "id": sample_id,
            "type": kind,
            "question_type": kind,
            "question": question,
            "ground_truth": truth,
            "ground_truth_doc_ids": paper_ids,
        }

    samples = [
        sample("q1", "summary", f"Tóm tắt nội dung chính của nghiên cứu '{first['title']}'.", str(first["summary"]), [str(first["paper_id"])]),
        sample("q2", "authors", f"Ai là tác giả của nghiên cứu '{first['title']}'?", str(first["authors_joined"]), [str(first["paper_id"])]),
        sample("q3", "date", f"Nghiên cứu '{second['title']}' được công bố vào thời điểm nào?", str(second["published"]), [str(second["paper_id"])]),
        sample("q4", "category", f"Nghiên cứu '{second['title']}' thuộc lĩnh vực chuyên môn nào?", str(second["categories_joined"]), [str(second["paper_id"])]),
        sample(
            "q5",
            "multi_hop",
            f"So sánh mối liên hệ giữa nghiên cứu '{first['title']}' và '{second['title']}'.",
            f"Nghiên cứu thứ nhất thuộc {first['categories_joined']} và tập trung vào: {first['summary']} "
            f"Nghiên cứu thứ hai thuộc {second['categories_joined']} và tập trung vào: {second['summary']}",
            [str(first["paper_id"]), str(second["paper_id"])],
        ),
    ]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(samples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    path = Path(output_path)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TestSet(samples=payload)
    return TestSet(samples=build_test_set(df, path))
