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
import { sortEntries, inventoryState } from "../model";
export function InventoryEntriesTable({ data }: { data: InventoryResponse }) {
  const { t } = useTranslation();
  const gap = `${tokens.spacing.s4}px`;
  const s = data.summary;
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
      <Typography variant="h2">
        {t("versions.inventory.entriesTitle")}
      </Typography>
      <TableContainer>
        <Table
          aria-label={t("versions.inventory.entriesTitle")}
          sx={{
            // 半幅パネルでも「対応」「状態」列が横スクロールの外に出ないよう、
            // 列幅を固定して抜粋・状態を折り返す（TEST-06 #3）。
            tableLayout: "fixed",
            width: "100%",
            "& th, & td": {
              verticalAlign: "top",
              whiteSpace: "normal",
              overflowWrap: "anywhere",
            },
          }}
        >
          <TableHead>
            <TableRow>
              {(
                [
                  ["position", "14%"],
                  ["sourceNo", "10%"],
                  ["excerpt", "36%"],
                  ["linkedItems", "12%"],
                  ["state", "28%"],
                ] as const
              ).map(([key, width]) => (
                <TableCell key={key} sx={{ width }}>
                  {t(`versions.inventory.columns.${key}`)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortEntries(data.entries).map((entry) => {
              const state = inventoryState(entry.judgement);
              return (
                <TableRow key={entry.entryId}>
                  <TableCell>{entry.position}</TableCell>
                  <TableCell>
                    {entry.sourceNo ?? t("versions.values.empty")}
                  </TableCell>
                  <TableCell>{entry.excerpt}</TableCell>
                  <TableCell>
                    {entry.linkedItems.map((item) => item.rowCode).join(", ") ||
                      t("versions.values.empty")}
                  </TableCell>
                  <TableCell>
                    <Typography
                      sx={
                        state.tone
                          ? { color: muiColor(tokens.colors[state.tone].main) }
                          : undefined
                      }
                    >
                      {t(state.key)}
                    </Typography>
                    <Typography variant="caption" component="div">
                      {t("versions.inventory.savedStatus", {
                        value:
                          entry.statusDetail ??
                          t(`versions.inventory.status.${entry.status}`),
                      })}
                    </Typography>
                    {entry.basis !== null && (
                      <Typography variant="caption" component="div">
                        {t("versions.inventory.basis", { value: entry.basis })}
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
            {!data.entries.length && (
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
        {t("versions.inventory.entriesNote", {
          source: s.sourceItemCount,
          output: s.outputRowCount,
          split: s.splitEntryIds.length,
          excluded: s.excludedEntryIds.length,
          missing: s.unmappedEntryIds.length,
        })}
      </Typography>
    </Paper>
  );
}
