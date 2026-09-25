"use client";
import { useRouter } from "next/navigation";
import { Box, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { useCases } from "../hooks";

export type CaseSelectTarget = "items" | "inventory" | "approval";

const SUFFIX: Record<CaseSelectTarget, string> = {
  items: "",
  inventory: "/inventory",
  approval: "/approval",
};

/**
 * SCR-03/05/06 の対象案件セレクタ（F-14・memory AD-036 ③）。
 * 選んだ案件の最新の確定版の同じ画面へ移る。版の無い案件は選べない。
 */
export function CaseSelect({
  caseId,
  target,
}: {
  caseId: number;
  target: CaseSelectTarget;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const list = useCases();
  const cases = list.data ?? [];
  return (
    <Box sx={{ marginTop: `${tokens.spacing.s3}px` }}>
      <TextField
        select
        SelectProps={{ native: true }}
        InputLabelProps={{ shrink: true }}
        label={t("cases.select.label")}
        value={String(caseId)}
        disabled={list.isLoading || list.isError || !cases.length}
        onChange={(event) => {
          const next = cases.find(
            (item) => String(item.caseId) === event.target.value,
          );
          if (next?.latestVersionId)
            router.push(
              `/cases/${next.caseId}/versions/${next.latestVersionId}${SUFFIX[target]}`,
            );
        }}
      >
        {!cases.some((item) => item.caseId === caseId) && (
          <option value={String(caseId)}>
            {t(
              list.isLoading
                ? "cases.select.loadingOption"
                : "common.notAvailable",
            )}
          </option>
        )}
        {cases.map((item) => (
          <option
            key={item.caseId}
            value={String(item.caseId)}
            disabled={item.latestVersionId === null}
          >
            {item.latestVersionId === null
              ? t("cases.select.noVersion", {
                  code: item.caseCode,
                  title: item.title ?? "",
                })
              : t("cases.select.option", {
                  code: item.caseCode,
                  title: item.title ?? "",
                })}
          </option>
        ))}
      </TextField>
      {list.isError && (
        <Typography variant="body2" role="alert">
          {t("cases.select.error")}
        </Typography>
      )}
    </Box>
  );
}
