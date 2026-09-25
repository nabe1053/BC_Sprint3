"use client";
import {
  Box,
  Button,
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
  RecordsResponse,
} from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { itemQuestions, rowBounceComments, valueLabelKey } from "../model";
import { DimensionValue, ItemValue } from "./ItemValue";
import { BounceCommentCell } from "./BounceCommentCell";
export function ApprovalTable({
  items,
  questions,
  records,
  onOpen,
  onEvidence,
  onComment,
  busy,
}: {
  items: ItemCurrentResponse[];
  questions: QuestionResponse[];
  records: RecordsResponse;
  onOpen: (id: number) => void;
  onEvidence: (id: number) => void;
  onComment: (id: number, value: string) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const text = (value: string | null, state: string | null) => {
    const key = valueLabelKey(state);
    return key ? t(key) : (value ?? t("common.notAvailable"));
  };
  return (
    <TableContainer sx={{ maxWidth: "100%", overflowX: "auto" }}>
      <Table
        sx={{
          "& td, & th": {
            verticalAlign: "top",
            whiteSpace: "nowrap",
            borderColor: tokens.colors.hair,
          },
          // 確認事項の対応状況・要約は折り返して隣の列へはみ出さない（F-13）。
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
              "rowCode",
              "kind",
              "spec",
              "qty",
              "due",
              "group",
              "edits",
              "judgement",
              "evidence",
              "bounce",
            ].map((key) => (
              <TableCell key={key}>
                {t(`versions.approval.columns.${key}`)}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow
              key={item.itemId}
              tabIndex={0}
              aria-label={t("versions.approval.row.openLabel", {
                row: item.rowCode,
              })}
              onClick={(event) => {
                if (
                  !(event.target as HTMLElement).closest(
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
            >
              <TableCell>
                {item.rowCode}
                <Typography
                  variant="caption"
                  component="div"
                  sx={{
                    color: tokens.colors[item.rowMatch ? "ok" : "warn"].main,
                  }}
                >
                  {t(
                    `versions.approval.row.${item.rowMatch ? "matched" : "unmatched"}`,
                  )}
                </Typography>
              </TableCell>
              <TableCell>{item.kind}</TableCell>
              <TableCell>
                <DimensionValue
                  item={{ ...item, history: [] }}
                  dimension="od"
                />
                {" / "}
                <DimensionValue
                  item={{ ...item, history: [] }}
                  dimension="weight"
                />
                {" / "}
                <ItemValue value={item.grade} state={item.gradeState} />
                {" / "}
                <ItemValue
                  value={item.connection}
                  state={item.connectionState}
                />
                {" / "}
                <ItemValue
                  value={
                    [item.rangeClass, item.lengthValue, item.lengthUnit]
                      .filter(Boolean)
                      .join(" ") || null
                  }
                  state={item.lengthState}
                />
              </TableCell>
              <TableCell>
                <ItemValue
                  value={
                    [item.qtyValue, item.qtyUnit].filter(Boolean).join(" ") ||
                    null
                  }
                  state={item.qtyState}
                />
              </TableCell>
              <TableCell>
                <ItemValue value={item.dueRaw} state={item.dueState} />
              </TableCell>
              <TableCell>
                {item.groupCode ?? t("common.notAvailable")}
                {item.groupCode && (
                  <Typography variant="caption" component="div">
                    {t("versions.approval.row.noGroupSum")}
                  </Typography>
                )}
              </TableCell>
              <TableCell>
                {item.history
                  .filter((e) => e.undoneAt === null)
                  .map((e) => (
                    <Box key={e.editId}>
                      <Typography>
                        {t("versions.approval.row.edit", {
                          field: t(`versions.edit.fields.${e.field}`),
                          old: text(e.oldValue, e.oldState),
                          new: text(e.newValue, e.newState),
                        })}
                      </Typography>
                      <Typography variant="caption">
                        {e.reason}
                        {" / "}
                        {e.recordedBy}
                      </Typography>
                    </Box>
                  ))}
                {!item.history.some((e) => e.undoneAt === null) &&
                  t("common.notAvailable")}
              </TableCell>
              <TableCell className="wrap">
                {itemQuestions(item, questions).map((q) => (
                  <Box key={q.questionId}>
                    <Typography>
                      {t(
                        `versions.question.statuses.${q.latest?.status ?? "open"}`,
                      )}
                      {" / "}
                      <Box
                        component="span"
                        sx={{
                          color:
                            tokens.colors[
                              q.latest?.resolution === "resolved"
                                ? "ok"
                                : "warn"
                            ].main,
                        }}
                      >
                        {t(
                          `versions.question.resolutions.${q.latest?.resolution ?? "unresolved"}`,
                        )}
                      </Box>
                    </Typography>
                    {q.latest?.note && <Typography>{q.latest.note}</Typography>}
                    <Typography variant="caption">
                      {q.reason}
                      {q.latest && (
                        <>
                          {" / "}
                          {q.latest.recordedBy}
                        </>
                      )}
                    </Typography>
                  </Box>
                ))}
                {!itemQuestions(item, questions).length &&
                  t("common.notAvailable")}
              </TableCell>
              <TableCell>
                <Button onClick={() => onEvidence(item.itemId)}>
                  {t("versions.approval.row.evidence")}
                </Button>
              </TableCell>
              <TableCell>
                <BounceCommentCell
                  itemId={item.itemId}
                  rowCode={item.rowCode}
                  comments={rowBounceComments(records, item.itemId)}
                  onRecord={onComment}
                  busy={busy}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
