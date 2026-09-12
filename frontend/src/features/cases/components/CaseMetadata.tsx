"use client";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useCase } from "../hooks";
import { tokens } from "@/shared/theme/tokens";

/** #3が提供する案件メタだけを表示する。抽出前の納期等をサンプルで埋めない。 */
export function CaseMetadata({ caseId }: { caseId: number }) {
  const { t } = useTranslation();
  const query = useCase(caseId);
  return (
    <Box>
      <Typography variant="h2">{t("cases.metadata.title")}</Typography>
      {query.isLoading && <Typography>{t("common.loading")}</Typography>}
      {query.isError && (
        <Box role="alert">
          <Typography>
            {t(
              query.error?.status === 404
                ? "cases.metadata.notFound"
                : "cases.metadata.error",
            )}
          </Typography>
          <Button variant="outlined" onClick={() => void query.refetch()}>
            {t("common.reload")}
          </Button>
        </Box>
      )}
      {query.data && (
        <>
          <Box
            component="dl"
            sx={{ margin: 0, display: "grid", gap: `${tokens.spacing.s2}px` }}
          >
            {(
              [
                ["caseCode", query.data.caseCode],
                ["customerName", query.data.customerName],
                ["subject", query.data.title],
                ["due", null],
                ["place", null],
                ["quotationDue", null],
              ] as const
            ).map(([key, value]) => (
              <Box key={key}>
                <Typography component="dt" variant="caption">
                  {t(`cases.metadata.${key}`)}
                </Typography>
                <Typography component="dd" sx={{ margin: 0 }}>
                  {value ?? t("common.notAvailable")}
                </Typography>
              </Box>
            ))}
          </Box>
          <Typography variant="body2">
            {t("cases.metadata.unavailableNote")}
          </Typography>
        </>
      )}
    </Box>
  );
}
