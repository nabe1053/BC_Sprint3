"use client";
import {
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
import type { InventoryResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { muiColor } from "@/shared/theme/mui-color";
import { sortItems } from "../model";
export function InventoryItemsTable({ data }: { data: InventoryResponse }) {
  const { t } = useTranslation();
  const gap = `${tokens.spacing.s4}px`;
  return (
    <Paper
      component="section"
      variant="outlined"
      sx={{
        padding: gap,
        display: "grid",
        gap,
        minWidth: 0,
        alignContent: "start",
      }}
    >
      <Typography variant="h2">{t("versions.inventory.itemsTitle")}</Typography>
      <TableContainer>
        <Table
          aria-label={t("versions.inventory.itemsTitle")}
          sx={{
            minWidth: "100%",
            "& th, & td": { verticalAlign: "top" },
            "& th": { whiteSpace: "nowrap" },
          }}
        >
          <TableHead>
            <TableRow>
              {["rowCode", "sourceNo", "candidate", "sources", "state"].map(
                (key) => (
                  <TableCell key={key}>
                    {t(`versions.inventory.columns.${key}`)}
                  </TableCell>
                ),
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortItems(data.items).map((item) => (
              <TableRow key={item.itemId}>
                <TableCell component="th" scope="row">
                  {item.rowCode}
                </TableCell>
                <TableCell>{item.sourceNo}</TableCell>
                <TableCell sx={{ whiteSpace: "nowrap" }}>
                  {item.groupCode
                    ? `${item.groupCode} · ${item.candidateLabel ?? t("versions.values.empty")}`
                    : t("versions.values.empty")}
                </TableCell>
                <TableCell sx={{ whiteSpace: "nowrap" }}>
                  {item.sourceEntries.length
                    ? item.sourceEntries.map((entry) => (
                        <Typography key={entry.entryId}>
                          {t("versions.inventory.source", {
                            position: entry.position,
                            number:
                              entry.sourceNo ?? t("versions.values.empty"),
                          })}
                        </Typography>
                      ))
                    : t("versions.values.empty")}
                </TableCell>
                <TableCell sx={{ minWidth: `${tokens.spacing.s8 * 5}px` }}>
                  <Typography
                    sx={{
                      color: muiColor(
                        tokens.colors[item.hasSource ? "ok" : "warn"].main,
                      ),
                    }}
                  >
                    {t(
                      item.hasSource
                        ? "versions.inventory.hasSource"
                        : "versions.inventory.noSource",
                    )}
                  </Typography>
                  {data.summary.multiMappedItemIds.includes(item.itemId) && (
                    <Typography variant="caption" component="div">
                      {t("versions.inventory.multiMapped", {
                        total: item.sourceEntries.length,
                      })}
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!data.items.length && (
              <TableRow>
                <TableCell colSpan={5}>
                  {t("versions.inventory.none")}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography>
        {t("versions.inventory.itemsNote", {
          total: data.summary.orphanItemIds.length,
        })}
      </Typography>
    </Paper>
  );
}
