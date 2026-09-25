import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import { Box, Button, Card, CardContent, Chip, Container, Stack, Typography } from "@mui/material";
import { ChatPlayground } from "./components/ChatPlayground";
import { ComparisonSection } from "./components/ComparisonSection";
import { CorruptionLogPanel } from "./components/CorruptionLogPanel";
import { QualityGateCard } from "./components/QualityGateCard";
import { RagTrainingPlayground } from "./components/RagTrainingPlayground";
import { ReportViewer } from "./components/ReportViewer";
import { usePipelineData } from "./hooks/usePipelineData";

export function PipelineDashboard() {
  const { artifacts, loading, lastReloadAt, reload } = usePipelineData();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", py: 4 }}>
      <Container maxWidth="xl">
        <Stack spacing={3}>
          <Card sx={{ bgcolor: "rgba(17, 24, 39, 0.86)" }}>
            <CardContent>
              <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                <Box>
                  <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                    <Chip color="primary" label="DAY 10" />
                    <Chip color="success" label="Pipeline RAG + Data Quality" />
                  </Stack>
                  <Typography variant="h3">Dashboard kể chuyện pipeline dữ liệu RAG</Typography>
                  <Typography variant="h6" color="text.secondary" sx={{ mt: 1 }}>
                    Chọn dữ liệu sạch hoặc bẩn, bấm train, hỏi RAG và nhìn chỉ số thay đổi.
                  </Typography>
                </Box>
                <Stack alignItems={{ xs: "flex-start", md: "flex-end" }} justifyContent="space-between" spacing={1.5}>
                  <Button
                    variant="contained"
                    startIcon={<RefreshRoundedIcon />}
                    onClick={() => void reload()}
                    disabled={loading}
                    size="large"
                  >
                    {loading ? "Đang tải lại..." : "Tải lại dữ liệu"}
                  </Button>
                  <Typography color="text.secondary">
                    Lần tải gần nhất: {lastReloadAt ? lastReloadAt.toLocaleTimeString() : "đang chờ"}
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          <StoryFlow />

          {artifacts ? (
            <>
              <ChatPlayground />
              <RagTrainingPlayground
                baselineMetrics={artifacts.baselineMetrics}
                corruptedMetrics={artifacts.corruptedMetrics}
                baselineAnswers={artifacts.baselineAnswers}
                corruptedAnswers={artifacts.corruptedAnswers}
                corruptionLog={artifacts.corruptionLog}
              />
              <QualityGateCard quality={artifacts.qualityReport} freshness={artifacts.freshnessReport} />
              <ComparisonSection
                baseline={artifacts.baselineMetrics}
                corrupted={artifacts.corruptedMetrics}
                repaired={artifacts.repairedMetrics}
              />
              <CorruptionLogPanel log={artifacts.corruptionLog} />
              <ReportViewer phase1Report={artifacts.phase1Report} corruptionReport={artifacts.corruptionReport} />
            </>
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h5">Đang tải artifacts của pipeline...</Typography>
              </CardContent>
            </Card>
          )}
        </Stack>
      </Container>
    </Box>
  );
}

function StoryFlow() {
  const steps = [
    "1. Làm sạch dữ liệu",
    "2. Great Expectations kiểm tra",
    "3. MiniLM biến text thành vector",
    "4. ChromaDB lưu vector",
    "5. RAG tìm tài liệu và trả lời"
  ];

  return (
    <Card>
      <CardContent>
        <Typography variant="h5">
          Câu chuyện trong 1 dòng
        </Typography>
        <Stack direction={{ xs: "column", lg: "row" }} spacing={1.2} sx={{ mt: 2 }}>
          {steps.map((step, index) => (
            <Box
              key={step}
              sx={{
                flex: 1,
                border: "1px solid rgba(148, 163, 184, 0.22)",
                borderRadius: 2,
                p: 1.5,
                bgcolor: index === 1 ? "rgba(245, 158, 11, 0.12)" : "rgba(15, 23, 42, 0.5)"
              }}
            >
              <Typography sx={{ fontWeight: 900 }}>{step}</Typography>
            </Box>
          ))}
        </Stack>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Great Expectations không làm sạch dữ liệu. Nó là chốt kiểm tra trước khi dữ liệu được đưa vào ChromaDB.
        </Typography>
      </CardContent>
    </Card>
  );
}

