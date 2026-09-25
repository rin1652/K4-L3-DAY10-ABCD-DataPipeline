import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SendIcon from "@mui/icons-material/Send";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { useState } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  retrievedDocs?: string[];
  collectionUsed?: string;
  answerMode?: string;
}

export function ChatPlayground() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [collection, setCollection] = useState("papers-baseline");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const collectionLabels: Record<string, string> = {
    "papers-baseline": "📗 Dữ liệu Sạch (Baseline)",
    "papers-corrupted": "📕 Dữ liệu Bẩn (Corrupted)",
    "papers-repaired": "📘 Dữ liệu Đã Sửa (Repaired)"
  };

  const collectionExplanations: Record<string, string> = {
    "papers-baseline": "Dữ liệu gốc sau khi làm sạch, chưa bị tiêm lỗi",
    "papers-corrupted": "Dữ liệu đã bị tiêm 6 loại lỗi: thiếu tóm tắt, nhiễu văn bản, ngày cũ, v.v.",
    "papers-repaired": "Dữ liệu được xây dựng lại từ nguồn gốc ban đầu (idempotent repair)"
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: input,
          collection_name: collection
        })
      });

      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();
      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        retrievedDocs: data.retrieved_docs,
        collectionUsed: data.collection_used,
        answerMode: data.answer_mode
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError("Không thể kết nối tới API server. Hãy chạy: python script/run_api_server.py");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setError("");
  };

  return (
    <Card>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
          <Typography variant="h5">💬 Hỏi đáp RAG trực tiếp</Typography>
          <Button startIcon={<RefreshRoundedIcon />} onClick={handleClear} size="small">
            Xóa lịch sử
          </Button>
        </Stack>

        <Paper elevation={2} sx={{ p: 3, mb: 3, bgcolor: "rgba(15, 23, 42, 0.5)" }}>
          <Typography variant="body1" sx={{ mb: 2 }}>
            <strong>Hướng dẫn:</strong> Chọn nguồn dữ liệu và đặt câu hỏi để thấy RAG trả lời như thế nào. Khi dùng dữ
            liệu bẩn, bạn sẽ thấy câu trả lời kém chất lượng hơn.
          </Typography>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Chọn nguồn dữ liệu</InputLabel>
            <Select value={collection} label="Chọn nguồn dữ liệu" onChange={(e) => setCollection(e.target.value)}>
              {Object.entries(collectionLabels).map(([key, label]) => (
                <MenuItem key={key} value={key}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Alert severity="info" sx={{ mt: 2 }}>
            <strong>{collectionLabels[collection]}</strong>
            <br />
            {collectionExplanations[collection]}
          </Alert>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError("")}>
            {error}
          </Alert>
        )}

        <Paper
          elevation={3}
          sx={{ height: 400, overflow: "auto", p: 2, mb: 2, bgcolor: "rgba(15, 23, 42, 0.3)", borderRadius: 2 }}
        >
          {messages.length === 0 && (
            <Box sx={{ textAlign: "center", color: "text.secondary", mt: 10 }}>
              <Typography variant="h6">Chưa có cuộc hội thoại nào</Typography>
              <Typography variant="body2">Hãy đặt câu hỏi bên dưới để bắt đầu</Typography>
            </Box>
          )}

          <Stack spacing={2}>
            {messages.map((msg, idx) => (
              <Box key={idx}>
                <Paper
                  elevation={1}
                  sx={{
                    p: 2,
                    bgcolor: msg.role === "user" ? "rgba(33, 150, 243, 0.15)" : "rgba(76, 175, 80, 0.15)",
                    borderLeft: msg.role === "user" ? "4px solid #2196f3" : "4px solid #4caf50"
                  }}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                    {msg.role === "user" ? "👤 Bạn" : "🤖 RAG"}
                  </Typography>
                <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
                  {msg.content}
                </Typography>

                {msg.answerMode ? <Chip label={msg.answerMode} size="small" sx={{ mt: 1 }} /> : null}

                  {msg.retrievedDocs && msg.retrievedDocs.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Divider sx={{ mb: 1 }} />
                      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
                        📚 Tài liệu đã truy xuất từ {collectionLabels[msg.collectionUsed || collection]}:
                      </Typography>
                      <Stack direction="row" spacing={1} flexWrap="wrap">
                        {msg.retrievedDocs.map((docId, i) => (
                          <Chip
                            key={i}
                            label={docId}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontSize: "0.7rem" }}
                          />
                        ))}
                      </Stack>
                    </Box>
                  )}
                </Paper>
              </Box>
            ))}
          </Stack>
        </Paper>

        <Paper elevation={2} sx={{ p: 2, bgcolor: "rgba(15, 23, 42, 0.5)" }}>
          <Stack direction="row" spacing={2} alignItems="flex-end">
            <TextField
              fullWidth
              multiline
              maxRows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Ví dụ: Ai là tác giả của nghiên cứu về RAG?"
              disabled={loading}
            />
            <Button
              variant="contained"
              endIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
              onClick={handleSend}
              disabled={loading || !input.trim()}
              sx={{ minWidth: 120 }}
            >
              {loading ? "Đang hỏi..." : "Gửi"}
            </Button>
          </Stack>
        </Paper>

        <Paper elevation={1} sx={{ p: 2, mt: 3, bgcolor: "rgba(245, 158, 11, 0.12)" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
            💡 Gợi ý câu hỏi:
          </Typography>
          <Stack spacing={0.5}>
            <Typography variant="body2">• Ai là tác giả của nghiên cứu về machine learning?</Typography>
            <Typography variant="body2">• Tóm tắt nội dung nghiên cứu về neural networks</Typography>
            <Typography variant="body2">• Nghiên cứu nào được công bố năm 2023?</Typography>
          </Stack>
        </Paper>
      </CardContent>
    </Card>
  );
}
