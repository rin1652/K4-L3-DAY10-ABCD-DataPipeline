import { z } from "zod";

export const DataHealthMetricsSchema = z.object({
  rows: z.number(),
  unique_paper_ids: z.number(),
  duplicate_rows: z.number(),
  blank_summary_rows: z.number(),
  truncated_title_rows: z.number(),
  stale_rows: z.number(),
  stale_ratio: z.number()
});

export const RagMetricsSchema = z.object({
  samples: z.number().optional(),
  retrieval_hit_rate: z.number().optional(),
  mean_token_f1: z.number().optional(),
  judge_accuracy: z.number().optional(),
  mean_judge_score: z.number().optional(),
  llm_judge_score: z.number().optional()
});

export const AnyMetricsSchema = DataHealthMetricsSchema.partial()
  .merge(RagMetricsSchema)
  .extend({
    rag: RagMetricsSchema.optional()
  })
  .passthrough();

export const CorruptionScenarioSchema = z.object({
  scenario: z.string(),
  description: z.string(),
  affected_rows: z.number(),
  affected_paper_ids: z.array(z.string()).optional(),
  params: z.record(z.unknown()).optional()
});

export const CorruptionLogSchema = z.object({
  generated_at: z.string(),
  seed: z.number(),
  input_rows: z.number(),
  output_rows: z.number(),
  scenarios: z.array(CorruptionScenarioSchema)
});

export const FreshnessReportSchema = z.object({
  latest_published: z.string().nullable(),
  oldest_published: z.string().nullable(),
  stale_rows: z.number(),
  total_rows: z.number(),
  stale_ratio: z.number(),
  threshold_days: z.number(),
  stale_ratio_limit: z.number(),
  is_fresh: z.boolean(),
  warning: z.boolean()
});

export const QualityReportSchema = z.object({
  success: z.boolean(),
  report_name: z.string(),
  run_at: z.string(),
  great_expectations: z.unknown().optional(),
  freshness: FreshnessReportSchema.optional(),
  freshness_warning: z.boolean().optional()
});

export const AnswerRecordSchema = z.object({
  id: z.string(),
  question_type: z.string(),
  question: z.string(),
  ground_truth: z.string(),
  ground_truth_doc_ids: z.array(z.string()),
  answer: z.string(),
  retrieved_doc_ids: z.array(z.string()),
  retrieved_contexts: z.array(z.string()).optional(),
  retrieval_hit: z.boolean().optional(),
  token_f1: z.number().optional(),
  judge: z
    .object({
      score: z.number().optional(),
      correct: z.boolean().optional(),
      reasoning: z.string().optional()
    })
    .passthrough()
    .optional()
});

export type DataHealthMetrics = z.infer<typeof DataHealthMetricsSchema>;
export type AnyMetrics = z.infer<typeof AnyMetricsSchema>;
export type CorruptionLog = z.infer<typeof CorruptionLogSchema>;
export type FreshnessReport = z.infer<typeof FreshnessReportSchema>;
export type QualityReport = z.infer<typeof QualityReportSchema>;
export type AnswerRecord = z.infer<typeof AnswerRecordSchema>;

export type ArtifactState<T> =
  | { status: "ready"; data: T }
  | { status: "missing"; message: string }
  | { status: "invalid"; message: string };

export type PipelineArtifacts = {
  baselineMetrics: ArtifactState<AnyMetrics>;
  corruptedMetrics: ArtifactState<AnyMetrics>;
  repairedMetrics: ArtifactState<AnyMetrics>;
  corruptionLog: ArtifactState<CorruptionLog>;
  freshnessReport: ArtifactState<FreshnessReport>;
  qualityReport: ArtifactState<QualityReport>;
  baselineAnswers: ArtifactState<AnswerRecord[]>;
  corruptedAnswers: ArtifactState<AnswerRecord[]>;
  repairedAnswers: ArtifactState<AnswerRecord[]>;
  phase1Report: ArtifactState<string>;
  corruptionReport: ArtifactState<string>;
};
