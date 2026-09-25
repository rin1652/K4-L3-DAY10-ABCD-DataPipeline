import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0b1020",
      paper: "#111827"
    },
    primary: {
      main: "#60a5fa"
    },
    success: {
      main: "#22c55e"
    },
    warning: {
      main: "#f59e0b"
    },
    error: {
      main: "#ef4444"
    },
    info: {
      main: "#38bdf8"
    }
  },
  typography: {
    fontFamily: [
      "Inter",
      "ui-sans-serif",
      "system-ui",
      "-apple-system",
      "BlinkMacSystemFont",
      "Segoe UI",
      "sans-serif"
    ].join(","),
    h3: {
      fontWeight: 800,
      letterSpacing: 0
    },
    h4: {
      fontWeight: 800,
      letterSpacing: 0
    },
    h5: {
      fontWeight: 750,
      letterSpacing: 0
    },
    h6: {
      fontWeight: 750,
      letterSpacing: 0
    }
  },
  shape: {
    borderRadius: 8
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          border: "1px solid rgba(148, 163, 184, 0.18)",
          backgroundImage: "none"
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 700
        }
      }
    }
  }
});
