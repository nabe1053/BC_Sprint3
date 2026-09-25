"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { PageHeading } from "@/shared/ui";
import {
  useVersion,
  useItems,
  useQuestions,
  useVersionHistory,
  useRecords,
  useApprovalMutations,
} from "../hooks";
import {
  approvalSummary,
  recorderMeta,
  findVersionListItem,
  filterApprovalRows,
  hasChanges,
  unresolvedQuestions,
  buildStateEventRequest,
  buildBounceRequest,
  buildBounceCommentRequest,
  type ApprovalFilter,
} from "../model";
import { ApprovalSummaryCard } from "./ApprovalSummaryCard";
import { ReviewCheckPanel } from "./ReviewCheckPanel";
import { SendoffPanel } from "./SendoffPanel";
import { ApprovalFilters } from "./ApprovalFilters";
import { ApprovalTable } from "./ApprovalTable";
import { ApprovalListsDrawer } from "./ApprovalListsDrawer";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { ApprovalError } from "./ApprovalError";
import { formatDateTime } from "@/shared/lib/datetime";
export function ApprovalPage({
  caseId,
  versionId,
}: {
  caseId: number;
  versionId: number;
}) {
  const { t } = useTranslation(),
    router = useRouter(),
    version = useVersion(versionId),
    items = useItems(versionId),
    questions = useQuestions(versionId),
    history = useVersionHistory(caseId),
    records = useRecords(versionId),
    mutations = useApprovalMutations(caseId, versionId);
  const [name, setName] = useState(""),
    [filter, setFilter] = useState<ApprovalFilter>("all"),
    [drawer, setDrawer] = useState<
      | { kind: "lists"; itemId: number | null }
      | { kind: "evidence"; itemId: number }
      | null
    >(null),
    [error, setError] = useState<unknown>(null),
    [status, setStatus] = useState(""),
    [busy, setBusy] = useState(false),
    lock = useRef(false);
  const sources = [version, items, questions, history, records],
    loading = sources.some((q) => q.isLoading),
    listItem = findVersionListItem(history.data ?? [], versionId),
    loadError = sources.some((q) => q.isError) || (!loading && !listItem),
    missing = sources.some(
      (q) => q.error instanceof ApiError && q.error.status === 404,
    );
  const refresh = () => {
    setError(null);
    void Promise.all(sources.map((q) => q.refetch()));
  };
  async function record(action: () => Promise<unknown>, done?: () => void) {
    if (lock.current) return false;
    lock.current = true;
    setBusy(true);
    setError(null);
    setStatus("");
    try {
      await action();
      done?.();
      return true;
    } catch (cause) {
      setError(cause);
      return false;
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  const summary =
      version.data && listItem && records.data
        ? approvalSummary(version.data, listItem, records.data)
        : null,
    meta = records.data ? recorderMeta(records.data) : null;
  const metaValue = (row: { recordedBy: string; recordedAt: string } | null) =>
    row
      ? t("versions.approval.meta.recorded", {
          by: row.recordedBy,
          at: formatDateTime(row.recordedAt),
        })
      : t("versions.approval.meta.unrecorded");
  const rows = records.data
      ? filterApprovalRows(
          items.data ?? [],
          questions.data ?? [],
          records.data,
          filter,
        )
      : [],
    currentIndex =
      items.data?.findIndex((item) => item.itemId === drawer?.itemId) ?? -1,
    current = items.data?.[currentIndex],
    gap = `${tokens.spacing.s4}px`;
  return (
    <Box
      sx={{
        display: "grid",
        gap,
        minWidth: 0,
      }}
    >
      <PageHeading
        title={t("versions.approval.title")}
        description={t("versions.approval.description")}
        actions={
          <Button
            component={Link}
            href={`/cases/${caseId}/versions/${versionId}`}
          >
            {t("versions.approval.back")}
          </Button>
        }
      />
      {loading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : loadError ? (
        <Box role="alert">
          <Typography>
            {t(
              missing
                ? "versions.approval.notFound"
                : "versions.approval.loadError",
            )}
          </Typography>
          <Button variant="outlined" onClick={refresh}>
            {t("versions.approval.reload")}
          </Button>
        </Box>
      ) : (
        version.data &&
        listItem &&
        records.data &&
        summary &&
        meta && (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "minmax(0,1fr)",
                  lg: "repeat(3,minmax(0,1fr))",
                },
                gap,
              }}
            >
              <ApprovalSummaryCard summary={summary} />
              <ReviewCheckPanel
                state={version.data.currentState}
                recordedBy={name}
                onName={(value) => {
                  setName(value);
                  // 名前の入力で「名前が空」の拒否表示だけを解除する（他のエラーは残す）。
                  if (
                    error instanceof ApiError &&
                    error.code === "E_RECORDER_REQUIRED"
                  )
                    setError(null);
                }}
                busy={busy}
                rows={
                  new Set(records.data.unlinkedComments.map((c) => c.itemId))
                    .size
                }
                invalid={
                  error instanceof ApiError &&
                  error.code === "E_RECORDER_REQUIRED"
                }
                onApprove={() =>
                  void record(
                    () =>
                      mutations.transition.mutateAsync(
                        buildStateEventRequest("review_checked", name),
                      ),
                    () =>
                      setStatus(
                        t("versions.approval.review.done", {
                          unresolved: summary.unresolved,
                        }),
                      ),
                  )
                }
                onBounce={() =>
                  void record(
                    () =>
                      mutations.bounce.mutateAsync(
                        buildBounceRequest(
                          name,
                          records.data!.unlinkedComments.length,
                        ),
                      ),
                    () => router.push(`/cases/${caseId}/versions/${versionId}`),
                  )
                }
              />
              <SendoffPanel
                caseId={caseId}
                versionId={versionId}
                current={listItem.latestSendoff}
                onRecord={(input) => mutations.sendoff.mutateAsync(input)}
                busy={busy}
              />
            </Box>
            <Typography variant="caption">
              {t("versions.approval.meta.line", {
                staff: metaValue(meta.staff),
                coverage: metaValue(meta.coverage),
                review: metaValue(meta.review),
              })}
            </Typography>
            <Box>
              <Typography sx={{ fontWeight: tokens.typography.weight.bold }}>
                {t("versions.approval.notice.lead")}
              </Typography>
              {version.data.currentState === "draft" && (
                <>
                  <Typography sx={{ color: tokens.colors.warn.main }}>
                    {t("versions.approval.notice.incomplete", {
                      matched: summary.matched,
                      total: summary.total,
                      coverage: t(
                        `versions.coverageState.${summary.coverage ? "yes" : "no"}`,
                      ),
                    })}
                  </Typography>
                  <Button
                    component={Link}
                    href={`/cases/${caseId}/versions/${versionId}`}
                  >
                    {t("versions.approval.back")}
                  </Button>
                </>
              )}
              {summary.unresolved > 0 && (
                <Typography sx={{ color: tokens.colors.warn.main }}>
                  {t("versions.approval.notice.unresolved", {
                    unresolved: summary.unresolved,
                  })}
                </Typography>
              )}
            </Box>
            <ApprovalError
              error={error}
              caseId={caseId}
              versionId={versionId}
            />
            {status && <Typography role="status">{status}</Typography>}
            <ApprovalFilters
              value={filter}
              onChange={setFilter}
              shown={rows.length}
              total={items.data?.length ?? 0}
              changes={
                (items.data ?? []).filter((item) =>
                  hasChanges(item, questions.data ?? []),
                ).length
              }
              unresolved={unresolvedQuestions(questions.data ?? []).length}
              onLists={() => setDrawer({ kind: "lists", itemId: null })}
            />
            {!items.data?.length ? (
              <Typography>{t("versions.approval.emptyItems")}</Typography>
            ) : !rows.length ? (
              <Typography>{t("versions.approval.emptyFiltered")}</Typography>
            ) : (
              <ApprovalTable
                items={rows}
                questions={questions.data ?? []}
                records={records.data}
                busy={busy}
                onOpen={(itemId) => setDrawer({ kind: "lists", itemId })}
                onEvidence={(itemId) => setDrawer({ kind: "evidence", itemId })}
                onComment={(id, value) =>
                  record(() =>
                    mutations.bounceComment.mutateAsync(
                      buildBounceCommentRequest(id, value, name),
                    ),
                  )
                }
              />
            )}
            <Typography variant="caption">
              {t("versions.approval.tableNote")}
            </Typography>
            {drawer?.kind === "lists" && (
              <ApprovalListsDrawer
                items={items.data ?? []}
                questions={questions.data ?? []}
                itemId={drawer.itemId}
                onClose={() => setDrawer(null)}
                onAll={() => setDrawer({ kind: "lists", itemId: null })}
                onEvidence={(itemId) => setDrawer({ kind: "evidence", itemId })}
              />
            )}
            {drawer?.kind === "evidence" && current && (
              <EvidenceDrawer
                readOnly
                caseId={caseId}
                versionId={versionId}
                item={current}
                questions={questions.data ?? []}
                previous={items.data?.[currentIndex - 1]?.itemId ?? null}
                next={items.data?.[currentIndex + 1]?.itemId ?? null}
                onClose={() => setDrawer(null)}
                onMove={(itemId) => setDrawer({ kind: "evidence", itemId })}
                onReload={refresh}
              />
            )}
          </>
        )
      )}
    </Box>
  );
}
