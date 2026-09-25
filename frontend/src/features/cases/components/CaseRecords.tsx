"use client";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { formatDateTime } from "@/shared/lib/datetime";
import { tokens } from "@/shared/theme/tokens";
import { useCaseRecords } from "../hooks";
import { recordTimeline, type TimelineEntry } from "../model";

/** F-15: 案件一覧の行を展開したときの、最新版の記録一覧（新しい順）。 */
export function CaseRecords({
  caseCode,
  versionId,
}: {
  caseCode: string;
  versionId: number;
}) {
  const { t } = useTranslation();
  const records = useCaseRecords(versionId, true);
  const label = (entry: TimelineEntry) => {
    const value =
      entry.kind === "state"
        ? t(`cases.list.states.${entry.value}`)
        : entry.kind === "sendoff"
          ? t(`cases.list.sendoffState.${entry.value}`)
          : entry.kind === "judgement"
            ? t(`versions.question.resolutions.${entry.value}`)
            : null;
    return t(`cases.records.kinds.${entry.kind}`, { value });
  };
  if (records.isLoading)
    return <Typography role="status">{t("common.loading")}</Typography>;
  if (records.isError)
    return <Typography role="alert">{t("cases.records.error")}</Typography>;
  const rows = records.data ? recordTimeline(records.data) : [];
  if (!rows.length) return <Typography>{t("cases.records.empty")}</Typography>;
  return (
    <Box
      component="ol"
      aria-label={t("cases.records.listLabel", { code: caseCode })}
      sx={{
        margin: 0,
        paddingLeft: `${tokens.spacing.s6}px`,
        display: "grid",
        gap: `${tokens.spacing.s1}px`,
      }}
    >
      {rows.map((entry) => (
        <Box component="li" key={entry.key}>
          <Typography variant="body2">
            {t("cases.records.entry", {
              label: label(entry),
              by: entry.by,
              at: formatDateTime(entry.at),
            })}
            {entry.undone &&
              t("cases.records.undone", {
                by: entry.undone.by ?? t("common.notAvailable"),
                at: formatDateTime(entry.undone.at),
              })}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
