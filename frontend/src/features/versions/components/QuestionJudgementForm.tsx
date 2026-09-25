"use client";
import { useEffect, useState } from "react";
import { Box, Button, TableCell, TextField, Typography } from "@mui/material";
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
  showReason = true,
}: {
  question: QuestionResponse;
  recordedBy: string;
  onRecord: (input: JudgementInput) => Promise<boolean>;
  busy: boolean;
  // 一覧では要約を「確認事項の要約」列に出すため繰り返さない（F-13）。
  showReason?: boolean;
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
      {showReason ? (
        <Typography variant="body2">{question.reason}</Typography>
      ) : (
        <Typography variant="caption">{question.questionCode}</Typography>
      )}
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

type Draft = Pick<JudgementRequest, "status" | "resolution"> & { note: string };
const draftOf = (question: QuestionResponse): Draft => ({
  status: question.latest?.status ?? "open",
  resolution: question.latest?.resolution ?? "unresolved",
  note: question.latest?.note ?? "",
});
// 各列の入力を縦にそろえるため、どのセルの1件分も「上の注記・入力・下の注記」の3段にする。
const blockSx = {
  display: "grid",
  gridTemplateRows: "auto auto auto",
  gap: `${tokens.spacing.s1}px`,
} as const;
const blank = " ";

/**
 * Item List の右3列（対応状況／解決状態／判断内容）へ判断欄を1列ずつ置く（03-spec SCR-03）。
 * 3列をまとめた1セルに並べると列の境目とずれてはみ出すため、セルごとに分けて返す。
 */
export function QuestionJudgementCells({
  questions,
  recordedBy,
  onRecord,
  busy,
}: {
  questions: QuestionResponse[];
  recordedBy: string;
  onRecord: (input: JudgementInput) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  // 記録で最新が変わったら、入力中の値を最新の記録へ戻す。
  const latestKey = questions
    .map((q) => `${q.questionId}:${q.latest?.judgementId ?? ""}`)
    .join(",");
  useEffect(() => setDrafts({}), [latestKey]);
  const draft = (q: QuestionResponse) => drafts[q.questionId] ?? draftOf(q);
  const change = (q: QuestionResponse, patch: Partial<Draft>) =>
    setDrafts((current) => ({
      ...current,
      [q.questionId]: { ...(current[q.questionId] ?? draftOf(q)), ...patch },
    }));
  const stack = { display: "grid", gap: `${tokens.spacing.s3}px` } as const;
  return (
    <>
      <TableCell>
        <Box sx={stack}>
          {questions.map((q) => (
            <Box key={q.questionId} sx={blockSx}>
              <Typography variant="caption">{q.questionCode}</Typography>
              <TextField
                size="small"
                InputLabelProps={{ shrink: true }}
                select
                SelectProps={{ native: true }}
                label={t("versions.question.status")}
                value={draft(q).status}
                disabled={busy}
                onChange={(event) =>
                  change(q, {
                    status: event.target.value as Draft["status"],
                  })
                }
              >
                {(["open", "in_progress", "judged"] as const).map((value) => (
                  <option key={value} value={value}>
                    {t(`versions.question.statuses.${value}`)}
                  </option>
                ))}
              </TextField>
              <Typography variant="caption">{blank}</Typography>
            </Box>
          ))}
        </Box>
      </TableCell>
      <TableCell>
        <Box sx={stack}>
          {questions.map((q) => (
            <Box key={q.questionId} sx={blockSx}>
              <Typography variant="caption">{blank}</Typography>
              <TextField
                size="small"
                InputLabelProps={{ shrink: true }}
                select
                SelectProps={{ native: true }}
                label={t("versions.question.resolution")}
                value={draft(q).resolution}
                disabled={busy}
                onChange={(event) =>
                  change(q, {
                    resolution: event.target.value as Draft["resolution"],
                  })
                }
              >
                {(["unresolved", "resolved"] as const).map((value) => (
                  <option key={value} value={value}>
                    {t(`versions.question.resolutions.${value}`)}
                  </option>
                ))}
              </TextField>
              <Typography variant="caption">{blank}</Typography>
            </Box>
          ))}
        </Box>
      </TableCell>
      <TableCell>
        <Box sx={stack}>
          {questions.map((q) => (
            <Box
              key={q.questionId}
              component="form"
              aria-label={t("versions.question.title", {
                code: q.questionCode,
              })}
              onSubmit={(event) => {
                event.preventDefault();
                const { status, resolution, note } = draft(q);
                void onRecord({
                  questionId: q.questionId,
                  status,
                  resolution,
                  note: note.trim() || null,
                  recordedBy: recordedBy.trim(),
                });
              }}
              sx={blockSx}
            >
              <Typography variant="caption">{blank}</Typography>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: `${tokens.spacing.s2}px`,
                }}
              >
                <TextField
                  size="small"
                  InputLabelProps={{ shrink: true }}
                  label={t("versions.question.note")}
                  value={draft(q).note}
                  disabled={busy}
                  onChange={(event) => change(q, { note: event.target.value })}
                />
                <Button type="submit" variant="outlined" disabled={busy}>
                  {t("versions.question.record")}
                </Button>
              </Box>
              <Typography variant="caption">
                {q.latest
                  ? t("versions.recorded", {
                      by: q.latest.recordedBy,
                      at: formatDateTime(q.latest.recordedAt),
                    })
                  : t("versions.question.unrecorded")}
              </Typography>
            </Box>
          ))}
        </Box>
      </TableCell>
    </>
  );
}
