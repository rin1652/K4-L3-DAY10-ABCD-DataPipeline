import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import QuestionAnswerRoundedIcon from "@mui/icons-material/QuestionAnswerRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  LinearProgress,
  Stack,
  Typography
} from "@mui/material";
import { useMemo, useState } from "react";
import { AnswerRecord, AnyMetrics, ArtifactState, CorruptionLog } from "../data/schemas";

type DatasetKey = "raw" | "clean" | "corrupted";

type RagTrainingPlaygroundProps = {
  baselineMetrics: ArtifactState<AnyMetrics>;
  corruptedMetrics: ArtifactState<AnyMetrics>;
  baselineAnswers: ArtifactState<AnswerRecord[]>;
  corruptedAnswers: ArtifactState<AnswerRecord[]>;
  corruptionLog: ArtifactState<CorruptionLog>;
};

const datasetGuide: Record<
  DatasetKey,
  {
    title: string;
    shortName: string;
    color: "warning" | "success" | "error";
    icon: JSX.Element;
    oneLine: string;
    whenChoose: string;
    result: string;
    metricMode: "demo" | "real";
  }
> = {
  raw: {
    title: "Trước clean",
    shortName: "Raw",
    color: "warning",
    icon: <WarningAmberRoundedIcon />,
    oneLine: "Dữ liệu thô vừa lấy về: có thể còn HTML/JATS, field thiếu, DOI/ngày/tác giả chưa chuẩn.",
    whenChoose: "Nếu cố train trước khi clean: đây là luồng sai để demo rủi ro.",
    result: "Pipeline chuẩn phải chặn ở bước này. Nếu vẫn ép vào ChromaDB, RAG dễ học nhầm từ dữ liệu chưa chuẩn.",
    metricMode: "demo"
  },
  clean: {
    title: "Nguồn sạch",
    shortName: "Baseline",
    color: "success",
    icon: <CheckCircleRoundedIcon />,
    oneLine: "Dữ liệu đã được làm sạch, không trùng khóa, summary đủ dài, ngày tháng hợp lệ.",
    whenChoose: "Nếu chọn nguồn sạch: dữ liệu qua chốt Great Expectations rồi mới vào ChromaDB.",
    result: "RAG thường tìm đúng tài liệu hơn và câu trả lời ổn định hơn.",
    metricMode: "real"
  },
  corrupted: {
    title: "Nguồn bẩn",
    shortName: "Corrupted",
    color: "error",
    icon: <ErrorRoundedIcon />,
    oneLine: "Dữ liệu cố tình bị phá: thiếu summary, nhiễu text, title cụt, ngày cũ, bản ghi trùng.",
    whenChoose: "Nếu chọn nguồn bẩn: demo cho thấy chuyện gì xảy ra khi bỏ qua hoặc phớt lờ quality gate.",
    result: "RAG dễ retrieve sai tài liệu, trả lời thiếu hoặc nói rất tự tin nhưng sai.",
    metricMode: "real"
  }
};

const rawDemoMetrics: ArtifactState<AnyMetrics> = {
  status: "ready",
  data: {
    samples: 10,
    retrieval_hit_rate: 0.4,
    mean_token_f1: 0.12,
    judge_accuracy: 0.1,
    mean_judge_score: 1
  }
};

export function RagTrainingPlayground({
  baselineMetrics,
  corruptedMetrics,
  baselineAnswers,
  corruptedAnswers,
  corruptionLog
}: RagTrainingPlaygroundProps) {
  const [selectedDataset, setSelectedDataset] = useState<DatasetKey>("clean");
  const [trainedDataset, setTrainedDataset] = useState<DatasetKey | null>(null);
  const [training, setTraining] = useState(false);
  const [questionId, setQuestionId] = useState("");

  const answersState = selectedDataset === "corrupted" ? corruptedAnswers : baselineAnswers;
  const metricsState =
    selectedDataset === "raw" ? rawDemoMetrics : selectedDataset === "clean" ? baselineMetrics : corruptedMetrics;
  const baseAnswers = answersState.status === "ready" ? answersState.data : [];
  const answers = selectedDataset === "raw" ? buildRawDemoAnswers(baseAnswers) : baseAnswers;
  const selectedAnswer = useMemo(
    () => answers.find((item) => item.id === questionId) ?? answers[0],
    [answers, questionId]
  );
  const isTrained = trainedDataset === selectedDataset && !training;
  const guide = datasetGuide[selectedDataset];

  const onSelectDataset = (dataset: DatasetKey) => {
    setSelectedDataset(dataset);
    setTrainedDataset(null);
    setTraining(false);
    setQuestionId("");
  };

  const onTrain = () => {
    setTraining(true);
    setTrainedDataset(null);
    window.setTimeout(() => {
      setTraining(false);
      setTrainedDataset(selectedDataset);
      setQuestionId(answers[0]?.id ?? "");
    }, 500);
  };

  return (
    <Card>
      <CardContent>
        <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
          <Box>
            <Chip color="primary" label="Demo thực tế" sx={{ mb: 1 }} />
            <Typography variant="h4">Chọn data → train ChromaDB → hỏi RAG</Typography>
            <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 940 }}>
              Hãy tưởng tượng RAG là một học sinh. Cho nó sách sạch thì nó trả lời dễ đúng. Cho nó sách bẩn thì nó vẫn
              trả lời, nhưng có thể trả lời sai mà nhìn vẫn rất tự tin.
            </Typography>
          </Box>
          <Chip
            color={isTrained ? guide.color : training ? "warning" : "default"}
            label={isTrained ? `Đang dùng: ${guide.shortName}` : training ? "Đang train..." : "Chưa train"}
            sx={{ alignSelf: { xs: "flex-start", md: "center" }, fontWeight: 900 }}
          />
        </Stack>

        <Divider sx={{ my: 2.5 }} />

        <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" sx={{ mb: 1.5 }}>
              1. Chọn nguồn dữ liệu
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              {(["raw", "clean", "corrupted"] as DatasetKey[]).map((dataset) => (
                <SourceButton
                  key={dataset}
                  active={selectedDataset === dataset}
                  dataset={dataset}
                  onClick={() => onSelectDataset(dataset)}
                />
              ))}
            </Stack>

            <Alert severity={guide.color} sx={{ mt: 2 }}>
              <Typography sx={{ fontWeight: 900 }}>{guide.whenChoose}</Typography>
              <Typography>{guide.result}</Typography>
            </Alert>

            <Button
              fullWidth
              variant="contained"
              color={guide.color}
              startIcon={<PlayArrowRoundedIcon />}
              size="large"
              onClick={onTrain}
              sx={{ mt: 2, py: 1.4, fontWeight: 900 }}
              disabled={answersState.status !== "ready" || training}
            >
              2. Bấm train / index vào ChromaDB
            </Button>

            {training ? (
              <Box sx={{ mt: 2 }}>
                <LinearProgress color={guide.color} />
                <Typography color="text.secondary" sx={{ mt: 1 }}>
                  MiniLM đang biến bài báo thành vector, ChromaDB đang lưu vector đó.
                </Typography>
              </Box>
            ) : null}
          </Box>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" sx={{ mb: 1.5 }}>
              Nói ngắn gọn để trình bày
            </Typography>
            <Stack spacing={1.2}>
              <ExplainLine label="Great Expectations" text="là chốt kiểm tra, không phải chổi lau dữ liệu." />
              <ExplainLine label="MiniLM" text="là model đổi văn bản thành vector số để máy so sánh ý nghĩa." />
              <ExplainLine label="ChromaDB" text="là kho lưu vector, dùng để tìm bài báo gần nghĩa với câu hỏi." />
              <ExplainLine label="RAG" text="lấy tài liệu liên quan từ ChromaDB rồi mới tạo câu trả lời." />
            </Stack>
          </Box>
        </Stack>

        {isTrained ? (
          <Box sx={{ mt: 3 }}>
            <Typography variant="h5" sx={{ mb: 1 }}>
              3. Câu hỏi ví dụ cho RAG trả lời
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Bấm một câu dưới đây để xem RAG trả lời, đáp án chuẩn và chỉ số đánh giá.
            </Typography>

            <Stack direction={{ xs: "column", md: "row" }} spacing={1.2} sx={{ flexWrap: "wrap" }}>
              {answers.map((item) => (
                <Button
                  key={item.id}
                  variant={selectedAnswer?.id === item.id ? "contained" : "outlined"}
                  color={selectedAnswer?.id === item.id ? guide.color : "inherit"}
                  onClick={() => setQuestionId(item.id)}
                  startIcon={<QuestionAnswerRoundedIcon />}
                  sx={{
                    justifyContent: "flex-start",
                    flex: "1 1 280px",
                    textAlign: "left",
                    whiteSpace: "normal",
                    py: 1.2
                  }}
                >
                  {item.question}
                </Button>
              ))}
            </Stack>

            {selectedAnswer ? (
              <Stack direction={{ xs: "column", lg: "row" }} spacing={2.5} sx={{ mt: 2.5 }}>
                <Box sx={{ flex: 1.25 }}>
                  <AnswerBox title="Câu hỏi đang demo" text={selectedAnswer.question} />
                  <AnswerBox title="RAG trả lời" text={selectedAnswer.answer} highlight />
                  <AnswerBox title="Đáp án chuẩn để so sánh" text={selectedAnswer.ground_truth} />
                  {selectedDataset === "corrupted" ? (
                    <CorruptedReason answer={selectedAnswer} corruptionLog={corruptionLog} />
                  ) : null}
                </Box>
                <Box sx={{ flex: 1 }}>
                  <MetricNotes metrics={metricsState} answer={selectedAnswer} mode={guide.metricMode} />
                </Box>
              </Stack>
            ) : null}
          </Box>
        ) : (
          <Alert severity="info" sx={{ mt: 3 }}>
            Chọn nguồn dữ liệu rồi bấm train. Sau đó web sẽ in ra các câu hỏi ví dụ để hỏi RAG.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function SourceButton({ active, dataset, onClick }: { active: boolean; dataset: DatasetKey; onClick: () => void }) {
  const guide = datasetGuide[dataset];

  return (
    <Button
      fullWidth
      variant={active ? "contained" : "outlined"}
      color={guide.color}
      onClick={onClick}
      sx={{ p: 2, justifyContent: "flex-start", textAlign: "left", borderRadius: 3 }}
    >
      <Stack spacing={0.7}>
        <Stack direction="row" spacing={1} alignItems="center">
          {guide.icon}
          <Typography variant="h6">{guide.title}</Typography>
        </Stack>
        <Typography sx={{ whiteSpace: "normal", opacity: active ? 0.95 : 0.82 }}>{guide.oneLine}</Typography>
      </Stack>
    </Button>
  );
}

function ExplainLine({ label, text }: { label: string; text: string }) {
  return (
    <Box sx={{ border: "1px solid rgba(148, 163, 184, 0.22)", borderRadius: 2, p: 1.5 }}>
      <Typography sx={{ fontWeight: 900 }}>{label}</Typography>
      <Typography color="text.secondary">{text}</Typography>
    </Box>
  );
}

function AnswerBox({ title, text, highlight = false }: { title: string; text: string; highlight?: boolean }) {
  return (
    <Box
      sx={{
        border: "1px solid rgba(148, 163, 184, 0.22)",
        borderRadius: 2,
        p: 2,
        mb: 1.5,
        bgcolor: highlight ? "rgba(37, 99, 235, 0.16)" : "rgba(15, 23, 42, 0.46)"
      }}
    >
      <Typography color="text.secondary" sx={{ mb: 0.75 }}>
        {title}
      </Typography>
      <Typography sx={{ fontSize: 17 }}>{text}</Typography>
    </Box>
  );
}

const corruptionLabels: Record<string, string> = {
  drop_latest_records: "doc gốc bị rơi khỏi dữ liệu",
  blank_summary: "summary bị xóa trắng",
  inject_text_noise: "summary/text_for_embedding bị chèn ký tự rác",
  truncate_title: "title bị cắt ngắn",
  stale_date: "ngày published bị lùi cũ",
  duplicate_rows: "bản ghi bị nhân đôi"
};

const corruptionExplanations: Record<string, string> = {
  drop_latest_records: "Nếu doc gốc bị drop, ChromaDB không còn vector chuẩn để trả về nên RAG phải kéo một doc gần nghĩa khác.",
  blank_summary: "Summary rỗng làm vector thiếu nội dung chính, nên semantic search dễ đánh giá sai độ liên quan.",
  inject_text_noise: "Ký tự rác đi vào text embedding làm vector bị méo, khiến khoảng cách vector không còn phản ánh đúng ý nghĩa.",
  truncate_title: "Title cụt làm các câu hỏi theo tên bài match kém hơn hoặc match sang bài có nội dung gần giống.",
  stale_date: "Ngày bị lùi cũ làm freshness SLA cảnh báo dữ liệu mốc; câu hỏi ngày tháng có thể trả lời sai.",
  duplicate_rows: "Duplicate tạo nhiều vector giống nhau, làm top-k bị lặp và đẩy tài liệu đúng ra khỏi danh sách."
};

function CorruptedReason({
  answer,
  corruptionLog
}: {
  answer: AnswerRecord;
  corruptionLog: ArtifactState<CorruptionLog>;
}) {
  const analysis = buildCorruptedAnalysis(answer, corruptionLog);

  return (
    <Alert severity="error" sx={{ mt: 0.5 }}>
      <Typography sx={{ fontWeight: 900, mb: 0.75 }}>Vì sao dữ liệu bẩn làm kết quả bị lệch?</Typography>
      <Typography component="div">
        - Doc đúng cần tìm: <strong>{analysis.expectedDoc}</strong>
        <br />
        - Doc ChromaDB kéo top-1: <strong>{analysis.topDoc}</strong>
        <br />
        - Trạng thái retrieve: <strong>{answer.retrieval_hit ? "có chứa doc đúng trong top-k" : "lệch, không chứa doc đúng trong top-k"}</strong>
        <br />
        - Lỗi liên quan: <strong>{analysis.relatedIssues}</strong>
        <br />- Kết luận: {analysis.conclusion}
      </Typography>
    </Alert>
  );
}

function buildCorruptedAnalysis(answer: AnswerRecord, corruptionLog: ArtifactState<CorruptionLog>) {
  const expectedIds = answer.ground_truth_doc_ids;
  const retrievedIds = answer.retrieved_doc_ids;
  const expectedDoc = expectedIds.join(", ") || "không có";
  const topDoc = retrievedIds[0] ?? "không retrieve được doc";
  const scenarioMap = buildScenarioMap(corruptionLog);
  const expectedIssues = uniqueFlat(expectedIds.map((docId) => scenarioMap[docId] ?? []));
  const retrievedIssues = uniqueFlat(retrievedIds.slice(0, 3).map((docId) => scenarioMap[docId] ?? []));
  const allIssues = uniqueFlat([...expectedIssues, ...retrievedIssues]);
  const labels = allIssues.map((scenario) => corruptionLabels[scenario] ?? scenario);
  const relatedIssues = labels.length > 0 ? labels.join("; ") : "không thấy doc này trong corruption_log, nhưng top-k vẫn bị ảnh hưởng bởi index bẩn";
  const contextSignals = detectContextSignals(answer);
  const conclusion = buildConclusion(answer, expectedIssues, retrievedIssues, contextSignals, topDoc);

  return {
    expectedDoc,
    topDoc,
    relatedIssues,
    conclusion
  };
}

function buildScenarioMap(corruptionLog: ArtifactState<CorruptionLog>): Record<string, string[]> {
  if (corruptionLog.status !== "ready") {
    return {};
  }
  const map: Record<string, string[]> = {};
  for (const scenario of corruptionLog.data.scenarios) {
    for (const paperId of scenario.affected_paper_ids ?? []) {
      map[paperId] = [...(map[paperId] ?? []), scenario.scenario];
    }
  }
  return map;
}

function uniqueFlat(values: string[][] | string[]): string[] {
  return Array.from(new Set(values.flat()));
}

function detectContextSignals(answer: AnswerRecord): string[] {
  const contexts = (answer.retrieved_contexts ?? []).join("\n");
  const signals: string[] = [];
  if (/[#@!$~%^&|\\]|NULL_TOKEN|xkcd###|qz9\$\$x|&&\*\*/.test(contexts)) {
    signals.push("context retrieve có ký tự rác");
  }
  if (/Summary:\s*(\n|$)/.test(contexts)) {
    signals.push("có retrieved context bị rỗng summary");
  }
  if (/Published:\s*2021-/.test(contexts)) {
    signals.push("có retrieved context bị lùi ngày về 5 năm trước");
  }
  return signals;
}

function buildConclusion(
  answer: AnswerRecord,
  expectedIssues: string[],
  retrievedIssues: string[],
  contextSignals: string[],
  topDoc: string
): string {
  if (expectedIssues.includes("drop_latest_records") && !answer.retrieval_hit) {
    return `doc gốc đã bị loại khỏi dữ liệu bẩn, nên ChromaDB buộc phải kéo doc gần nghĩa ${topDoc}; đây là lệch nguồn retrieval.`;
  }
  if (retrievedIssues.includes("inject_text_noise") || expectedIssues.includes("inject_text_noise")) {
    return answer.retrieval_hit
      ? "doc đúng vẫn được kéo ra, nhưng chính nội dung/context của doc đó đã bị chèn noise nên câu trả lời bị nhiễu so với bản sạch."
      : "noise đã đi vào embedding text, làm vector lệch khỏi ý nghĩa gốc nên ChromaDB kéo sai nguồn.";
  }
  if (retrievedIssues.includes("blank_summary")) {
    return "summary bị rỗng làm vector thiếu tín hiệu nội dung, nên retrieval dễ kéo nhầm tài liệu gần đó.";
  }
  if (retrievedIssues.includes("stale_date") || expectedIssues.includes("stale_date")) {
    return "ngày published bị sửa cũ, nên câu hỏi về thời điểm/freshness có thể trả lời lệch so với ground truth.";
  }
  if (retrievedIssues.includes("duplicate_rows")) {
    return "top-k bị bản ghi duplicate chiếm chỗ, nên retrieval nhìn có vẻ tự tin nhưng nguồn bị nhiễu.";
  }
  if (contextSignals.length > 0) {
    return `${contextSignals.join("; ")}, vì vậy RAG đang trả lời trên context đã hỏng thay vì context chuẩn.`;
  }
  if (!answer.retrieval_hit) {
    return `doc đúng không xuất hiện trong top-k; RAG đang trả lời dựa trên ${topDoc}, không phải nguồn ground truth.`;
  }
  return "doc đúng vẫn còn trong top-k, nhưng nội dung bị tiêm lỗi làm câu trả lời hoặc điểm đánh giá giảm so với baseline.";
}

function buildRawDemoAnswers(answers: AnswerRecord[]): AnswerRecord[] {
  return answers.map((item) => ({
    ...item,
    answer:
      item.question_type === "summary"
        ? "Cảnh báo demo: dữ liệu raw chưa clean nên summary có thể còn thẻ HTML/JATS hoặc bị thiếu. Pipeline chuẩn không nên cho index ở bước này."
        : item.question_type === "authors"
          ? "Cảnh báo demo: field authors trong raw có thể chưa được chuẩn hóa, nên RAG không nên trả lời tác giả trước bước clean."
          : item.question_type === "date"
            ? "Cảnh báo demo: ngày published trong raw có thể chưa parse ISO 8601, nên câu trả lời ngày tháng không đáng tin."
            : item.question_type === "category"
              ? "Cảnh báo demo: categories trong raw có thể chưa chuẩn hóa, nên phân loại lĩnh vực dễ sai."
              : "Cảnh báo demo: multi-hop trên raw rất rủi ro vì nhiều field chưa sạch, RAG có thể ghép nhầm thông tin.",
    retrieval_hit: false,
    token_f1: 0,
    judge: {
      score: 1,
      correct: false,
      reasoning: "Raw/pre-clean mode is a UI demonstration of why the quality gate must run before indexing."
    }
  }));
}

function MetricNotes({
  metrics,
  answer,
  mode
}: {
  metrics: ArtifactState<AnyMetrics>;
  answer: AnswerRecord;
  mode: "demo" | "real";
}) {
  const metricData = metrics.status === "ready" ? metrics.data : undefined;
  const nested = metricData?.rag;
  const retrievalHitRate = nested?.retrieval_hit_rate ?? metricData?.retrieval_hit_rate;
  const tokenF1 = nested?.mean_token_f1 ?? metricData?.mean_token_f1;
  const judgeScore = nested?.mean_judge_score ?? metricData?.mean_judge_score;

  return (
    <Box sx={{ border: "1px solid rgba(148, 163, 184, 0.22)", borderRadius: 2, p: 2 }}>
      <Typography variant="h5">Chỉ số đánh giá câu trả lời</Typography>
      {mode === "demo" ? (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          Case “trước clean” là mô phỏng để trình bày: pipeline thật phải clean + quality gate trước khi index.
        </Alert>
      ) : null}
      <Stack spacing={1.5} sx={{ mt: 1.5 }}>
        <MetricLine
          label="Retrieval Hit Rate"
          value={typeof retrievalHitRate === "number" ? `${Math.round(retrievalHitRate * 100)}%` : "N/A"}
          note="RAG có tìm trúng tài liệu gốc không. 100% là câu nào cũng tìm trúng; thấp hơn nghĩa là có câu tìm sai nguồn."
        />
        <MetricLine
          label="Token F1"
          value={typeof tokenF1 === "number" ? tokenF1.toFixed(3) : "N/A"}
          note="Câu trả lời giống đáp án chuẩn bao nhiêu theo từ khóa/token. Càng cao càng giống đáp án chuẩn."
        />
        <MetricLine
          label="Judge Score"
          value={typeof judgeScore === "number" ? judgeScore.toFixed(1) : "N/A"}
          note="Điểm chấm chất lượng câu trả lời. Nếu không có API LLM judge thì demo dùng cách chấm heuristic."
        />
        <MetricLine
          label="Câu này retrieve"
          value={answer.retrieval_hit ? "Trúng" : "Sai hoặc không chắc"}
          note="Chỉ riêng câu đang bấm: RAG có kéo đúng document thật hay không."
        />
        <MetricLine
          label="Doc được kéo ra"
          value={`${answer.retrieved_doc_ids.length} docs`}
          note={answer.retrieved_doc_ids.slice(0, 3).join(", ") || "Không có doc id"}
        />
      </Stack>
    </Box>
  );
}

function MetricLine({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" spacing={2}>
        <Typography sx={{ fontWeight: 900 }}>{label}</Typography>
        <Typography color="primary.light" sx={{ fontWeight: 900 }}>
          {value}
        </Typography>
      </Stack>
      <Typography color="text.secondary">{note}</Typography>
    </Box>
  );
}
