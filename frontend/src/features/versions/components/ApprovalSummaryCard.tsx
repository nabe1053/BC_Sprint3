"use client";
import { Box, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import type { approvalSummary } from "../model";
import { sendoffTone, stateTone } from "../model";
export function ApprovalSummaryCard({
  summary,
}: {
  summary: ReturnType<typeof approvalSummary>;
}) {
  const { t } = useTranslation();
  const values = [
    ["state", t(`versions.state.${summary.state}`), stateTone(summary.state)],
    [
      "sendoff",
      t(`versions.approval.sendoff.state.${summary.sendoff}`),
      sendoffTone(summary.sendoff),
    ],
    [
      "matched",
      t("versions.approval.summary.matchedValue", summary),
      summary.matched === summary.total ? "ok" : "warn",
    ],
    [
      "coverage",
      t(`versions.coverageState.${summary.coverage ? "yes" : "no"}`),
      summary.coverage ? "ok" : "warn",
    ],
    ["edits", String(summary.edits), null],
    [
      "unresolved",
      String(summary.unresolved),
      summary.unresolved ? "warn" : null,
    ],
    [
      "bounceComments",
      String(summary.bounceComments),
      summary.bounceComments ? "warn" : null,
    ],
  ] as const;
  return (
    <Paper
      component="section"
      variant="outlined"
      aria-labelledby="approval-summary-title"
      sx={{ padding: `${tokens.spacing.s4}px`, minWidth: 0 }}
    >
      <Typography id="approval-summary-title" variant="h2">
        {t("versions.approval.summary.title")}
      </Typography>
      <Box
        component="dl"
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: `${tokens.spacing.s4}px`,
          margin: 0,
        }}
      >
        {values.map(([key, value, tone]) => (
          <Box key={key}>
            <Typography component="dt" variant="caption">
              {t(`versions.approval.summary.${key}`)}
            </Typography>
            <Typography
              component="dd"
              sx={{
                margin: 0,
                color: tone ? tokens.colors[tone].main : tokens.colors.text,
              }}
            >
              {value}
            </Typography>
            {key === "sendoff" && summary.noSendoff && (
              <Typography variant="caption">
                {t("versions.approval.summary.noSendoff")}
              </Typography>
            )}
          </Box>
        ))}
      </Box>
      {summary.bounced && (
        <Typography sx={{ color: tokens.colors.warn.main }}>
          {t("versions.approval.summary.bounced")}
        </Typography>
      )}
      {summary.needsRecheck && (
        <Typography sx={{ color: tokens.colors.warn.main }}>
          {t("versions.approval.summary.needsRecheck")}
        </Typography>
      )}
    </Paper>
  );
}
