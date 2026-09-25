import { CssBaseline, ThemeProvider } from "@mui/material";
import React from "react";
import ReactDOM from "react-dom/client";
import { PipelineDashboard } from "../features/pipeline-dashboard/PipelineDashboard";
import { theme } from "./theme";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <PipelineDashboard />
    </ThemeProvider>
  </React.StrictMode>
);
