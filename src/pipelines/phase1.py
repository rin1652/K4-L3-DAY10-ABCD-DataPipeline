from __future__ import annotations

import logging

from core.config import load_settings, normalized_provider, require_llm_credentials
from core.utils import now_utc, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_build_test_set
from ingestion.cleaning import build_clean_dataframe, save_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)
DEMO_QUESTIONS = 2


def _run_agent_demo(settings, index, test_set) -> list[dict[str, str]]:
    """Optional: ask the tool-using agent a couple of benchmark questions (needs real LLM credentials)."""
    try:
        require_llm_credentials(settings)
        if normalized_provider(settings) == "mock":
            return []
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings, index)
        return [
            {"question": item["question"], "answer": str(run_agent_question(agent, item["question"]))}
            for item in test_set[:DEMO_QUESTIONS]
        ]
    except Exception as exc:  # the demo must never break the baseline pipeline
        logger.warning("Agent demo skipped: %s", exc)
        return [{"skipped": str(exc)}]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    # 1-2. Ingest (live API when REFRESH_SOURCE=1, otherwise offline snapshot) + raw lineage.
    records = fetch_source_records(settings)
    print(f"[1/7] Ingested {len(records)} raw records -> {paths.raw_records_json.name}")

    # 3-4. Clean and persist.
    df = build_clean_dataframe(records, run_date)
    save_dataframe(df, paths.clean_csv, paths.clean_json)
    print(f"[2/7] Clean dataset: {len(df)} rows -> {paths.clean_csv.name}")

    # Quality gate BEFORE indexing: bad data must never reach the vector store.
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(f"[3/7] Quality gate success={quality['success']} | fresh={freshness['is_fresh']} "
          f"({freshness['stale_rows']}/{freshness['total_rows']} stale)")
    if not quality["success"]:
        raise RuntimeError(
            f"Quality gate failed ({', '.join(quality['failed_critical'])}); refusing to index. "
            f"See {paths.baseline_quality_report}."
        )

    # 5. Embed + Chroma index.
    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)
    print(f"[4/7] Indexed {len(index.documents)} documents into Chroma collection '{index.collection_name}'")

    # 6. Frozen benchmark.
    test_set = load_or_build_test_set(df, paths.eval_testset, refresh=settings.refresh_test_set)
    print(f"[5/7] Test set: {len(test_set)} questions -> {paths.eval_testset.name}")

    # 7. Evaluate.
    bundle = evaluate_pipeline(settings, index, paths.eval_testset, paths.baseline_metrics, paths.baseline_answers)
    summary = bundle.summary
    print(f"[6/7] Baseline hit_rate={summary['retrieval_hit_rate']:.3f} token_f1={summary['mean_token_f1']:.3f} "
          f"judge_acc={summary['judge_accuracy']:.3f}")

    # 10. Optional agent demo.
    demo = _run_agent_demo(settings, index, test_set)
    if demo:
        write_json(paths.demo_answers, demo)

    # 9. Report.
    source_summary = {
        "source_api": settings.source_api,
        "mode": "live API" if settings.refresh_source else "offline snapshot (data/raw/crossref_response.json)",
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_records": len(records),
        "clean_rows": len(df),
        "run_date_utc": run_date.strftime("%Y-%m-%d %H:%M"),
        "embedding_model": settings.embedding_model,
        "chroma_collection": index.collection_name,
        "llm": f"{settings.llm_provider}/{settings.model_name}",
    }
    generate_phase1_report(paths.baseline_report, source_summary, summary, quality, freshness, bundle.answers)
    print(f"[7/7] Report -> {paths.baseline_report}")
