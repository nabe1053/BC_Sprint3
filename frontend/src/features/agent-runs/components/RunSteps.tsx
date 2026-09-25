"use client";
import { useState } from "react";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { useAgentRunSteps } from "../hooks";

/** 内部のツール名は画面に出さず、処理の名前で示す（memory AD-036 ⑤）。 */
function toolLabelKey(toolName: string, exists: (key: string) => boolean) {
  const key = `agentRuns.steps.tool.${toolName}`;
  return exists(key) ? key : "agentRuns.steps.tool.other";
}

export function RunSteps({
  runId,
  documentName,
}: {
  runId: number;
  documentName: (documentId: number) => string | null;
}) {
  const { t, i18n } = useTranslation();
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
                        tool: t(
                          toolLabelKey(step.toolName, (key) =>
                            i18n.exists(key),
                          ),
                        ),
                        status: t(
                          `agentRuns.steps.status.${step.resultStatus}`,
                        ),
                      })}
                    </Typography>
                    {step.documentId !== null &&
                      documentName(step.documentId) && (
                        <Typography variant="body2">
                          {t("agentRuns.steps.document", {
                            name: documentName(step.documentId),
                          })}
                        </Typography>
                      )}
                    {step.locator && (
                      <Typography variant="body2">{step.locator}</Typography>
                    )}
                    {step.durationMs !== null && (
                      <Typography variant="body2">
                        {step.durationMs < 100
                          ? t("agentRuns.steps.durationShort")
                          : t("agentRuns.steps.duration", {
                              seconds: (step.durationMs / 1000).toFixed(1),
                            })}
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
