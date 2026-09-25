"use client";

import { useId, useRef, useState, type ChangeEvent } from "react";
import Link from "next/link";
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { visuallyHidden } from "@mui/utils";
import { CaseMetadata } from "@/features/cases";
import { AgentRunPanel } from "@/features/agent-runs";
import type { DocumentSummary } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { Note, PageHeading } from "@/shared/ui";
import { useDocuments, useIntakeDocument } from "../hooks";

const limits = [
  "file_size",
  "document_count",
  "pdf_pages",
  "xlsx_sheets",
] as const;
type Limit = (typeof limits)[number];
function limitDetails(
  value: unknown,
): { limit: Limit; max: number; actual: number } | null {
  if (
    !value ||
    typeof value !== "object" ||
    !("limit" in value) ||
    !("max" in value) ||
    !("actual" in value)
  )
    return null;
  const limit = limits.find((key) => key === value.limit);
  return limit &&
    typeof value.max === "number" &&
    Number.isFinite(value.max) &&
    typeof value.actual === "number" &&
    Number.isFinite(value.actual)
    ? { limit, max: value.max, actual: value.actual }
    : null;
}
const statusColor = {
  success: tokens.colors.ok.main,
  partial: tokens.colors.warn.main,
  unreadable: tokens.colors.danger.main,
  encrypted: tokens.colors.danger.main,
  unsupported: tokens.colors.danger.main,
};
const gap = `${tokens.spacing.s4}px`;

// xlsx はセル単位の locator になり得るため、先頭だけ示して残りは件数にする。
const shownRanges = 3;
function partialLabelArgs(locators: string[]) {
  return {
    ranges: locators.slice(0, shownRanges).join("、"),
    rest: locators.length - shownRanges,
  };
}

// ページ数は PDF=ページ・xlsx=シートとして意味を持つ。txt の 1（本文1単位）や
// 判定できない null（.eml・破損）は件数として見せない（0 で埋めない・CV-003）。
function pageKey(document: DocumentSummary) {
  return document.pageCount !== null &&
    (document.kind === "pdf" || document.kind === "xlsx")
    ? document.kind
    : "none";
}

export function IntakePage({ caseId }: { caseId: number }) {
  const { t } = useTranslation();
  const list = useDocuments(caseId);
  const intake = useIntakeDocument(caseId);
  const fileId = useId();
  const lock = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  const [agentBusy, setAgentBusy] = useState(false);
  const busy = submitting || intake.isPending;
  const limitExceeded =
    error instanceof ApiError && error.code === "E_LIMIT_EXCEEDED";
  const details = limitExceeded ? limitDetails(error.details) : null;
  const unsupported =
    error instanceof ApiError && error.code === "E_UNSUPPORTED_FORMAT";
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file || lock.current || intake.isPending || agentBusy) return;
    lock.current = true;
    setSubmitting(true);
    setError(null);
    setSaved(false);
    try {
      await intake.mutateAsync(file);
      setSaved(true);
    } catch (cause) {
      setError(cause);
    } finally {
      input.value = "";
      lock.current = false;
      setSubmitting(false);
    }
  }
  return (
    <Box sx={{ display: "grid", gap }}>
      <PageHeading
        eyebrow={t("documents.eyebrow")}
        title={t("documents.title")}
        description={t("documents.description")}
        actions={
          <Button component={Link} href="/cases">
            {t("common.backToCases")}
          </Button>
        }
      />
      <Note>{t("documents.banner.noExternalLink")}</Note>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr",
          gap,
          [`@media (min-width:${tokens.breakpoints.sm}px)`]: {
            gridTemplateColumns: "1fr 2fr",
          },
        }}
      >
        <Paper variant="outlined" sx={{ padding: gap, alignSelf: "start" }}>
          <CaseMetadata caseId={caseId} />
          <Typography variant="body2">{t("documents.sourceNote")}</Typography>
          <AgentRunPanel
            key={caseId}
            caseId={caseId}
            showCarryOver
            onBusyChange={setAgentBusy}
            inputRevision={JSON.stringify(
              list.data?.map(({ documentId, readStatus }) => [
                documentId,
                readStatus,
              ]) ?? [],
            )}
            blockedReason={
              busy
                ? "uploading"
                : list.isLoading
                  ? "loading"
                  : list.isError
                    ? "documentsError"
                    : limitExceeded
                      ? "limitExceeded"
                      : !list.data?.some(
                            (document) =>
                              document.readStatus === "success" ||
                              document.readStatus === "partial",
                          )
                        ? "noReadable"
                        : null
            }
          />
        </Paper>
        <Paper variant="outlined" sx={{ padding: gap, display: "grid", gap }}>
          <Typography variant="h2">{t("documents.intakeTitle")}</Typography>
          <Typography>{t("documents.intakeDescription")}</Typography>
          <Box sx={{ display: "grid", gap: `${tokens.spacing.s2}px` }}>
            <Button
              component="label"
              variant="outlined"
              disabled={busy || agentBusy || list.error?.status === 404}
            >
              {t("documents.selectFile")}
              {/* 未対応形式もサーバで記録する契約なので、acceptによるブラウザ側の除外をしない。 */}
              <Box
                component="input"
                id={fileId}
                type="file"
                aria-label={t("documents.selectFile")}
                disabled={busy || agentBusy || list.error?.status === 404}
                onChange={upload}
                sx={visuallyHidden}
              />
            </Button>
            <Typography variant="body2">{t("documents.formats")}</Typography>
            <Typography variant="body2">
              {t("documents.limits.values")}
            </Typography>
            <Typography variant="body2">
              {t("documents.limits.provisional")}
            </Typography>
            <Typography variant="body2">
              {t("documents.duplicateNote")}
            </Typography>
          </Box>
          {busy && (
            <Typography role="status">{t("documents.pending")}</Typography>
          )}
          {saved && (
            <Typography role="status">{t("documents.success")}</Typography>
          )}
          {!!error && (
            <Box role="alert">
              {limitExceeded ? (
                <>
                  <Typography>{t("documents.limitExceeded.title")}</Typography>
                  {details && (
                    <Typography>
                      {t("documents.limitExceeded.detail", {
                        label: t(
                          `documents.limitExceeded.limitLabel.${details.limit}`,
                        ),
                        unit: t(
                          `documents.limitExceeded.unit.${details.limit}`,
                        ),
                        max: details.max,
                        actual: details.actual,
                      })}
                    </Typography>
                  )}
                  <Typography>{t("documents.limitExceeded.hint")}</Typography>
                </>
              ) : unsupported ? (
                <>
                  <Typography>
                    {t("documents.unsupportedFormat.title")}
                  </Typography>
                  <Typography>{t("documents.unsupportedHint")}</Typography>
                </>
              ) : (
                <Typography>
                  {t(
                    error instanceof ApiError && error.status === 404
                      ? "documents.error.notFound"
                      : "documents.requestError",
                  )}
                </Typography>
              )}
            </Box>
          )}
          <Typography variant="h2">{t("documents.list.title")}</Typography>
          {list.isLoading && (
            <Typography role="status">{t("common.loading")}</Typography>
          )}
          {list.isError && (
            <Box role="alert">
              <Typography>{t("documents.error.title")}</Typography>
              <Typography>
                {t(
                  list.error?.status === 404
                    ? "documents.error.notFound"
                    : "documents.error.hint",
                )}
              </Typography>
            </Box>
          )}
          <Box>
            <Button
              variant="outlined"
              onClick={() => void list.refetch()}
              disabled={busy || list.isFetching}
            >
              {t("common.reload")}
            </Button>
          </Box>
          {!list.isLoading && !list.isError && list.data?.length === 0 && (
            <Box>
              <Typography>{t("documents.empty.title")}</Typography>
              <Typography>{t("documents.empty.cta")}</Typography>
            </Box>
          )}
          {!!list.data?.length && (
            <TableContainer>
              <Table aria-label={t("documents.list.title")}>
                <TableHead>
                  <TableRow>
                    {["name", "kind", "pages", "status"].map((key) => (
                      <TableCell key={key}>
                        {t(`documents.list.columns.${key}`)}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {list.data.map((document) => (
                    <TableRow key={document.documentId}>
                      <TableCell component="th" scope="row">
                        {document.fileName}
                      </TableCell>
                      <TableCell>
                        {t(`documents.kind.${document.kind}`)}
                      </TableCell>
                      <TableCell>
                        {t(`documents.pages.${pageKey(document)}`, {
                          pages: document.pageCount,
                        })}
                      </TableCell>
                      <TableCell>
                        <Typography
                          component="span"
                          sx={{ color: statusColor[document.readStatus] }}
                        >
                          {document.readStatus === "partial" &&
                          document.unreadableLocators.length
                            ? t(
                                document.unreadableLocators.length > shownRanges
                                  ? "documents.partialRangeMore"
                                  : "documents.partialRange",
                                partialLabelArgs(document.unreadableLocators),
                              )
                            : t(`documents.readStatus.${document.readStatus}`)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
          {/* AD-006: encryptedは将来の判別用。現在の読取不能と混同させない。 */}
          <Typography variant="body2">
            {t("documents.encryptedNote")}
          </Typography>
          <Box component="details">
            <Box component="summary">{t("documents.examples.title")}</Box>
            <Box component="ul">
              {["partial", "reference", "attachment", "date"].map((key) => (
                <Typography component="li" key={key}>
                  {t(`documents.examples.${key}`)}
                </Typography>
              ))}
            </Box>
            <Typography variant="body2">
              {t("documents.examples.note")}
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}
