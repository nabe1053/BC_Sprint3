"use client";
import { useState, type FormEvent } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import type { DocumentSummary } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { StatusNotice } from "@/shared/ui";
import { useExcludeDocument } from "../hooks";

const KNOWN = [
  "E_RUN_IN_PROGRESS",
  "E_ALREADY_EXCLUDED",
  "E_NOT_FOUND",
  "E_RECORDER_REQUIRED",
] as const;

/** F-16: 資料の除外（物理削除ではない）。除外者名は必須で AI は補完しない。 */
export function DocumentExcludeDialog({
  caseId,
  document,
  onClose,
}: {
  caseId: number;
  document: DocumentSummary;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const exclude = useExcludeDocument(caseId);
  const [recordedBy, setRecordedBy] = useState("");
  const [invalid, setInvalid] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = exclude.isPending;
  async function submit(event: FormEvent) {
    event.preventDefault();
    const name = recordedBy.trim();
    if (!name) {
      setInvalid(true);
      return;
    }
    setError(null);
    try {
      await exclude.mutateAsync({
        documentId: document.documentId,
        recordedBy: name,
      });
      onClose();
    } catch (cause) {
      const code = cause instanceof ApiError ? cause.code : null;
      setInvalid(code === "E_RECORDER_REQUIRED");
      setError(KNOWN.find((known) => known === code) ?? "unknown");
    }
  }
  return (
    <Dialog
      open
      onClose={() => {
        if (!pending) onClose();
      }}
      aria-labelledby="document-exclude-title"
    >
      <form onSubmit={(event) => void submit(event)} noValidate>
        <DialogTitle id="document-exclude-title">
          {t("documents.exclusion.title")}
        </DialogTitle>
        <DialogContent sx={{ display: "grid", gap: `${tokens.spacing.s3}px` }}>
          <Typography>
            {t("documents.exclusion.target", { name: document.fileName })}
          </Typography>
          <Typography variant="body2">
            {t("documents.exclusion.description")}
          </Typography>
          <TextField
            InputLabelProps={{ shrink: true }}
            label={t("documents.exclusion.recorder")}
            required
            value={recordedBy}
            disabled={pending}
            error={invalid}
            helperText={t("documents.exclusion.recorderHint")}
            inputProps={{ "aria-invalid": invalid }}
            onChange={(event) => {
              setRecordedBy(event.target.value);
              setInvalid(false);
            }}
          />
          {error && (
            <StatusNotice tone="danger">
              {t(`documents.exclusion.errors.${error}`)}
            </StatusNotice>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={pending}>
            {t("documents.exclusion.cancel")}
          </Button>
          <Button
            type="submit"
            variant="outlined"
            disabled={pending}
            // MUI の color="error" は oklch を演算できないため、トークンを CSS で直接当てる。
            sx={{
              color: tokens.colors.danger.main,
              borderColor: tokens.colors.danger.main,
              "&:hover": { borderColor: tokens.colors.danger[800] },
            }}
          >
            {t(
              pending
                ? "documents.exclusion.pending"
                : "documents.exclusion.submit",
            )}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
