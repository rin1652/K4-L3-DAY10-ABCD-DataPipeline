import ArticleRoundedIcon from "@mui/icons-material/ArticleRounded";
import { Box, Card, CardContent, Tab, Tabs, Typography } from "@mui/material";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ArtifactState } from "../data/schemas";

type ReportViewerProps = {
  phase1Report: ArtifactState<string>;
  corruptionReport: ArtifactState<string>;
};

export function ReportViewer({ phase1Report, corruptionReport }: ReportViewerProps) {
  const [tab, setTab] = useState(0);
  const active = tab === 0 ? phase1Report : corruptionReport;

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <ArticleRoundedIcon color="primary" />
          <Typography variant="h5">Report Viewer</Typography>
        </Box>
        <Tabs value={tab} onChange={(_, value: number) => setTab(value)} sx={{ mt: 2 }}>
          <Tab label="Phase 1 report" />
          <Tab label="Corruption report" />
        </Tabs>
        <Box
          sx={{
            mt: 2,
            p: 2.5,
            borderRadius: 2,
            bgcolor: "rgba(15, 23, 42, 0.72)",
            border: "1px solid rgba(148, 163, 184, 0.16)",
            maxHeight: 460,
            overflow: "auto",
            "& table": { borderCollapse: "collapse", width: "100%" },
            "& th, & td": { border: "1px solid rgba(148, 163, 184, 0.24)", p: 1 },
            "& code": { color: "primary.light" }
          }}
        >
          {active.status === "ready" ? (
            <ReactMarkdown>{active.data}</ReactMarkdown>
          ) : (
            <Typography color="text.secondary">{active.message}</Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
