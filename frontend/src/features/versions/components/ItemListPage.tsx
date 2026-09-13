"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  ItemCurrentResponse,
  ItemEditRequest,
} from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import {
  useVersionHistory,
  useVersion,
  useItems,
  useQuestions,
  useRecordMutations,
} from "../hooks";
import {
  findVersionListItem,
  emptyFilters,
  filterItems,
  recordErrorKey,
} from "../model";
import { StaffCheckAction } from "./StaffCheckAction";
import { BounceBanner } from "./BounceBanner";
import { VersionSummary } from "./VersionSummary";
import { VersionHistory } from "./VersionHistory";
import { ExportButton } from "./ExportButton";
import { ItemFilters } from "./ItemFilters";
import { ItemTable } from "./ItemTable";
import { EvidenceDrawer } from "./EvidenceDrawer";
import {
  QuestionJudgementForm,
  type JudgementInput,
} from "./QuestionJudgementForm";
export function ItemListPage({
  caseId,
  versionId,
}: {
  caseId: number;
  versionId: number;
}) {
  const { t } = useTranslation();
  const version = useVersion(versionId);
  const history = useVersionHistory(caseId);
  const listItem = findVersionListItem(history.data ?? [], versionId);
  const items = useItems(versionId);
  const questions = useQuestions(versionId);
  const mutations = useRecordMutations(versionId, caseId);
  const [recordedBy, setRecordedBy] = useState("");
  const [recorderInvalid, setRecorderInvalid] = useState(false);
  const [filters, setFilters] = useState({ ...emptyFilters });
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  const rows = filterItems(items.data ?? [], questions.data ?? [], filters);
  const index = rows.findIndex((item) => item.itemId === selected);
  const current = rows[index];
  const refresh = () => {
    setError(null);
    void Promise.all([
      version.refetch(),
      items.refetch(),
      questions.refetch(),
      history.refetch(),
    ]);
  };
  async function record(by: string, action: () => Promise<unknown>) {
    if (lock.current) return false;
    if (!by.trim()) {
      setError("versions.errors.E_RECORDER_REQUIRED");
      return false;
    }
    lock.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
      return true;
    } catch (cause) {
      setError(recordErrorKey(cause));
      return false;
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }
  function match(item: ItemCurrentResponse) {
    void record(recordedBy, () =>
      item.rowMatch
        ? mutations.undoConfirmation.mutateAsync({
            confirmationId: item.rowMatch.confirmationId,
            recordedBy: recordedBy.trim(),
          })
        : mutations.confirm.mutateAsync({
            kind: "row_match",
            itemId: item.itemId,
            recordedBy: recordedBy.trim(),
          }),
    );
  }
  const edit = (input: ItemEditRequest) =>
    record(input.recordedBy, () => mutations.edit.mutateAsync(input));
  const judge = (input: JudgementInput) =>
    record(input.recordedBy, () => mutations.judge.mutateAsync(input));
  const gap = `${tokens.spacing.s4}px`;
  const loading =
    version.isLoading ||
    items.isLoading ||
    questions.isLoading ||
    history.isLoading;
  const loadError =
    version.isError ||
    items.isError ||
    questions.isError ||
    history.isError ||
    (!loading && !listItem);
  // 03-spec:237「未生成」の無効化。本ルートは URL に versionId を持つため
  // （AD-024 ①）、版が 1 つも無い状態は T-503 の契約で取得失敗に畳まれる。
  // **現契約ではこの分岐は到達しない**（loadError が先に真になる）。
  // 齟齬は memory TODO-044 として研修者判断に上げる（本スライスで決めない）。
  const notGenerated = !loading && !history.isError && !history.data?.length;
  const missing =
    version.error instanceof ApiError && version.error.status === 404;
  return (
    <Box
      component="main"
      sx={{
        padding: `${tokens.spacing.s6}px`,
        display: "grid",
        gap,
        minWidth: 0,
      }}
    >
      <Box
        component="header"
        sx={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          gap,
        }}
      >
        <Box>
          <Typography variant="h1">{t("versions.title")}</Typography>
          <Typography>{t("versions.description")}</Typography>
        </Box>
        {version.data && !loading && !loadError && (
          <ExportButton
            versionId={versionId}
            label={t("versions.export.button")}
            disabled={notGenerated}
          />
        )}
        {version.data && !loading && !loadError && (
          <StaffCheckAction
            caseId={caseId}
            version={version.data}
            recordedBy={recordedBy}
            onRecorderInvalid={setRecorderInvalid}
          />
        )}
        <Button component={Link} href="/cases">
          {t("versions.back")}
        </Button>
      </Box>
      {loading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : loadError ? (
        <Box role="alert">
          <Typography>
            {t(missing ? "versions.notFound" : "versions.loadError")}
          </Typography>
          <Button variant="outlined" onClick={refresh}>
            {t("versions.reload")}
          </Button>
        </Box>
      ) : (
        version.data && (
          <>
            <VersionHistory caseId={caseId} versionId={versionId} />
            <VersionSummary version={version.data} />
            {listItem && <BounceBanner item={listItem} />}
            <Box
              sx={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap,
              }}
            >
              <TextField
                InputLabelProps={{ shrink: true }}
                label={t("versions.recorder")}
                value={recordedBy}
                onChange={(event) => {
                  setRecordedBy(event.target.value);
                  setRecorderInvalid(false);
                }}
                inputProps={{ "aria-invalid": recorderInvalid }}
                helperText={t("versions.recorderHint")}
              />
              <Typography>
                {t("versions.coverage", {
                  state: t(
                    version.data.coverageConfirmed
                      ? "versions.coverageState.yes"
                      : "versions.coverageState.no",
                  ),
                })}
              </Typography>
              <Button
                component={Link}
                href={`/cases/${caseId}/versions/${versionId}/inventory`}
              >
                {t("versions.inventory.link")}
              </Button>
            </Box>
            <ItemFilters
              items={items.data ?? []}
              filters={filters}
              onChange={setFilters}
              count={rows.length}
            />
            {error && !current && (
              <Box role="alert">
                <Typography>{t(error)}</Typography>
                <Button variant="outlined" onClick={refresh}>
                  {t("versions.reload")}
                </Button>
              </Box>
            )}
            {busy && (
              <Typography role="status">{t("versions.pending")}</Typography>
            )}
            {!items.data?.length ? (
              <Typography>{t("versions.emptyItems")}</Typography>
            ) : !rows.length ? (
              <Typography>{t("versions.emptyFiltered")}</Typography>
            ) : (
              <ItemTable
                items={rows}
                questions={questions.data ?? []}
                recordedBy={recordedBy}
                onMatch={match}
                onOpen={setSelected}
                onJudge={judge}
                busy={busy}
              />
            )}
            {!!questions.data?.some((q) => q.itemId === null) && (
              <Paper
                component="section"
                aria-label={t("versions.caseQuestions")}
                variant="outlined"
                sx={{ padding: gap, display: "grid", gap }}
              >
                <Typography variant="h2">
                  {t("versions.caseQuestions")}
                </Typography>
                {questions.data
                  .filter((q) => q.itemId === null)
                  .map((q) => (
                    <QuestionJudgementForm
                      key={q.questionId}
                      question={q}
                      recordedBy={recordedBy}
                      onRecord={judge}
                      busy={busy}
                    />
                  ))}
              </Paper>
            )}
            {!questions.data?.length && (
              <Typography>{t("versions.noQuestions")}</Typography>
            )}
            <Typography>{t("versions.judgementNote")}</Typography>
            <Typography>{t("versions.recordNote")}</Typography>
            {current && (
              <EvidenceDrawer
                caseId={caseId}
                versionId={versionId}
                item={current}
                questions={questions.data ?? []}
                recordedBy={recordedBy}
                previous={rows[index - 1]?.itemId ?? null}
                next={rows[index + 1]?.itemId ?? null}
                onClose={() => setSelected(null)}
                onMove={setSelected}
                onMatch={match}
                onEdit={edit}
                onUndo={(editId) =>
                  void record(recordedBy, () =>
                    mutations.undoEdit.mutateAsync({
                      editId,
                      recordedBy: recordedBy.trim(),
                    }),
                  )
                }
                onJudge={judge}
                busy={busy}
                error={error}
                onReload={refresh}
              />
            )}
          </>
        )
      )}
    </Box>
  );
}
