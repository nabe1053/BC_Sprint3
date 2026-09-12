"use client";
import { Box, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { VersionResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { ItemValue } from "./ItemValue";
const gap = `${tokens.spacing.s4}px`;
export function VersionSummary({ version }: { version: VersionResponse }) {
  const { t } = useTranslation();
  const header = version.caseHeader;
  return (
    <>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap }}>
        <Typography>
          {t("versions.version", { number: version.versionNo })}
        </Typography>
        <Typography>{t(`versions.state.${version.currentState}`)}</Typography>
        {!version.isComplete && (
          <Typography>{t("versions.partial")}</Typography>
        )}
      </Box>
      <Paper variant="outlined" sx={{ padding: gap }}>
        <Typography variant="h2">{t("versions.header.title")}</Typography>
        {header ? (
          <Box
            component="dl"
            sx={{ display: "flex", flexWrap: "wrap", gap, margin: 0 }}
          >
            {(
              [
                ["inquiryNo", header.inquiryNo, header.inquiryNoState],
                ["customerName", header.customerName, header.customerNameState],
                ["due", header.dueRaw, header.dueState],
                ["place", header.placeRaw, header.placeState],
                ["incoterms", header.incoterms, header.incotermsState],
              ] as const
            ).map(([key, value, state]) => (
              <Box key={key}>
                <Typography component="dt" variant="caption">
                  {t(`versions.header.${key}`)}
                </Typography>
                <Box component="dd" sx={{ margin: 0 }}>
                  <ItemValue value={value} state={state} />
                  {key === "due" && (
                    <Typography variant="caption" component="div">
                      {[
                        header.dueGranularity
                          ? t(
                              `versions.header.dueGranularity.${header.dueGranularity}`,
                            )
                          : null,
                        header.dueBasis
                          ? t(`versions.header.dueBasis.${header.dueBasis}`)
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" / ")}
                    </Typography>
                  )}
                </Box>
              </Box>
            ))}
            <Box>
              <Typography component="dt" variant="caption">
                {t("versions.header.quoteDeadline")}
              </Typography>
              <Typography component="dd" sx={{ margin: 0 }}>
                {header.quoteDeadlineRaw ??
                  header.quoteDeadlineAt ??
                  t("versions.values.not_stated")}
              </Typography>
              {header.quoteDeadlineTzState === "missing" && (
                <Typography variant="caption">
                  {t("versions.header.tzMissing")}
                </Typography>
              )}
            </Box>
          </Box>
        ) : (
          <Typography>{t("versions.header.empty")}</Typography>
        )}
      </Paper>
      <Box
        component="dl"
        sx={{ display: "flex", flexWrap: "wrap", gap, margin: 0 }}
      >
        {(
          [
            "itemCount",
            "questionItemCount",
            "tbaItemCount",
            "choiceGroupCount",
            "matchedCount",
            "editCount",
            "unresolvedCount",
          ] as const
        ).map((key) => (
          <Box key={key}>
            <Typography component="dt" variant="caption">
              {t(`versions.counts.${key}`)}
            </Typography>
            <Typography component="dd" variant="h2" sx={{ margin: 0 }}>
              {key === "matchedCount"
                ? t("versions.counts.matched", {
                    count: version.counts.matchedCount,
                    total: version.counts.itemCount,
                  })
                : version.counts[key]}
            </Typography>
            {key === "editCount" && (
              <Typography variant="caption">
                {t("versions.counts.editedItemCount", {
                  count: version.counts.editedItemCount,
                })}
              </Typography>
            )}
          </Box>
        ))}
      </Box>
    </>
  );
}
