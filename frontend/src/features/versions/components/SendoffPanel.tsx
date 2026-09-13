"use client";
import { useRef, useState } from "react";
import { Button, MenuItem, Paper, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  SendoffDecisionRecord,
  SendoffDecisionRequest,
} from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { buildSendoffRequest } from "../model";
import { ApprovalError } from "./ApprovalError";
export function SendoffPanel({
  caseId,
  versionId,
  current,
  onRecord,
  busy,
}: {
  caseId: number;
  versionId: number;
  current: SendoffDecisionRecord | null;
  onRecord: (input: SendoffDecisionRequest) => Promise<unknown>;
  busy: boolean;
}) {
  const { t } = useTranslation(),
    [decision, setDecision] = useState<SendoffDecisionRequest["decision"]>(
      current?.decision ?? "undecided",
    ),
    [reason, setReason] = useState(current?.reason ?? ""),
    [name, setName] = useState(""),
    [error, setError] = useState<unknown>(null),
    [status, setStatus] = useState(""),
    [pending, setPending] = useState(false),
    lock = useRef(false);
  async function record() {
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError(null);
    setStatus("");
    try {
      const input = buildSendoffRequest(decision, reason, name);
      await onRecord(input);
      setStatus(
        t("versions.approval.sendoff.done", {
          decision: t(`versions.approval.sendoff.state.${input.decision}`),
        }),
      );
    } catch (cause) {
      setError(cause);
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return (
    <Paper
      component="section"
      variant="outlined"
      aria-labelledby="sendoff-title"
      sx={{
        padding: `${tokens.spacing.s4}px`,
        display: "grid",
        alignContent: "start",
        gap: `${tokens.spacing.s3}px`,
        minWidth: 0,
      }}
    >
      <Typography id="sendoff-title" variant="h2">
        {t("versions.approval.sendoff.title")}
      </Typography>
      <TextField
        select
        label={t("versions.approval.sendoff.decision")}
        value={decision}
        onChange={(e) => setDecision(e.target.value as typeof decision)}
      >
        {(["undecided", "hold", "approved"] as const).map((value) => (
          <MenuItem key={value} value={value}>
            {t(`versions.approval.sendoff.state.${value}`)}
          </MenuItem>
        ))}
      </TextField>
      <TextField
        label={t("versions.approval.sendoff.reason")}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        InputLabelProps={{ shrink: true }}
        inputProps={{
          "aria-invalid":
            error instanceof ApiError &&
            error.code === "E_SENDOFF_REASON_REQUIRED",
        }}
      />
      <TextField
        label={t("versions.approval.sendoff.recorder")}
        value={name}
        onChange={(e) => setName(e.target.value)}
        InputLabelProps={{ shrink: true }}
        inputProps={{
          "aria-required": true,
          "aria-invalid":
            error instanceof ApiError && error.code === "E_RECORDER_REQUIRED",
        }}
      />
      <Button
        variant="outlined"
        disabled={busy || pending}
        onClick={() => void record()}
      >
        {t("versions.approval.sendoff.record")}
      </Button>
      <Typography variant="caption">
        {t("versions.approval.sendoff.current", {
          decision: t(
            `versions.approval.sendoff.state.${current?.decision ?? "undecided"}`,
          ),
          by: current?.recordedBy ?? t("versions.approval.meta.unrecorded"),
          at: current?.recordedAt ?? t("common.notAvailable"),
        })}
      </Typography>
      <ApprovalError
        error={error}
        caseId={caseId}
        versionId={versionId}
        sendoff
      />
      {status && <Typography role="status">{status}</Typography>}
    </Paper>
  );
}
