"use client";
import {
  Box,
  Button,
  Checkbox,
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
import type {
  ItemCurrentResponse,
  QuestionResponse,
} from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { muiColor } from "@/shared/theme/mui-color";
import { hasEdits, itemQuestions, rowState } from "../model";
import { DimensionValue, ItemValue } from "./ItemValue";
import {
  QuestionJudgementForm,
  type JudgementInput,
} from "./QuestionJudgementForm";
import { formatDateTime } from "@/shared/lib/datetime";
export function ItemTable({
  items,
  questions,
  recordedBy,
  onMatch,
  onOpen,
  onJudge,
  busy,
}: {
  items: ItemCurrentResponse[];
  questions: QuestionResponse[];
  recordedBy: string;
  onMatch: (item: ItemCurrentResponse) => void;
  onOpen: (itemId: number) => void;
  onJudge: (input: JudgementInput) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  return (
    <TableContainer
      component={Paper}
      variant="outlined"
      sx={{ maxWidth: "100%" }}
    >
      <Table
        aria-label={t("versions.title")}
        sx={{
          width: "max-content",
          minWidth: "100%",
          "& td, & th": { whiteSpace: "nowrap", verticalAlign: "top" },
          // 出典と照合の☑は横スクロールしても左端に残す（F-13）。
          // `:first-of-type` は行 ID の `th`（scope=row）にも当たるため class で指す。
          "& .sticky": {
            position: "sticky",
            left: 0,
            zIndex: tokens.z.sticky,
            background: tokens.colors.paper,
            borderRight: `${tokens.border.width}px solid ${tokens.colors.divider}`,
          },
          // 確認事項の要約・判断は折り返して隣の列へはみ出さない（F-13）。
          "& td.wrap": {
            whiteSpace: "normal",
            overflowWrap: "anywhere",
            minWidth: "16em",
            maxWidth: "24em",
          },
        }}
      >
        <TableHead>
          <TableRow>
            {[
              "match",
              "rowCode",
              "kind",
              "od",
              "weight",
              "grade",
              "connection",
              "length",
              "qtyValue",
              "qtyUnit",
              "due",
              "group",
              "state",
              "questions",
              "sourceNo",
              "status",
              "resolution",
              "note",
              "details",
            ].map((key) => (
              <TableCell
                key={key}
                className={key === "match" ? "sticky" : undefined}
                sx={{ whiteSpace: "nowrap" }}
              >
                {t(`versions.columns.${key}`)}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => {
            const qs = itemQuestions(item, questions);
            const state = rowState(item, questions);
            const value = (
              field: "kind" | "grade" | "connection" | "qty_value" | "qty_unit",
              value?: string | null,
              state?: string | null,
            ) => (
              <ItemValue
                value={value}
                state={state}
                field={field}
                history={item.history}
              />
            );
            return (
              <TableRow
                key={item.itemId}
                tabIndex={0}
                onClick={(event) => {
                  if (
                    !(event.target as Element).closest(
                      "button,a,input,select,textarea,label",
                    )
                  )
                    onOpen(item.itemId);
                }}
                onKeyDown={(event) => {
                  if (
                    event.target === event.currentTarget &&
                    (event.key === "Enter" || event.key === " ")
                  ) {
                    event.preventDefault();
                    onOpen(item.itemId);
                  }
                }}
                sx={{
                  "& td": { verticalAlign: "top" },
                  "&:focus-visible": {
                    outline: `${tokens.border.width}px solid ${tokens.colors.accent}`,
                  },
                }}
              >
                <TableCell className="sticky">
                  <Checkbox
                    checked={!!item.rowMatch}
                    disabled={busy}
                    onChange={() => onMatch(item)}
                    inputProps={{
                      "aria-label": t("versions.matchLabel", {
                        row: item.rowCode,
                      }),
                    }}
                  />
                  {item.rowMatch && (
                    <Typography variant="caption" component="div">
                      {t("versions.recorded", {
                        by: item.rowMatch.recordedBy,
                        at: formatDateTime(item.rowMatch.recordedAt),
                      })}
                    </Typography>
                  )}
                </TableCell>
                <TableCell component="th" scope="row">
                  {item.rowCode}
                </TableCell>
                <TableCell>{value("kind", item.kind)}</TableCell>
                <TableCell>
                  <DimensionValue item={item} dimension="od" />
                </TableCell>
                <TableCell>
                  <DimensionValue item={item} dimension="weight" />
                </TableCell>
                <TableCell>
                  {value("grade", item.grade, item.gradeState)}
                </TableCell>
                <TableCell>
                  {value("connection", item.connection, item.connectionState)}
                </TableCell>
                <TableCell>
                  <ItemValue
                    value={t("versions.values.length", {
                      range: item.rangeClass ?? t("versions.values.empty"),
                      length:
                        [item.lengthValue, item.lengthUnit]
                          .filter(Boolean)
                          .join(" ") || t("versions.values.empty"),
                    })}
                  />
                  <Typography variant="caption" component="div">
                    {t(`versions.values.${item.lengthState}`)}
                  </Typography>
                  {(
                    ["range_class", "length_value", "length_unit"] as const
                  ).map((field) => (
                    <Box key={field}>
                      <ItemValue
                        value=""
                        history={item.history}
                        field={field}
                      />
                    </Box>
                  ))}
                </TableCell>
                <TableCell>
                  {value("qty_value", item.qtyValue, item.qtyState)}
                </TableCell>
                <TableCell>
                  {value("qty_unit", item.qtyUnit, item.qtyState)}
                </TableCell>
                <TableCell>
                  <ItemValue value={item.dueRaw} state={item.dueState} />
                </TableCell>
                <TableCell>
                  {item.groupCode ?? t("versions.values.empty")}
                  <Typography variant="caption">
                    {item.candidateLabel}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography
                    sx={{ color: muiColor(tokens.colors[state.tone].main) }}
                  >
                    {t(state.key)}
                  </Typography>
                  {hasEdits(item) && (
                    <Typography>{t("versions.rowState.edited")}</Typography>
                  )}
                  <Typography>
                    {t(
                      item.rowMatch
                        ? "versions.rowState.matched"
                        : "versions.rowState.unmatched",
                    )}
                  </Typography>
                </TableCell>
                <TableCell className="wrap">
                  {qs.length
                    ? qs.map((q) => (
                        <Typography key={q.questionId}>
                          {t("versions.questionSummary", {
                            code: q.questionCode,
                            reason: q.reason,
                          })}
                        </Typography>
                      ))
                    : t("versions.noQuestions")}
                </TableCell>
                <TableCell>{item.sourceNo}</TableCell>
                <TableCell colSpan={3} className="wrap">
                  {qs.map((q) => (
                    <QuestionJudgementForm
                      key={q.questionId}
                      question={q}
                      showReason={false}
                      recordedBy={recordedBy}
                      onRecord={onJudge}
                      busy={busy}
                    />
                  ))}
                </TableCell>
                <TableCell>
                  <Button
                    variant="outlined"
                    onClick={() => onOpen(item.itemId)}
                  >
                    {t("versions.details")}
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
