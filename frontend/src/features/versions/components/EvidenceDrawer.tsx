"use client";
import {
  Box,
  Button,
  Checkbox,
  Drawer,
  FormControlLabel,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  ItemCurrentResponse,
  ItemEditRequest,
  QuestionResponse,
} from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { useDocuments } from "@/features/documents";
import { useEvidence } from "../hooks";
import { editableFields, itemQuestions } from "../model";
import { ItemValue } from "./ItemValue";
import { EditForm } from "./EditForm";
import { EditHistory } from "./EditHistory";
import {
  QuestionJudgementForm,
  type JudgementInput,
} from "./QuestionJudgementForm";
const states: Record<string, keyof ItemCurrentResponse> = {
  od_value: "odState",
  od_unit: "odState",
  wall_value: "wallState",
  wall_unit: "wallState",
  weight_value: "weightState",
  weight_unit: "weightState",
  grade: "gradeState",
  connection: "connectionState",
  range_class: "lengthState",
  length_value: "lengthState",
  length_unit: "lengthState",
  qty_value: "qtyState",
  qty_unit: "qtyState",
  due_raw: "dueState",
  place_raw: "placeState",
};
const camel = (field: string) =>
  field.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
export function EvidenceDrawer({
  caseId,
  versionId,
  item,
  questions,
  recordedBy = "",
  readOnly = false,
  previous,
  next,
  onClose,
  onMove,
  onMatch,
  onEdit,
  onUndo,
  onJudge,
  busy = false,
  error = null,
  onReload,
}: {
  caseId: number;
  versionId: number;
  item: ItemCurrentResponse;
  questions: QuestionResponse[];
  recordedBy?: string;
  readOnly?: boolean;
  previous: number | null;
  next: number | null;
  onClose: () => void;
  onMove: (id: number) => void;
  onMatch?: (item: ItemCurrentResponse) => void;
  onEdit?: (input: ItemEditRequest) => Promise<boolean>;
  onUndo?: (id: number) => void;
  onJudge?: (input: JudgementInput) => Promise<boolean>;
  busy?: boolean;
  error?: string | null;
  onReload: () => void;
}) {
  const { t } = useTranslation();
  const evidence = useEvidence(versionId, item.itemId);
  const documents = useDocuments(caseId);
  const qs = itemQuestions(item, questions);
  return (
    <Drawer
      anchor="right"
      open
      onClose={onClose}
      PaperProps={{
        role: "dialog",
        "aria-labelledby": "evidence-title",
        sx: {
          width: "min(600px,94vw)",
          padding: `${tokens.spacing.s5}px`,
          display: "block",
        },
      }}
    >
      <Box sx={{ display: "grid", gap: `${tokens.spacing.s4}px` }}>
        <Box>
          <Typography id="evidence-title" variant="h2">
            {t("versions.drawer.title", { row: item.rowCode, kind: item.kind })}
          </Typography>
          <Button onClick={onClose}>{t("versions.drawer.close")}</Button>
        </Box>
        <Box sx={{ display: "flex", justifyContent: "space-between" }}>
          <Button
            variant="outlined"
            disabled={previous === null}
            onClick={() => previous !== null && onMove(previous)}
          >
            {t("versions.drawer.previous")}
          </Button>
          <Button
            variant="outlined"
            disabled={next === null}
            onClick={() => next !== null && onMove(next)}
          >
            {t("versions.drawer.next")}
          </Button>
        </Box>
        <Box>
          <Typography variant="h3">{t("versions.drawer.raw")}</Typography>
          {Object.entries(item)
            .filter(
              ([key, value]) =>
                key.endsWith("Raw") && typeof value === "string",
            )
            .map(([key, value]) => (
              <Box
                component="blockquote"
                key={key}
                sx={{
                  margin: 0,
                  padding: `${tokens.spacing.s3}px`,
                  borderLeft: `${tokens.border.quoteWidth}px solid ${tokens.colors.accent}`,
                  overflowWrap: "anywhere",
                  fontFamily: tokens.typography.mono,
                }}
              >
                {String(value)}
              </Box>
            ))}
        </Box>
        <Box>
          <Typography variant="h3">{t("versions.drawer.adopted")}</Typography>
          {evidence.isLoading ? (
            <Typography role="status">{t("common.loading")}</Typography>
          ) : evidence.isError ? (
            <Box role="alert">
              <Typography>{t("versions.loadError")}</Typography>
              <Button onClick={() => void evidence.refetch()}>
                {t("versions.reload")}
              </Button>
            </Box>
          ) : (
            <>
              {!evidence.data?.length && (
                <Typography>{t("versions.drawer.noEvidence")}</Typography>
              )}
              {[...editableFields, "due_raw", "place_raw"].map((field) => {
                const records =
                  evidence.data?.filter((row) => row.field === field) ?? [];
                const value = item[camel(field) as keyof ItemCurrentResponse];
                const state = states[field]
                  ? String(item[states[field]])
                  : null;
                return (
                  <Box
                    key={field}
                    sx={{
                      paddingBlock: `${tokens.spacing.s3}px`,
                      borderBottom: `${tokens.border.width}px solid ${tokens.colors.hair}`,
                      overflowWrap: "anywhere",
                    }}
                  >
                    <Typography variant="h3">
                      {t(
                        field === "due_raw"
                          ? "versions.columns.due"
                          : field === "place_raw"
                            ? "versions.header.place"
                            : `versions.edit.fields.${field}`,
                      )}
                    </Typography>
                    <ItemValue
                      value={typeof value === "string" ? value : null}
                      state={state}
                    />
                    {records.length ? (
                      records.map((row) => (
                        <Box key={row.evidenceId}>
                          <Typography>
                            {documents.data?.find(
                              (doc) => doc.documentId === row.documentId,
                            )?.fileName ?? t("versions.drawer.documentMissing")}
                          </Typography>
                          <Typography variant="caption">
                            {row.locator}
                          </Typography>
                          <Box
                            component="blockquote"
                            sx={{
                              margin: 0,
                              padding: `${tokens.spacing.s3}px`,
                              borderLeft: `${tokens.border.quoteWidth}px solid ${tokens.colors.accent}`,
                            }}
                          >
                            {row.quote}
                          </Box>
                          {(
                            [
                              "appliedCondition",
                              "conversionNote",
                              "changeReason",
                              "priorValue",
                            ] as const
                          ).map(
                            (key) =>
                              row[key] && (
                                <Typography key={key}>
                                  {t(`versions.drawer.${key}`)}
                                  {": "}
                                  {row[key]}
                                </Typography>
                              ),
                          )}
                        </Box>
                      ))
                    ) : (
                      <Typography variant="caption" component="div">
                        {t("versions.drawer.noFieldEvidence")}
                      </Typography>
                    )}
                  </Box>
                );
              })}
            </>
          )}
          {documents.isError && (
            <Box role="alert">
              <Typography>{t("versions.drawer.documentMissing")}</Typography>
              <Button onClick={() => void documents.refetch()}>
                {t("versions.reload")}
              </Button>
            </Box>
          )}
        </Box>
        {item.isInheritCandidate && (
          <Typography>{t("versions.drawer.inherit")}</Typography>
        )}
        {!readOnly && onMatch && (
          <FormControlLabel
            control={
              <Checkbox
                checked={!!item.rowMatch}
                disabled={busy}
                onChange={() => onMatch(item)}
              />
            }
            label={t("versions.matchLabel", { row: item.rowCode })}
          />
        )}
        {item.rowMatch && (
          <Typography variant="caption">
            {t("versions.recorded", {
              by: item.rowMatch.recordedBy,
              at: item.rowMatch.recordedAt,
            })}
          </Typography>
        )}
        {error && (
          <Box role="alert">
            <Typography>{t(error)}</Typography>
            <Button onClick={onReload}>{t("versions.reload")}</Button>
          </Box>
        )}
        {!readOnly && onEdit && (
          <EditForm
            key={item.itemId}
            itemId={item.itemId}
            recordedBy={recordedBy}
            onRecord={onEdit}
            busy={busy}
          />
        )}
        <EditHistory
          history={item.history}
          onUndo={onUndo}
          busy={busy}
          readOnly={readOnly}
        />
        <Box>
          <Typography variant="h3">{t("versions.drawer.questions")}</Typography>
          {qs.length ? (
            qs.map((q) =>
              !readOnly && onJudge ? (
                <QuestionJudgementForm
                  key={q.questionId}
                  question={q}
                  recordedBy={recordedBy}
                  onRecord={onJudge}
                  busy={busy}
                />
              ) : (
                <Box key={q.questionId}>
                  <Typography>{q.reason}</Typography>
                  <Typography>
                    {t(
                      `versions.question.statuses.${q.latest?.status ?? "open"}`,
                    )}
                    {" / "}
                    {t(
                      `versions.question.resolutions.${q.latest?.resolution ?? "unresolved"}`,
                    )}
                  </Typography>
                  {q.latest?.note && <Typography>{q.latest.note}</Typography>}
                  {q.latest && (
                    <Typography variant="caption">
                      {t("versions.recorded", {
                        by: q.latest.recordedBy,
                        at: q.latest.recordedAt,
                      })}
                    </Typography>
                  )}
                </Box>
              ),
            )
          ) : (
            <Typography>{t("versions.noQuestions")}</Typography>
          )}
        </Box>
      </Box>
    </Drawer>
  );
}
