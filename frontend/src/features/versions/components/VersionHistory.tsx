"use client";
import Link from "next/link";
import {
  Box,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { AgentRunPanel } from "@/features/agent-runs";
import { tokens } from "@/shared/theme/tokens";
import { Note, Pill, Popover, ScrollArea } from "@/shared/ui";
import { useExports, useVersionHistory } from "../hooks";
import { findVersionListItem, integrityLabelKey } from "../model";
import { ExportButton } from "./ExportButton";

const gap = `${tokens.spacing.s3}px`;

/** モック SCR-03 の `.ver`（版の履歴ポップオーバー）。 */
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
  const versions = history.data ?? [];
  return (
    <Popover
      summary={t("versions.history.summary", { count: versions.length })}
    >
      {history.isLoading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : history.isError ? (
        <Box role="alert">
          <Typography>{t("versions.loadError")}</Typography>
          <Button onClick={() => void history.refetch()}>
            {t("versions.reload")}
          </Button>
        </Box>
      ) : (
        <ScrollArea>
          <Table aria-label={t("versions.history.title")}>
            <TableHead>
              <TableRow>
                {[
                  "version",
                  "createdAt",
                  "elapsed",
                  "state",
                  "unresolvedShort",
                  "export",
                ].map((key) => (
                  <TableCell key={key}>
                    {t(`versions.history.columns.${key}`)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {versions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6}>
                    {t("versions.history.empty")}
                  </TableCell>
                </TableRow>
              ) : (
                versions.map((version) => (
                  <TableRow key={version.versionId}>
                    <TableCell>
                      <Box
                        component={Link}
                        href={`/cases/${caseId}/versions/${version.versionId}`}
                        aria-current={
                          version.versionId === versionId ? "page" : undefined
                        }
                      >
                        {t("versions.history.open", {
                          number: version.versionNo,
                        })}
                      </Box>
                      {version.versionId === versionId && (
                        <Typography component="small">
                          {t("versions.history.current")}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{version.finalizedAt}</TableCell>
                    <TableCell>
                      {version.elapsedSec === null
                        ? t("versions.history.elapsedUnrecorded")
                        : t("versions.history.elapsedSeconds", {
                            seconds: version.elapsedSec,
                          })}
                      <Typography component="small">
                        {t("versions.history.elapsedNote")}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {t(`versions.state.${version.currentState}`)}
                      <Typography component="small">
                        {t("versions.export.sendoffShort", {
                          state: t(
                            `versions.export.sendoff.${version.latestSendoff?.decision ?? "undecided"}`,
                          ),
                        })}
                      </Typography>
                    </TableCell>
                    <TableCell>{version.unresolvedCount}</TableCell>
                    <TableCell>
                      <ExportButton
                        versionId={version.versionId}
                        label={t("versions.export.versionButton", {
                          number: version.versionNo,
                        })}
                      />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      )}
      <Box
        sx={{ display: "flex", flexWrap: "wrap", gap, alignItems: "center" }}
      >
        <AgentRunPanel
          caseId={caseId}
          blockedReason={null}
          emphasis="secondary"
        />
        <Button component={Link} href={`/cases/${caseId}/intake`}>
          {t("versions.intake")}
        </Button>
      </Box>
      <Typography variant="body2">
        {t("versions.history.carryOverWarning")}
      </Typography>
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
      <Box>
        <Typography component="h3" variant="body2">
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
          <Typography variant="body2">
            {t("versions.export.history.empty")}
          </Typography>
        ) : (
          exports.data.map((record) => (
            <Box
              key={record.exportId}
              sx={{ display: "flex", flexWrap: "wrap", gap }}
            >
              <Typography variant="body2">
                {`${t("versions.export.history.fileName")}: ${record.fileName}`}
              </Typography>
              <Typography variant="body2">
                {`${t("versions.export.history.exportedAt")}: ${record.exportedAt}`}
              </Typography>
              <Typography variant="body2">
                {`${t("versions.export.history.stateAtExport")}: ${t(
                  `versions.state.${record.stateAtExport}`,
                )}`}
              </Typography>
              <Typography variant="body2">
                {`${t("versions.export.history.unresolvedAtExport")}: ${
                  record.unresolvedAtExport
                }`}
              </Typography>
              <Typography variant="body2">
                {t(
                  record.isInitial
                    ? "versions.export.history.initial"
                    : "versions.export.history.reexport",
                )}
              </Typography>
              <Typography variant="body2">
                {`${t("versions.export.history.integrity")}: ${t(
                  integrityLabelKey(record.integrity),
                )}`}
              </Typography>
            </Box>
          ))
        )}
      </Box>
      <Note>{t("versions.history.compareNote")}</Note>
      <Box sx={{ display: "flex", gap, alignItems: "center" }}>
        <Pill tone="neutral">{t("versions.history.scope2")}</Pill>
        <Button disabled>{t("versions.history.compare")}</Button>
      </Box>
    </Popover>
  );
}
