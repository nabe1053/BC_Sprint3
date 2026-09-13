"use client";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { VersionResponse } from "@/shared/api/generated/model";
import { Kpis, MetaList } from "@/shared/ui";
import { tokens } from "@/shared/theme/tokens";
import { ItemValue } from "./ItemValue";

/** モック SCR-03 の `.meta`（案件ヘッダ）と `.kpis`（7件数）。 */
export function VersionSummary({ version }: { version: VersionResponse }) {
  const { t } = useTranslation();
  const header = version.caseHeader;
  const dueNote = header
    ? [
        header.dueGranularity
          ? t(`versions.header.dueGranularity.${header.dueGranularity}`)
          : null,
        header.dueBasis
          ? t(`versions.header.dueBasis.${header.dueBasis}`)
          : null,
      ]
        .filter(Boolean)
        .join(" / ")
    : "";
  return (
    <>
      {header ? (
        <MetaList
          items={[
            {
              label: t("versions.header.inquiryNo"),
              value: (
                <ItemValue
                  value={header.inquiryNo}
                  state={header.inquiryNoState}
                />
              ),
            },
            {
              label: t("versions.header.customerName"),
              value: (
                <ItemValue
                  value={header.customerName}
                  state={header.customerNameState}
                />
              ),
            },
            {
              label: t("versions.header.due"),
              value: (
                <>
                  <ItemValue value={header.dueRaw} state={header.dueState} />
                  {dueNote && (
                    <Typography variant="caption" component="div">
                      {dueNote}
                    </Typography>
                  )}
                </>
              ),
            },
            {
              label: t("versions.header.place"),
              value: (
                <ItemValue value={header.placeRaw} state={header.placeState} />
              ),
            },
            {
              label: t("versions.header.incoterms"),
              value: (
                <ItemValue
                  value={header.incoterms}
                  state={header.incotermsState}
                />
              ),
            },
            {
              label: t("versions.header.quoteDeadline"),
              value: (
                <>
                  {header.quoteDeadlineRaw ??
                    header.quoteDeadlineAt ??
                    t("versions.values.not_stated")}
                  {header.quoteDeadlineTzState === "missing" && (
                    <Typography variant="caption" component="div">
                      {t("versions.header.tzMissing")}
                    </Typography>
                  )}
                </>
              ),
            },
            {
              label: t("versions.header.state"),
              value: (
                <>
                  {t("versions.version", { number: version.versionNo })} /{" "}
                  {t(`versions.state.${version.currentState}`)}
                  {!version.isComplete && (
                    <Typography variant="caption" component="div">
                      {t("versions.partial")}
                    </Typography>
                  )}
                </>
              ),
            },
          ]}
        />
      ) : (
        <Box sx={{ paddingBottom: `${tokens.spacing.s4}px` }}>
          <Typography>{t("versions.header.empty")}</Typography>
        </Box>
      )}
      <Kpis
        items={(
          [
            "itemCount",
            "questionItemCount",
            "tbaItemCount",
            "choiceGroupCount",
            "matchedCount",
            "editCount",
            "unresolvedCount",
          ] as const
        ).map((key) => ({
          label: t(`versions.counts.${key}`),
          value:
            key === "matchedCount"
              ? t("versions.counts.matched", {
                  count: version.counts.matchedCount,
                  total: version.counts.itemCount,
                })
              : version.counts[key],
          note:
            key === "editCount"
              ? t("versions.counts.editedItemCount", {
                  count: version.counts.editedItemCount,
                })
              : undefined,
        }))}
      />
    </>
  );
}
