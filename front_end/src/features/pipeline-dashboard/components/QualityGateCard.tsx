import { GridLegacy as Grid, Stack, Typography } from "@mui/material";
import { ArtifactState, FreshnessReport, QualityReport } from "../data/schemas";
import { StatusCard } from "./StatusCard";

type QualityGateCardProps = {
  quality: ArtifactState<QualityReport>;
  freshness: ArtifactState<FreshnessReport>;
};

export function QualityGateCard({ quality, freshness }: QualityGateCardProps) {
  const gxStatus = quality.status === "ready" ? (quality.data.success ? "pass" : "fail") : "unknown";
  const freshnessStatus = freshness.status === "ready" ? (freshness.data.is_fresh ? "pass" : "fail") : "unknown";

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <StatusCard
          title="Chốt chặn Great Expectations"
          status={gxStatus}
          subtitle={quality.status === "ready" ? `Báo cáo: ${quality.data.report_name}` : quality.message}
        >
          {quality.status === "ready" ? (
            <Typography variant="h4" sx={{ mt: 2 }}>
              {quality.data.success ? "Được phép index" : "Bị chặn"}
            </Typography>
          ) : null}
        </StatusCard>
      </Grid>
      <Grid item xs={12} md={6}>
        <StatusCard
          title="Độ tươi dữ liệu"
          status={freshnessStatus}
          subtitle={freshness.status === "ready" ? `Ngưỡng: ${freshness.data.threshold_days} ngày` : freshness.message}
        >
          {freshness.status === "ready" ? (
            <Stack direction="row" spacing={4} sx={{ mt: 2 }}>
              <div>
                <Typography variant="h4">{Math.round(freshness.data.stale_ratio * 100)}%</Typography>
                <Typography color="text.secondary">tỷ lệ dữ liệu cũ</Typography>
              </div>
              <div>
                <Typography variant="h4">
                  {freshness.data.stale_rows}/{freshness.data.total_rows}
                </Typography>
                <Typography color="text.secondary">dòng dữ liệu cũ</Typography>
              </div>
            </Stack>
          ) : null}
        </StatusCard>
      </Grid>
    </Grid>
  );
}
