import ContentCutRoundedIcon from "@mui/icons-material/ContentCutRounded";
import ContentPasteOffRoundedIcon from "@mui/icons-material/ContentPasteOffRounded";
import EventBusyRoundedIcon from "@mui/icons-material/EventBusyRounded";
import FileCopyRoundedIcon from "@mui/icons-material/FileCopyRounded";
import NewReleasesRoundedIcon from "@mui/icons-material/NewReleasesRounded";
import NoiseControlOffRoundedIcon from "@mui/icons-material/NoiseControlOffRounded";
import { Box, Card, CardContent, GridLegacy as Grid, Stack, Typography } from "@mui/material";
import { ArtifactState, CorruptionLog } from "../data/schemas";

type CorruptionLogPanelProps = {
  log: ArtifactState<CorruptionLog>;
};

const scenarioIcon: Record<string, JSX.Element> = {
  drop_latest_records: <NewReleasesRoundedIcon />,
  blank_summary: <ContentPasteOffRoundedIcon />,
  inject_text_noise: <NoiseControlOffRoundedIcon />,
  truncate_title: <ContentCutRoundedIcon />,
  stale_date: <EventBusyRoundedIcon />,
  duplicate_rows: <FileCopyRoundedIcon />
};

const scenarioLabel: Record<string, string> = {
  drop_latest_records: "Mất bài mới nhất",
  blank_summary: "Tóm tắt bị rỗng",
  inject_text_noise: "Chèn ký tự rác",
  truncate_title: "Tiêu đề bị cắt",
  stale_date: "Ngày bị lùi cũ",
  duplicate_rows: "Dữ liệu bị trùng"
};

export function CorruptionLogPanel({ log }: CorruptionLogPanelProps) {
  if (log.status !== "ready") {
    return (
      <Card>
        <CardContent>
          <Typography variant="h5">Nhật ký tiêm lỗi dữ liệu</Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            {log.message}
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 2 }}>
          <Typography variant="h5">6 lỗi dữ liệu được cố tình tiêm vào</Typography>
          <Typography color="text.secondary">{log.data.output_rows} dòng dữ liệu bẩn</Typography>
        </Stack>
        <Grid container spacing={2}>
          {log.data.scenarios.map((scenario) => (
            <Grid item xs={12} sm={6} lg={4} key={scenario.scenario}>
              <Box
                sx={{
                  border: "1px solid",
                  borderColor: "rgba(248, 113, 113, 0.32)",
                  borderRadius: 2,
                  p: 2,
                  minHeight: 152,
                  bgcolor: "rgba(127, 29, 29, 0.18)"
                }}
              >
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Box sx={{ color: "error.main" }}>{scenarioIcon[scenario.scenario] ?? <NewReleasesRoundedIcon />}</Box>
                  <Typography variant="h6">{scenarioLabel[scenario.scenario] ?? scenario.scenario}</Typography>
                </Stack>
                <Typography variant="h4" sx={{ mt: 1 }}>
                  {scenario.affected_rows}
                </Typography>
                <Typography color="text.secondary">bản ghi bị ảnh hưởng</Typography>
                <Typography sx={{ mt: 1.5 }} color="text.secondary">
                  {scenario.description}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}
