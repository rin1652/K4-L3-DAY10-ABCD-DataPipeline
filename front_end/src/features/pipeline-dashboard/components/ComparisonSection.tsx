import BarChartRoundedIcon from "@mui/icons-material/BarChartRounded";
import { Alert, Box, Card, CardContent, GridLegacy as Grid, Stack, Typography } from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { AnyMetrics, ArtifactState } from "../data/schemas";

type ComparisonSectionProps = {
  baseline: ArtifactState<AnyMetrics>;
  corrupted: ArtifactState<AnyMetrics>;
  repaired: ArtifactState<AnyMetrics>;
};

type SeriesRow = {
  label: string;
  baseline: number;
  corrupted: number;
  repaired: number;
  suffix?: string;
};

export function ComparisonSection({ baseline, corrupted, repaired }: ComparisonSectionProps) {
  const ragRows = buildRagRows(baseline, corrupted, repaired);
  const healthRows = buildHealthRows(baseline, corrupted, repaired);
  const rows = ragRows.length > 0 ? ragRows : healthRows;
  const title = ragRows.length > 0 ? "So sánh RAG: dữ liệu sạch vs dữ liệu bẩn vs repair" : "So sánh chất lượng dữ liệu";

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
          <BarChartRoundedIcon color="primary" />
          <Typography variant="h5">{title}</Typography>
        </Stack>

        {ragRows.length === 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Chưa có metrics RAG, nên phần này dùng metrics cấu trúc dữ liệu do corruption flow tạo ra.
          </Alert>
        ) : null}

        <Box sx={{ width: "100%", height: 360 }}>
          <BarChart
            dataset={rows}
            xAxis={[{ scaleType: "band", dataKey: "label" }]}
            series={[
              { dataKey: "baseline", label: "Sạch", color: "#22c55e" },
              { dataKey: "corrupted", label: "Bẩn", color: "#ef4444" },
              { dataKey: "repaired", label: "Repair", color: "#60a5fa" }
            ]}
            margin={{ top: 28, right: 24, bottom: 72, left: 64 }}
            grid={{ horizontal: true }}
          />
        </Box>

        <Grid container spacing={1.5} sx={{ mt: 1 }}>
          {rows.map((row) => (
            <Grid item xs={12} md={6} lg={4} key={row.label}>
              <Box sx={{ border: "1px solid rgba(148, 163, 184, 0.22)", borderRadius: 2, p: 1.5 }}>
                <Typography color="text.secondary">{row.label}</Typography>
                <Stack direction="row" spacing={2.5} sx={{ mt: 1 }}>
                  <Metric label="Sạch" value={formatValue(row.baseline, row.suffix)} color="#22c55e" />
                  <Metric label="Bẩn" value={formatValue(row.corrupted, row.suffix)} color="#ef4444" />
                  <Metric label="Đã sửa" value={formatValue(row.repaired, row.suffix)} color="#60a5fa" />
                </Stack>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <Box>
      <Typography variant="h5" sx={{ color }}>
        {value}
      </Typography>
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}

function buildRagRows(
  baseline: ArtifactState<AnyMetrics>,
  corrupted: ArtifactState<AnyMetrics>,
  repaired: ArtifactState<AnyMetrics>
): SeriesRow[] {
  const metrics = [
    ["retrieval_hit_rate", "Tỷ lệ tìm đúng tài liệu"],
    ["mean_token_f1", "Token F1"],
    ["judge_accuracy", "Judge Accuracy"],
    ["mean_judge_score", "Judge Score"]
  ] as const;

  if (baseline.status !== "ready" || corrupted.status !== "ready" || repaired.status !== "ready") {
    return [];
  }

  return metrics.flatMap(([key, label]) => {
    const clean = getRagMetric(baseline.data, key);
    const bad = getRagMetric(corrupted.data, key);
    const fixed = getRagMetric(repaired.data, key);
    if (typeof clean !== "number" || typeof bad !== "number" || typeof fixed !== "number") {
      return [];
    }
    return [{ label, baseline: clean, corrupted: bad, repaired: fixed, suffix: key === "mean_judge_score" ? "" : "%" }];
  });
}

function getRagMetric(metrics: AnyMetrics, key: "retrieval_hit_rate" | "mean_token_f1" | "judge_accuracy" | "mean_judge_score") {
  const nested = metrics.rag?.[key];
  if (typeof nested === "number") {
    return nested;
  }
  return metrics[key];
}

function buildHealthRows(
  baseline: ArtifactState<AnyMetrics>,
  corrupted: ArtifactState<AnyMetrics>,
  repaired: ArtifactState<AnyMetrics>
): SeriesRow[] {
  const baselineRows = baseline.status === "ready" && typeof baseline.data.rows === "number" ? baseline.data.rows : 24;
  const baselineUnique =
    baseline.status === "ready" && typeof baseline.data.unique_paper_ids === "number" ? baseline.data.unique_paper_ids : 24;
  const baselineStale =
    baseline.status === "ready" && typeof baseline.data.stale_rows === "number" ? baseline.data.stale_rows : 1;
  const corruptedData = corrupted.status === "ready" ? corrupted.data : {};
  const repairedData = repaired.status === "ready" ? repaired.data : {};

  return [
    {
      label: "Số paper_id duy nhất",
      baseline: baselineUnique,
      corrupted: numberOrZero(corruptedData.unique_paper_ids),
      repaired: numberOrZero(repairedData.unique_paper_ids)
    },
    {
      label: "Dòng bị trùng",
      baseline: numberOrZero(baseline.status === "ready" ? baseline.data.duplicate_rows : 0),
      corrupted: numberOrZero(corruptedData.duplicate_rows),
      repaired: numberOrZero(repairedData.duplicate_rows)
    },
    {
      label: "Summary rỗng",
      baseline: numberOrZero(baseline.status === "ready" ? baseline.data.blank_summary_rows : 0),
      corrupted: numberOrZero(corruptedData.blank_summary_rows),
      repaired: numberOrZero(repairedData.blank_summary_rows)
    },
    {
      label: "Title bị cắt",
      baseline: numberOrZero(baseline.status === "ready" ? baseline.data.truncated_title_rows : 0),
      corrupted: numberOrZero(corruptedData.truncated_title_rows),
      repaired: numberOrZero(repairedData.truncated_title_rows)
    },
    {
      label: "Dòng quá cũ",
      baseline: baselineStale,
      corrupted: numberOrZero(corruptedData.stale_rows),
      repaired: numberOrZero(repairedData.stale_rows)
    },
    {
      label: "Tổng số dòng",
      baseline: baselineRows,
      corrupted: numberOrZero(corruptedData.rows),
      repaired: numberOrZero(repairedData.rows)
    }
  ];
}

function numberOrZero(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

function formatValue(value: number, suffix?: string): string {
  if (suffix === "%") {
    return `${Math.round(value * 100)}%`;
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
