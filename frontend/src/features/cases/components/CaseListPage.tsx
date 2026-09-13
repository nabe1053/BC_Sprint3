"use client";

import { useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { tokens } from "@/shared/theme/tokens";
import { ApiError } from "@/shared/api/mutator";
import { useCases, useCreateCase } from "../hooks";

const stages = [
  "intake",
  "draft_review",
  "staff_checked",
  "review_checked",
] as const;
const gap = `${tokens.spacing.s4}px`;

export function CaseListPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const list = useCases();
  const create = useCreateCase();
  const [open, setOpen] = useState(false);
  const [caseCode, setCaseCode] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const lock = useRef(false);
  const busy = submitting || create.isPending;
  function showForm() {
    setError(null);
    setOpen(true);
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!caseCode.trim() || lock.current || create.isPending) return;
    lock.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const created = await create.mutateAsync({
        caseCode: caseCode.trim(),
        customerName: customerName.trim() || null,
        title: title.trim() || null,
      });
      router.push(`/cases/${created.caseId}/intake`);
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.code === "E_DUPLICATE_CASE_CODE"
          ? "duplicateError"
          : cause instanceof ApiError && cause.status === 422
            ? "validationError"
            : "requestError",
      );
    } finally {
      lock.current = false;
      setSubmitting(false);
    }
  }
  return (
    <Box
      component="main"
      sx={{ padding: `${tokens.spacing.s6}px`, display: "grid", gap }}
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
          <Typography variant="h1">{t("cases.list.title")}</Typography>
          <Typography>{t("cases.list.description")}</Typography>
        </Box>
        <Button variant={open ? "outlined" : "contained"} onClick={showForm}>
          {t("cases.list.newCaseButton")}
        </Button>
      </Box>
      {list.isLoading && (
        <Typography role="status">{t("common.loading")}</Typography>
      )}
      {list.isError && (
        <Box role="alert">
          <Typography>{t("cases.error.title")}</Typography>
          <Typography>{t("cases.error.hint")}</Typography>
          <Button variant="outlined" onClick={() => void list.refetch()}>
            {t("common.reload")}
          </Button>
        </Box>
      )}
      {!list.isLoading && !list.isError && list.data?.length === 0 && (
        <Paper variant="outlined" sx={{ padding: gap }}>
          <Typography>{t("cases.empty.title")}</Typography>
          <Button onClick={showForm}>{t("cases.empty.cta")}</Button>
        </Paper>
      )}
      {!!list.data?.length && (
        <TableContainer component={Paper} variant="outlined">
          <Table aria-label={t("cases.list.title")}>
            <TableHead>
              <TableRow>
                {[
                  "code",
                  "case",
                  "items",
                  "progress",
                  "state",
                  "sendoff",
                  "action",
                ].map((key) => (
                  <TableCell key={key}>
                    {t(`cases.list.columns.${key}`)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {list.data.map((item) => (
                <TableRow key={item.caseId}>
                  <TableCell component="th" scope="row">
                    {item.caseCode}
                  </TableCell>
                  <TableCell>
                    <Typography>
                      {item.title ?? t("common.notAvailable")}
                    </Typography>
                    <Typography variant="caption">
                      {item.customerName ?? t("common.notAvailable")}
                    </Typography>
                  </TableCell>
                  <TableCell>{t("common.notAvailable")}</TableCell>
                  <TableCell>
                    <Typography>
                      {t(`cases.progress.${item.progressStatus}`)}
                    </Typography>
                    <Box
                      sx={{ display: "flex", gap: `${tokens.spacing.s1}px` }}
                    >
                      {stages.map((stage, index) => (
                        <Box
                          key={stage}
                          sx={{
                            flex: 1,
                            borderTop: `${tokens.border.quoteWidth}px solid ${index <= stages.indexOf(item.progressStatus) ? tokens.colors.accent : tokens.colors.hair}`,
                            paddingTop: `${tokens.spacing.s1}px`,
                          }}
                        >
                          <Typography variant="caption">
                            {t(`cases.progress.stage.${stage}`)}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {t(`cases.list.states.${item.progressStatus}`)}
                  </TableCell>
                  <TableCell>
                    <Typography
                      sx={{
                        color:
                          item.latestSendoff === "approved"
                            ? tokens.colors.ok.main
                            : item.latestSendoff === "hold"
                              ? tokens.colors.warn.main
                              : tokens.colors.text,
                      }}
                    >
                      {item.latestSendoff
                        ? t(`cases.list.sendoffState.${item.latestSendoff}`)
                        : t("common.notAvailable")}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Button
                      component={Link}
                      href={`/cases/${item.caseId}/intake`}
                      variant="outlined"
                    >
                      {t("cases.list.intakeLink")}
                    </Button>
                    {item.latestVersionId !== null && (
                      <Button
                        component={Link}
                        href={`/cases/${item.caseId}/versions/${item.latestVersionId}`}
                        variant="outlined"
                      >
                        {t("cases.list.openCase")}
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      <Box>
        <Typography variant="body2">{t("cases.list.versionNote")}</Typography>
        <Typography variant="body2">{t("cases.list.itemsNote")}</Typography>
        <Typography variant="body2">{t("cases.list.footnote")}</Typography>
      </Box>
      <Dialog
        open={open}
        onClose={() => {
          if (!busy) setOpen(false);
        }}
        aria-labelledby="new-case-title"
        fullWidth
        maxWidth="sm"
      >
        <Box component="form" onSubmit={submit}>
          <DialogTitle id="new-case-title">
            {t("cases.newCaseDialog.title")}
          </DialogTitle>
          <DialogContent sx={{ display: "grid", gap }}>
            <TextField
              autoFocus
              label={t("cases.newCaseDialog.caseCodeLabel")}
              value={caseCode}
              onChange={(e) => setCaseCode(e.target.value)}
              disabled={busy}
              inputProps={{ "aria-required": true }}
            />
            <TextField
              label={t("cases.newCaseDialog.customerNameLabel")}
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              disabled={busy}
            />
            <TextField
              label={t("cases.newCaseDialog.titleLabel")}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={busy}
            />
            {error && (
              <Box role="alert">
                <Typography>{t(`cases.newCaseDialog.${error}`)}</Typography>
                {error === "duplicateError" && (
                  <Typography>
                    {t("cases.newCaseDialog.duplicateHint")}
                  </Typography>
                )}
              </Box>
            )}
            {busy && (
              <Typography role="status">
                {t("cases.newCaseDialog.pending")}
              </Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button disabled={busy} onClick={() => setOpen(false)}>
              {t("cases.newCaseDialog.cancel")}
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={busy || !caseCode.trim()}
            >
              {t("cases.newCaseDialog.submit")}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}
