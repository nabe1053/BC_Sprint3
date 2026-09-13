"use client";
import { Box, Button, Drawer, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type {
  ItemCurrentResponse,
  QuestionResponse,
} from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import {
  caseLevelUnresolved,
  changeTags,
  hasChanges,
  itemQuestions,
  unresolvedQuestions,
} from "../model";
export function ApprovalListsDrawer({
  items,
  questions,
  itemId,
  onClose,
  onAll,
  onEvidence,
}: {
  items: ItemCurrentResponse[];
  questions: QuestionResponse[];
  itemId: number | null;
  onClose: () => void;
  onAll: () => void;
  onEvidence: (id: number) => void;
}) {
  const { t } = useTranslation(),
    selected = items.find((item) => item.itemId === itemId),
    scope =
      itemId === null ? items : items.filter((item) => item.itemId === itemId),
    changed = scope.filter((item) => hasChanges(item, questions)),
    unresolved = unresolvedQuestions(questions).filter(
      (q) => itemId === null || q.itemId === itemId,
    ),
    caseLevel = caseLevelUnresolved(questions).length;
  return (
    <Drawer
      anchor="right"
      open
      onClose={onClose}
      PaperProps={{
        role: "dialog",
        "aria-labelledby": "approval-lists-title",
        sx: {
          width: "min(600px,94vw)",
          padding: `${tokens.spacing.s5}px`,
          display: "block",
        },
      }}
    >
      <Box
        sx={{
          display: "grid",
          gap: `${tokens.spacing.s4}px`,
          overflowWrap: "anywhere",
        }}
      >
        <Typography id="approval-lists-title" variant="h2">
          {t(
            itemId === null
              ? "versions.approval.lists.title"
              : "versions.approval.lists.rowTitle",
            { row: selected?.rowCode },
          )}
        </Typography>
        <Button onClick={onClose}>{t("versions.approval.lists.close")}</Button>
        <Typography>
          {t(
            itemId === null
              ? "versions.approval.lists.description"
              : "versions.approval.lists.rowDescription",
            {
              total: items.length,
              changes:
                itemId === null
                  ? changed.length
                  : changed.reduce(
                      (n, item) => n + changeTags(item, questions).length,
                      0,
                    ),
              unresolved: unresolved.length,
            },
          )}
        </Typography>
        {itemId !== null && (
          <>
            {caseLevel > 0 && (
              <Typography sx={{ color: tokens.colors.warn.main }}>
                {t("versions.approval.lists.caseUnresolved", { caseLevel })}
              </Typography>
            )}
            <Box>
              <Button onClick={onAll}>
                {t("versions.approval.lists.openAll")}
              </Button>
              <Button onClick={() => onEvidence(itemId)}>
                {t("versions.approval.lists.openEvidence")}
              </Button>
            </Box>
          </>
        )}
        <Box>
          <Typography variant="h3">
            {t("versions.approval.lists.changesTitle", {
              total: changed.length,
            })}
          </Typography>
          {changed.length ? (
            changed.map((item) => (
              <Box
                key={item.itemId}
                sx={{
                  paddingBlock: `${tokens.spacing.s3}px`,
                  borderBottom: `${tokens.border.width}px solid ${tokens.colors.hair}`,
                }}
              >
                <Typography>{item.rowCode}</Typography>
                {changeTags(item, questions).map((tag) => (
                  <Typography key={tag} variant="caption" component="div">
                    {tag === "judged"
                      ? itemQuestions(item, questions)
                          .filter((q) => q.latest)
                          .map((q) =>
                            t("versions.approval.tags.judged", {
                              status: t(
                                `versions.question.statuses.${q.latest!.status}`,
                              ),
                              resolution: t(
                                `versions.question.resolutions.${q.latest!.resolution}`,
                              ),
                            }),
                          )
                          .join(" / ")
                      : t(`versions.approval.tags.${tag}`, {
                          group: item.groupCode,
                          total: item.history.filter((e) => e.undoneAt === null)
                            .length,
                        })}
                  </Typography>
                ))}
                {itemQuestions(item, questions).map((question) => (
                  <Typography key={question.questionId} variant="body2">
                    {question.reason}
                    {question.latest?.note && ` / ${question.latest.note}`}
                  </Typography>
                ))}
              </Box>
            ))
          ) : (
            <Typography>
              {t(
                itemId === null
                  ? "versions.approval.lists.noChanges"
                  : "versions.approval.lists.noRowChanges",
              )}
            </Typography>
          )}
        </Box>
        <Box>
          <Typography variant="h3">
            {t("versions.approval.lists.unresolvedTitle", {
              total: unresolved.length,
            })}
          </Typography>
          {unresolved.length ? (
            unresolved.map((q) => (
              <Box
                key={q.questionId}
                sx={{
                  paddingBlock: `${tokens.spacing.s3}px`,
                  borderBottom: `${tokens.border.width}px solid ${tokens.colors.hair}`,
                }}
              >
                <Typography>
                  {q.questionCode}
                  {" / "}
                  {items.find((item) => item.itemId === q.itemId)?.rowCode ??
                    t("versions.approval.lists.caseLevel")}
                </Typography>
                <Typography>{q.reason}</Typography>
                {q.candidates && <Typography>{q.candidates}</Typography>}
                <Typography sx={{ color: tokens.colors.warn.main }}>
                  {t(
                    `versions.question.statuses.${q.latest?.status ?? "open"}`,
                  )}
                  {" / "}
                  {t(
                    `versions.question.resolutions.${q.latest?.resolution ?? "unresolved"}`,
                  )}
                </Typography>
                {q.latest?.note && <Typography>{q.latest.note}</Typography>}
              </Box>
            ))
          ) : (
            <Typography>
              {t(
                itemId === null
                  ? "versions.approval.lists.noUnresolved"
                  : "versions.approval.lists.noRowUnresolved",
              )}
            </Typography>
          )}
        </Box>
        <Typography>{t("versions.approval.lists.unresolvedNote")}</Typography>
      </Box>
    </Drawer>
  );
}
