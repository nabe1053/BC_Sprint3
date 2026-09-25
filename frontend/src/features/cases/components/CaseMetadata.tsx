"use client";
import {
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { useCase } from "../hooks";
import { tokens } from "@/shared/theme/tokens";

/** #3が提供する案件メタだけを表示する。抽出前の納期等をサンプルで埋めない。 */
export function CaseMetadata({ caseId }: { caseId: number }) {
  const { t } = useTranslation();
  const query = useCase(caseId);
  return (
    <Box sx={{ display: "grid", gap: `${tokens.spacing.s2}px` }}>
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
          <TableContainer component={Paper} variant="outlined">
            <Table
              size="small"
              aria-label={t("cases.metadata.title")}
              sx={{
                // 項目名（左列）と値（右列）を罫線と面の濃淡で区別する。罫線は hair の1段。
                "& th": {
                  width: "40%",
                  backgroundColor: tokens.colors.surface,
                  borderRight: `${tokens.border.width}px solid ${tokens.colors.hair}`,
                },
                "& tr:last-child th, & tr:last-child td": { borderBottom: 0 },
              }}
            >
              <TableBody>
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
                  <TableRow key={key}>
                    <TableCell component="th" scope="row">
                      {t(`cases.metadata.${key}`)}
                    </TableCell>
                    <TableCell sx={{ overflowWrap: "anywhere" }}>
                      {value ?? t("common.notAvailable")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="body2">
            {t("cases.metadata.unavailableNote")}
          </Typography>
        </>
      )}
    </Box>
  );
}
