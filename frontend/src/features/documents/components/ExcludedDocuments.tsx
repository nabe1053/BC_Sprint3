"use client";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { formatDateTime } from "@/shared/lib/datetime";
import { tokens } from "@/shared/theme/tokens";
import { useDocumentExclusions } from "../hooks";

/** F-16: 除外済みの資料と除外者・日時（開いたときだけ取得する）。 */
export function ExcludedDocuments({ caseId }: { caseId: number }) {
  const { t } = useTranslation();
  const list = useDocumentExclusions(caseId, true);
  if (list.isLoading)
    return <Typography role="status">{t("common.loading")}</Typography>;
  if (list.isError)
    return (
      <Typography role="alert">{t("documents.exclusion.loadError")}</Typography>
    );
  if (!list.data?.length)
    return <Typography>{t("documents.exclusion.empty")}</Typography>;
  return (
    <Box
      component="ul"
      aria-label={t("documents.exclusion.listLabel")}
      sx={{ margin: 0, paddingLeft: `${tokens.spacing.s6}px` }}
    >
      {list.data.map((row) => (
        <Typography component="li" variant="body2" key={row.documentId}>
          {t("documents.exclusion.entry", {
            name: row.fileName,
            by: row.recordedBy,
            at: formatDateTime(row.recordedAt),
          })}
        </Typography>
      ))}
    </Box>
  );
}
