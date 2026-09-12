"use client";
import { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { useAgentRunSteps } from "../hooks";

export function RunSteps({ runId }: { runId: number }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const steps = useAgentRunSteps(runId, open);
  return (
    <Box>
      <Button
        variant="text"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        {t(open ? "agentRuns.steps.hide" : "agentRuns.steps.show")}
      </Button>
      {open && (
        <Box>
          <Typography variant="body2">{t("agentRuns.steps.note")}</Typography>
          {steps.isLoading && <Typography>{t("common.loading")}</Typography>}
          {steps.isError && (
            <Typography role="alert">{t("agentRuns.steps.error")}</Typography>
          )}
          <Button
            variant="outlined"
            disabled={steps.isFetching}
            onClick={() => void steps.refetch()}
          >
            {t("agentRuns.steps.reload")}
          </Button>
          {!steps.isLoading && !steps.isError && steps.data?.length === 0 && (
            <Typography>{t("agentRuns.steps.empty")}</Typography>
          )}
          {!!steps.data?.length && (
            <Box
              component="ol"
              aria-label={t("agentRuns.steps.title")}
              sx={{
                paddingLeft: `${tokens.spacing.s6}px`,
                overflowWrap: "anywhere",
              }}
            >
              {[...steps.data]
                .sort((a, b) => a.seq - b.seq)
                .map((step) => (
                  <Box component="li" key={step.stepId} value={step.seq}>
                    <Typography>
                      {t("agentRuns.steps.entry", {
                        tool: step.toolName,
                        status: t(
                          `agentRuns.steps.status.${step.resultStatus}`,
                        ),
                      })}
                    </Typography>
                    {step.documentId !== null && (
                      <Typography variant="body2">
                        {t("agentRuns.steps.document", { id: step.documentId })}
                      </Typography>
                    )}
                    {step.locator && (
                      <Typography variant="body2">{step.locator}</Typography>
                    )}
                    {step.argsSummary && (
                      <Typography variant="body2">
                        {step.argsSummary}
                      </Typography>
                    )}
                    {step.durationMs !== null && (
                      <Typography variant="body2">
                        {t("agentRuns.steps.duration", { ms: step.durationMs })}
                      </Typography>
                    )}
                  </Box>
                ))}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
