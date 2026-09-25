import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import HelpRoundedIcon from "@mui/icons-material/HelpRounded";
import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { ReactNode } from "react";

type StatusCardProps = {
  title: string;
  status: "pass" | "fail" | "unknown";
  subtitle: string;
  children?: ReactNode;
};

const icons = {
  pass: <CheckCircleRoundedIcon color="success" fontSize="large" />,
  fail: <ErrorRoundedIcon color="error" fontSize="large" />,
  unknown: <HelpRoundedIcon color="warning" fontSize="large" />
};

export function StatusCard({ title, status, subtitle, children }: StatusCardProps) {
  const label = status === "pass" ? "PASS" : status === "fail" ? "FAIL" : "WAITING";

  return (
    <Card>
      <CardContent>
        <Stack direction="row" alignItems="flex-start" spacing={2}>
          <Box>{icons[status]}</Box>
          <Box sx={{ flex: 1 }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
              <Typography variant="h6">{title}</Typography>
              <Chip label={label} color={status === "pass" ? "success" : status === "fail" ? "error" : "warning"} />
            </Stack>
            <Typography color="text.secondary" sx={{ mt: 1 }}>
              {subtitle}
            </Typography>
            {children}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
