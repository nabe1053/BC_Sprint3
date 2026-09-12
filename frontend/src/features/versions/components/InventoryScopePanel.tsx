"use client";
import { Box, Button, Paper, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { InventoryEntryResponse } from "@/shared/api/generated/model";
import { getGetFileApiV1UiDocumentsDocumentIdFileGetUrl } from "@/shared/api/generated/ui";
import { apiBaseUrl } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { documentNames } from "../model";
export function InventoryScopePanel({
  entries,
}: {
  entries: InventoryEntryResponse[];
}) {
  const { t } = useTranslation();
  const gap = `${tokens.spacing.s4}px`;
  return (
    <Paper
      component="section"
      aria-label={t("versions.inventory.scope")}
      variant="outlined"
      sx={{
        padding: gap,
        display: "grid",
        gap,
        alignContent: "start",
        minWidth: 0,
      }}
    >
      <Typography variant="h2">{t("versions.inventory.scope")}</Typography>
      <Box
        component="ul"
        sx={{ margin: 0, paddingLeft: gap, display: "grid", gap }}
      >
        {documentNames(entries).map((name, index) => (
          <Box component="li" key={index} sx={{ overflowWrap: "anywhere" }}>
            <Typography component="span">
              {name ?? t("versions.inventory.unknownDocument")}
            </Typography>
            {[
              ...new Set(
                entries
                  .filter((entry) => entry.documentFileName === name)
                  .map((entry) => entry.documentId),
              ),
            ].map((id) => (
              <Button
                key={id}
                component="a"
                variant="text"
                href={`${apiBaseUrl}${getGetFileApiV1UiDocumentsDocumentIdFileGetUrl(id)}`}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={t("versions.inventory.openDocumentLabel", {
                  name: name ?? t("versions.inventory.unknownDocument"),
                })}
              >
                {t("versions.inventory.openDocument")}
              </Button>
            ))}
          </Box>
        ))}
      </Box>
      <Typography>{t("versions.inventory.scopeNote")}</Typography>
    </Paper>
  );
}
