"use client";
import { useRef, useState } from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { RowMatchResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { useCoverageMutations } from "../hooks";
import { buildCoverageRequest, inventoryErrorKey } from "../model";
export function CoverageRecordPanel({
  versionId,
  coverage,
  onReload,
}: {
  versionId: number;
  coverage: RowMatchResponse | null;
  onReload: () => void;
}) {
  const { t } = useTranslation();
  const mutations = useCoverageMutations(versionId);
  const [recordedBy, setRecordedBy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const gap = `${tokens.spacing.s4}px`;
  async function record() {
    if (lock.current) return;
    try {
      const input = buildCoverageRequest(recordedBy);
      lock.current = true;
      setBusy(true);
      setError(null);
      if (coverage)
        await mutations.undoConfirmation.mutateAsync({
          confirmationId: coverage.confirmationId,
          recordedBy: input.recordedBy,
        });
      else await mutations.confirm.mutateAsync(input);
    } catch (cause) {
      setError(inventoryErrorKey(cause));
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  return (
    <Paper
      component="section"
      aria-label={t("versions.inventory.recordTitle")}
      variant="outlined"
      sx={{
        padding: gap,
        display: "grid",
        gap,
        alignContent: "start",
        minWidth: 0,
      }}
    >
      <Typography variant="h2">
        {t("versions.inventory.recordTitle")}
      </Typography>
      <TextField
        required
        InputLabelProps={{ shrink: true }}
        label={t("versions.inventory.recorder")}
        helperText={t("versions.inventory.recorderHint")}
        value={recordedBy}
        onChange={(event) => setRecordedBy(event.target.value)}
        disabled={busy}
      />
      <Typography>
        {coverage
          ? t("versions.inventory.recorded", {
              name: coverage.recordedBy,
              at: coverage.recordedAt,
            })
          : t("versions.inventory.unrecorded")}
      </Typography>
      <Box>
        <Button
          variant="outlined"
          onClick={() => void record()}
          disabled={busy}
        >
          {t(
            coverage ? "versions.inventory.undo" : "versions.inventory.record",
          )}
        </Button>
      </Box>
      <Typography>
        {t(
          coverage
            ? "versions.inventory.undoNote"
            : "versions.inventory.requiredNote",
        )}
      </Typography>
      {busy && <Typography role="status">{t("versions.pending")}</Typography>}
      {error && (
        <Box role="alert">
          <Typography>{t(error)}</Typography>
          <Button
            variant="outlined"
            onClick={() => {
              setError(null);
              onReload();
            }}
          >
            {t("versions.inventory.reload")}
          </Button>
        </Box>
      )}
    </Paper>
  );
}
