"use client";
import Link from "next/link";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { useInventory, useVersion } from "../hooks";
import { inventoryCounts } from "../model";
import { InventoryScopePanel } from "./InventoryScopePanel";
import { CoverageRecordPanel } from "./CoverageRecordPanel";
import { InventoryEntriesTable } from "./InventoryEntriesTable";
import { InventoryItemsTable } from "./InventoryItemsTable";
export function InventoryPage({
  caseId,
  versionId,
}: {
  caseId: number;
  versionId: number;
}) {
  const { t } = useTranslation();
  const inventory = useInventory(versionId),
    version = useVersion(versionId);
  const gap = `${tokens.spacing.s4}px`;
  const reload = () => {
    void Promise.all([inventory.refetch(), version.refetch()]);
  };
  const loading = inventory.isLoading || version.isLoading;
  const error = inventory.isError || version.isError;
  const missing = [inventory.error, version.error].some(
    (error) => error instanceof ApiError && error.status === 404,
  );
  const data = inventory.data,
    s = data?.summary;
  const pair = {
    display: "grid",
    gridTemplateColumns: {
      xs: "minmax(0, 1fr)",
      lg: "repeat(2, minmax(0, 1fr))",
    },
    gap,
    minWidth: 0,
  };
  return (
    <Box
      component="main"
      sx={{
        padding: `${tokens.spacing.s6}px`,
        display: "grid",
        gap,
        minWidth: 0,
      }}
    >
      <Box
        component="header"
        sx={{
          display: "flex",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap,
        }}
      >
        <Box>
          <Typography variant="h1">{t("versions.inventory.title")}</Typography>
          {s && (
            <Typography>
              {t("versions.inventory.description", {
                source: s.sourceItemCount,
                output: s.outputRowCount,
                split: s.splitEntryIds.length,
                excluded: s.excludedEntryIds.length,
                missing: s.unmappedEntryIds.length,
              })}
            </Typography>
          )}
        </Box>
        <Button
          component={Link}
          href={`/cases/${caseId}/versions/${versionId}`}
        >
          {t("versions.inventory.back")}
        </Button>
      </Box>
      <Box>
        <Typography sx={{ fontWeight: tokens.typography.weight.bold }}>
          {t("versions.inventory.noticeLead")}
        </Typography>
        <Typography>{t("versions.inventory.noticeBody")}</Typography>
      </Box>
      {loading ? (
        <Typography role="status">{t("common.loading")}</Typography>
      ) : error ? (
        <Box role="alert">
          <Typography>
            {t(
              missing
                ? "versions.inventory.notFound"
                : "versions.inventory.loadError",
            )}
          </Typography>
          {missing ? (
            <Button component={Link} href="/cases">
              {t("versions.back")}
            </Button>
          ) : (
            <Button variant="outlined" onClick={reload}>
              {t("versions.inventory.reload")}
            </Button>
          )}
        </Box>
      ) : (
        data &&
        version.data && (
          <>
            <Box sx={{ display: "flex", gap }}>
              <Typography>
                {t("versions.version", { number: version.data.versionNo })}
              </Typography>
              <Typography>
                {t(`versions.state.${version.data.currentState}`)}
              </Typography>
            </Box>
            <Box
              component="section"
              aria-label={t("versions.inventory.countsLabel")}
            >
              <Box
                component="dl"
                sx={{ display: "flex", flexWrap: "wrap", gap, margin: 0 }}
              >
                {Object.entries(inventoryCounts(data.summary)).map(
                  ([key, total]) => (
                    <Box key={key}>
                      <Typography component="dt" variant="caption">
                        {t(`versions.inventory.counts.${key}`)}
                      </Typography>
                      <Typography
                        component="dd"
                        sx={{
                          margin: 0,
                          fontWeight: tokens.typography.weight.bold,
                        }}
                      >
                        {total}
                      </Typography>
                    </Box>
                  ),
                )}
              </Box>
            </Box>
            {!data.entries.length && !data.items.length ? (
              <Box>
                <Typography>{t("versions.inventory.empty")}</Typography>
                <Button component={Link} href={`/cases/${caseId}/intake`}>
                  {t("versions.inventory.intake")}
                </Button>
              </Box>
            ) : (
              <>
                <Box sx={pair}>
                  <InventoryScopePanel entries={data.entries} />
                  <CoverageRecordPanel
                    versionId={versionId}
                    coverage={data.summary.coverage}
                    onReload={reload}
                  />
                </Box>
                <Box sx={pair}>
                  <InventoryEntriesTable data={data} />
                  <InventoryItemsTable data={data} />
                </Box>
              </>
            )}
          </>
        )
      )}
    </Box>
  );
}
