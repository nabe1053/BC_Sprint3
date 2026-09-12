"use client";
import { useEffect, useId, useRef, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { useStartAgentRun, useAgentRun } from "../hooks";
import { startFailure, runLimitDetails, type BlockedReason } from "../model";
import { RunProgress } from "./RunProgress";
import { RunSteps } from "./RunSteps";

export function AgentRunPanel({
  caseId,
  blockedReason,
  inputRevision = "",
  onBusyChange,
}: {
  caseId: number;
  blockedReason: BlockedReason | null;
  inputRevision?: string;
  onBusyChange?: (busy: boolean) => void;
}) {
  const { t } = useTranslation();
  const reasonId = useId();
  const [runId, setRunId] = useState<number | null>(null);
  const [acknowledgedRunId, setAcknowledgedRunId] = useState<number | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState<{
    kind: ReturnType<typeof startFailure>;
    revision: string;
    details: unknown;
  } | null>(null);
  const [confirmedRevision, setConfirmedRevision] = useState<string | null>(
    null,
  );
  const lock = useRef(false);
  const start = useStartAgentRun(caseId);
  const run = useAgentRun(runId);
  // 資料を変えた場合に限り、資料由来のサーバー判定を再確認できる。
  const errorKind =
    failure &&
    (!(failure.kind === "noReadable" || failure.kind === "limitExceeded") ||
      failure.revision === inputRevision)
      ? failure.kind
      : null;
  const limitDetails =
    errorKind === "limitExceeded" ? runLimitDetails(failure?.details) : null;
  const carryOver = errorKind === "carryOver";
  const acknowledged = carryOver && confirmedRevision === inputRevision;
  const pending = submitting || start.isPending;
  const running =
    runId !== null &&
    !run.isError &&
    (!run.data || run.data.outcome === "running");
  const uncertain =
    errorKind === "unknown" || errorKind === "inProgress" || run.isError;
  const blocked =
    blockedReason !== null ||
    pending ||
    running ||
    uncertain ||
    (!!errorKind && !carryOver) ||
    (carryOver && !acknowledged);
  useEffect(() => {
    onBusyChange?.(pending || running || uncertain);
  }, [onBusyChange, pending, running, uncertain]);
  useEffect(() => () => onBusyChange?.(false), [onBusyChange]);
  async function launch() {
    if (blocked || lock.current) return;
    lock.current = true;
    setSubmitting(true);
    setRunId(null);
    setAcknowledgedRunId(null);
    try {
      const accepted = await start.mutateAsync({
        acknowledgedCarryOver: acknowledged,
      });
      setRunId(accepted.runId);
      setAcknowledgedRunId(acknowledged ? accepted.runId : null);
      setFailure(null);
      setConfirmedRevision(null);
    } catch (error) {
      setFailure({
        kind: startFailure(error),
        revision: inputRevision,
        details: error instanceof ApiError ? error.details : null,
      });
      setConfirmedRevision(null);
    } finally {
      lock.current = false;
      setSubmitting(false);
    }
  }
  function resetState() {
    if (pending) return;
    setRunId(null);
    setFailure(null);
    setConfirmedRevision(null);
    setAcknowledgedRunId(null);
  }
  return (
    <Box
      component="section"
      aria-label={t("agentRuns.title")}
      sx={{
        display: "grid",
        gap: `${tokens.spacing.s3}px`,
        marginTop: `${tokens.spacing.s6}px`,
      }}
    >
      <Typography variant="h2">{t("agentRuns.title")}</Typography>
      <Button
        variant="contained"
        disabled={blocked}
        aria-describedby={blockedReason ? reasonId : undefined}
        onClick={() => void launch()}
      >
        {t(pending || running ? "agentRuns.pending" : "agentRuns.start")}
      </Button>
      <Typography variant="body2">{t("agentRuns.versionNote")}</Typography>
      {blockedReason && (
        <Typography id={reasonId}>
          {t(`agentRuns.blocked.${blockedReason}`)}
        </Typography>
      )}
      {errorKind && (
        <Box role="alert">
          <Typography>{t(`agentRuns.startError.${errorKind}`)}</Typography>
          {limitDetails && (
            <>
              <Typography>
                {t("agentRuns.limit.detail", {
                  label: t(`agentRuns.limit.label.${limitDetails.kind}`),
                  unit: t(`agentRuns.limit.unit.${limitDetails.kind}`),
                  actual: limitDetails.actual,
                  limit: limitDetails.limit,
                })}
              </Typography>
              {limitDetails.documentId !== null && (
                <Typography>
                  {t("agentRuns.limit.document", {
                    id: limitDetails.documentId,
                  })}
                </Typography>
              )}
            </>
          )}
          {carryOver && (
            <FormControlLabel
              control={
                <Checkbox
                  checked={acknowledged}
                  onChange={(_, checked) =>
                    setConfirmedRevision(checked ? inputRevision : null)
                  }
                />
              }
              label={t("agentRuns.acknowledge")}
            />
          )}
        </Box>
      )}
      {runId !== null &&
        (run.isError ? (
          <Box role="alert">
            <Typography>
              {t(
                run.error instanceof ApiError && run.error.status === 404
                  ? "agentRuns.notFound"
                  : "agentRuns.communicationInterrupted",
              )}
            </Typography>
            <Typography>{t("agentRuns.connectionHint")}</Typography>
          </Box>
        ) : run.data ? (
          <RunProgress
            run={run.data}
            acknowledgedCarryOver={acknowledgedRunId === run.data.runId}
          />
        ) : (
          <Typography role="status">{t("agentRuns.loading")}</Typography>
        ))}
      {uncertain && (
        <Button variant="outlined" disabled={pending} onClick={resetState}>
          {t("agentRuns.resetState")}
        </Button>
      )}
      {runId !== null && <RunSteps key={runId} runId={runId} />}
    </Box>
  );
}
