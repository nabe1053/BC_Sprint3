"use client";
import Link from "next/link";
import { Box, Button, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { AgentRunPanel } from "@/features/agent-runs";
import { tokens } from "@/shared/theme/tokens";
import { useExports, useVersionHistory } from "../hooks";
import { findVersionListItem, integrityLabelKey } from "../model";
import { ExportButton } from "./ExportButton";

export function VersionHistory({
  caseId,
  versionId,
}: {
  caseId: number;
  versionId: number;
}) {
  const { t } = useTranslation();
  const history = useVersionHistory(caseId);
  const exports = useExports(versionId);
  const current = findVersionListItem(history.data ?? [], versionId);
  const gap = `${tokens.spacing.s3}px`;
  return (
    <Box component="details">
      <Typography component="summary">{t("versions.history.title")}</Typography>
      {history.isLoading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : history.isError ? (
        <Box role="alert">
          <Typography>{t("versions.loadError")}</Typography>
          <Button onClick={() => void history.refetch()}>
            {t("versions.reload")}
          </Button>
        </Box>
      ) : !history.data?.length ? (
        <Typography>{t("versions.history.empty")}</Typography>
      ) : (
        <>
          <Typography variant="body2">
            {t("versions.history.elapsedNote")}
          </Typography>
          {history.data.map((version) => (
            <Box
              key={version.versionId}
              sx={{
                display: "flex",
                flexWrap: "wrap",
                gap,
                alignItems: "center",
              }}
            >
              <Button
                component={Link}
                href={`/cases/${caseId}/versions/${version.versionId}`}
                aria-current={
                  version.versionId === versionId ? "page" : undefined
                }
              >
                {t("versions.history.open", { number: version.versionNo })}
              </Button>
              <Typography>
                {`${t("versions.history.createdAt")}: ${version.finalizedAt}`}
              </Typography>
              <Typography>
                {`${t("versions.history.elapsed")}: ${
                  version.elapsedSec === null
                    ? t("versions.history.elapsedUnrecorded")
                    : t("versions.history.elapsedSeconds", {
                        seconds: version.elapsedSec,
                      })
                }`}
              </Typography>
              <Typography>
                {`${t("versions.history.state")}: ${t(
                  `versions.state.${version.currentState}`,
                )}`}
              </Typography>
              <Typography>
                {t("versions.history.unresolved", {
                  count: version.unresolvedCount,
                })}
              </Typography>
              <ExportButton
                versionId={version.versionId}
                label={t("versions.export.versionButton", {
                  number: version.versionNo,
                })}
              />
              {version.versionId === versionId && (
                <Typography>{t("versions.history.current")}</Typography>
              )}
            </Box>
          ))}
        </>
      )}
      <Paper variant="outlined" sx={{ padding: gap, display: "grid", gap }}>
        <Typography component="h2">
          {t("versions.export.history.title")}
        </Typography>
        {exports.isLoading ? (
          <Typography role="status">{t("common.loading")}</Typography>
        ) : exports.isError ? (
          <Box role="alert">
            <Typography>{t("versions.export.history.loadError")}</Typography>
            <Button onClick={() => void exports.refetch()}>
              {t("versions.reload")}
            </Button>
          </Box>
        ) : !exports.data?.length ? (
          <Typography>{t("versions.export.history.empty")}</Typography>
        ) : (
          exports.data.map((record) => (
            <Box
              key={record.exportId}
              sx={{ display: "flex", flexWrap: "wrap", gap }}
            >
              <Typography>
                {`${t("versions.export.history.fileName")}: ${record.fileName}`}
              </Typography>
              <Typography>
                {`${t("versions.export.history.exportedAt")}: ${record.exportedAt}`}
              </Typography>
              <Typography>
                {`${t("versions.export.history.stateAtExport")}: ${t(
                  `versions.state.${record.stateAtExport}`,
                )}`}
              </Typography>
              <Typography>
                {`${t("versions.export.history.unresolvedAtExport")}: ${
                  record.unresolvedAtExport
                }`}
              </Typography>
              <Typography>
                {t(
                  record.isInitial
                    ? "versions.export.history.initial"
                    : "versions.export.history.reexport",
                )}
              </Typography>
              <Typography>
                {`${t("versions.export.history.integrity")}: ${t(
                  integrityLabelKey(record.integrity),
                )}`}
              </Typography>
            </Box>
          ))
        )}
      </Paper>
      {current && (
        <Typography variant="body2">
          {t("versions.export.currentStateNote", {
            state: t(`versions.state.${current.currentState}`),
            sendoff: t(
              `versions.export.sendoff.${current.latestSendoff?.decision ?? "undecided"}`,
            ),
          })}
        </Typography>
      )}
      {current && current.unresolvedCount > 0 && (
        <Typography variant="body2">
          {t("versions.export.unresolvedNote", {
            count: current.unresolvedCount,
          })}
        </Typography>
      )}
      <Typography variant="body2">{t("versions.export.sheets")}</Typography>
      <Typography variant="body2">
        {t("versions.export.sampleFormat")}
      </Typography>
      <Typography variant="body2">{t("versions.export.snapshot")}</Typography>
      <Typography variant="body2">
        {t("versions.history.carryOverWarning")}
      </Typography>
      <AgentRunPanel
        caseId={caseId}
        blockedReason={null}
        emphasis="secondary"
      />
      <Button component={Link} href={`/cases/${caseId}/intake`}>
        {t("versions.intake")}
      </Button>
      <Box>
        <Button disabled>{t("versions.history.compare")}</Button>
        <Typography variant="body2">
          {t("versions.history.compareNote")}
        </Typography>
      </Box>
    </Box>
  );
}
