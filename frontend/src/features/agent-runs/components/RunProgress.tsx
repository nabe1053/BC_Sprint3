"use client";
import Link from "next/link";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { AgentRunResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import {
  diagnosticCode,
  hasDraft,
  readProgress,
  stopReasonLabelKey,
  stageLabelKey,
  stageSteps,
  stepMark,
} from "../model";

export function RunProgress({
  run,
  caseId,
  acknowledgedCarryOver = false,
}: {
  run: AgentRunResponse;
  caseId: number;
  acknowledgedCarryOver?: boolean;
}) {
  const { t } = useTranslation();
  const count = run.stage === "reading" ? readProgress(run.stageDetail) : null;
  const diagnostic = diagnosticCode(run.stageDetail);
  const active = run.outcome === "running";
  const complete = hasDraft(run);
  return (
    <Box role="status" aria-live="polite">
      {active ? (
        <>
          <Typography>
            {count
              ? t("agentRuns.readingCount", count)
              : t(stageLabelKey(run.stage))}
          </Typography>
          <Box
            component="ol"
            aria-label={t("agentRuns.steps.stagesLabel")}
            sx={{ margin: 0, paddingLeft: `${tokens.spacing.s5}px` }}
          >
            {stageSteps.map((step, index) => {
              const mark = stepMark(run.stage, index);
              return (
                <Typography
                  component="li"
                  key={step}
                  sx={
                    mark === "current"
                      ? { fontWeight: tokens.typography.weight.semibold }
                      : undefined
                  }
                >
                  {t("agentRuns.stageStepLine", {
                    step: t(`agentRuns.stageStep.${step}`),
                    mark: t(`agentRuns.stageMark.${mark}`),
                  })}
                </Typography>
              );
            })}
          </Box>
        </>
      ) : complete ? (
        <>
          <Typography sx={{ color: tokens.colors.ok.main }}>
            {t(stopReasonLabelKey(run.stopReason))}
          </Typography>
          {!run.isComplete && (
            <Typography sx={{ color: tokens.colors.warn.main }}>
              {t("agentRuns.partial")}
            </Typography>
          )}
          <Button
            component={Link}
            href={`/cases/${caseId}/versions/${run.versionId}`}
          >
            {t("agentRuns.resultNote")}
          </Button>
          {acknowledgedCarryOver && (
            <Typography>{t("agentRuns.carryOverResult")}</Typography>
          )}
        </>
      ) : (
        <>
          <Typography sx={{ color: tokens.colors.danger.main }}>
            {t(
              stopReasonLabelKey(
                run.stopReason === "completed" ? null : run.stopReason,
              ),
            )}
          </Typography>
          <Typography>{t("agentRuns.stoppedHint")}</Typography>
        </>
      )}
      <Typography>
        {t("agentRuns.elapsed", {
          seconds: Math.floor(run.elapsedSec),
          turns: run.turns,
        })}
      </Typography>
      {!active && run.outcome !== "success" && diagnostic && (
        <Typography>{t(`agentRuns.diagnostic.${diagnostic}`)}</Typography>
      )}
    </Box>
  );
}
