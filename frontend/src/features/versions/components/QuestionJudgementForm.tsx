"use client";
import { useEffect, useState } from "react";
import { Box, Button, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  JudgementRequest,
  QuestionResponse,
} from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { formatDateTime } from "@/shared/lib/datetime";
export type JudgementInput = JudgementRequest & { questionId: number };
export function QuestionJudgementForm({
  question,
  recordedBy,
  onRecord,
  busy,
}: {
  question: QuestionResponse;
  recordedBy: string;
  onRecord: (input: JudgementInput) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<JudgementRequest["status"]>(
    question.latest?.status ?? "open",
  );
  const [resolution, setResolution] = useState<JudgementRequest["resolution"]>(
    question.latest?.resolution ?? "unresolved",
  );
  const [note, setNote] = useState(question.latest?.note ?? "");
  useEffect(() => {
    setStatus(question.latest?.status ?? "open");
    setResolution(question.latest?.resolution ?? "unresolved");
    setNote(question.latest?.note ?? "");
  }, [question.latest]);
  return (
    <Box
      component="form"
      aria-label={t("versions.question.title", { code: question.questionCode })}
      onSubmit={(event) => {
        event.preventDefault();
        void onRecord({
          questionId: question.questionId,
          status,
          resolution,
          note: note.trim() || null,
          recordedBy: recordedBy.trim(),
        });
      }}
      sx={{ display: "grid", gap: `${tokens.spacing.s2}px` }}
    >
      <Typography variant="body2">{question.reason}</Typography>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: `${tokens.spacing.s2}px`,
        }}
      >
        <TextField
          InputLabelProps={{ shrink: true }}
          select
          SelectProps={{ native: true }}
          label={t("versions.question.status")}
          value={status}
          disabled={busy}
          onChange={(event) => setStatus(event.target.value as typeof status)}
        >
          {(["open", "in_progress", "judged"] as const).map((value) => (
            <option key={value} value={value}>
              {t(`versions.question.statuses.${value}`)}
            </option>
          ))}
        </TextField>
        <TextField
          InputLabelProps={{ shrink: true }}
          select
          SelectProps={{ native: true }}
          label={t("versions.question.resolution")}
          value={resolution}
          disabled={busy}
          onChange={(event) =>
            setResolution(event.target.value as typeof resolution)
          }
        >
          {(["unresolved", "resolved"] as const).map((value) => (
            <option key={value} value={value}>
              {t(`versions.question.resolutions.${value}`)}
            </option>
          ))}
        </TextField>
        <TextField
          InputLabelProps={{ shrink: true }}
          label={t("versions.question.note")}
          value={note}
          disabled={busy}
          onChange={(event) => setNote(event.target.value)}
        />
        <Button type="submit" variant="outlined" disabled={busy}>
          {t("versions.question.record")}
        </Button>
      </Box>
      <Typography variant="caption">
        {question.latest
          ? t("versions.recorded", {
              by: question.latest.recordedBy,
              at: formatDateTime(question.latest.recordedAt),
            })
          : t("versions.question.unrecorded")}
      </Typography>
    </Box>
  );
}
