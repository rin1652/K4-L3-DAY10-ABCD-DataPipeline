import { z } from "zod";
import {
  AnyMetricsSchema,
  AnswerRecordSchema,
  ArtifactState,
  CorruptionLogSchema,
  FreshnessReportSchema,
  PipelineArtifacts,
  QualityReportSchema
} from "./schemas";

const JSON_HEADERS = { Accept: "application/json" };

async function fetchJson<T>(path: string, schema: z.ZodType<T>): Promise<ArtifactState<T>> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`, { headers: JSON_HEADERS });
    if (response.status === 404) {
      return { status: "missing", message: `${path} not run yet` };
    }
    if (!response.ok) {
      return { status: "invalid", message: `${path} returned HTTP ${response.status}` };
    }
    const payload = await response.json();
    return { status: "ready", data: schema.parse(payload) };
  } catch (error) {
    return {
      status: "invalid",
      message: error instanceof Error ? error.message : `Could not load ${path}`
    };
  }
}

async function fetchText(path: string): Promise<ArtifactState<string>> {
  try {
    const response = await fetch(`${path}?t=${Date.now()}`);
    if (response.status === 404) {
      return { status: "missing", message: `${path} not run yet` };
    }
    if (!response.ok) {
      return { status: "invalid", message: `${path} returned HTTP ${response.status}` };
    }
    return { status: "ready", data: await response.text() };
  } catch (error) {
    return {
      status: "invalid",
      message: error instanceof Error ? error.message : `Could not load ${path}`
    };
  }
}

export async function loadArtifacts(): Promise<PipelineArtifacts> {
  const [
    baselineMetrics,
    corruptedMetrics,
    repairedMetrics,
    corruptionLog,
    freshnessReport,
    qualityReport,
    baselineAnswers,
    corruptedAnswers,
    repairedAnswers,
    phase1Report,
    corruptionReport
  ] = await Promise.all([
    fetchJson("/data/results/baseline_metrics.json", AnyMetricsSchema),
    fetchJson("/data/results/corrupted_metrics.json", AnyMetricsSchema),
    fetchJson("/data/results/repaired_metrics.json", AnyMetricsSchema),
    fetchJson("/data/results/corruption_log.json", CorruptionLogSchema),
    fetchJson("/data/quality/freshness_report.json", FreshnessReportSchema),
    fetchJson("/data/quality/test_quality_report.json", QualityReportSchema),
    fetchJson("/data/results/baseline_answers.json", AnswerRecordSchema.array()),
    fetchJson("/data/results/corrupted_answers.json", AnswerRecordSchema.array()),
    fetchJson("/data/results/repaired_answers.json", AnswerRecordSchema.array()),
    fetchText("/data/reports/phase1_report.md"),
    fetchText("/data/reports/corruption_report.md")
  ]);

  return {
    baselineMetrics,
    corruptedMetrics,
    repairedMetrics,
    corruptionLog,
    freshnessReport,
    qualityReport,
    baselineAnswers,
    corruptedAnswers,
    repairedAnswers,
    phase1Report,
    corruptionReport
  };
}
