"use client";
import { Box, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { VersionListItem } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { formatDateTime } from "@/shared/lib/datetime";
export function BounceBanner({ item }: { item: VersionListItem }) {
  const { t } = useTranslation();
  return (
    <>
      {item.bounced && item.latestBounce && (
        <Box>
          <Typography sx={{ color: tokens.colors.warn.main }}>
            {t("versions.staffCheck.bounced")}
          </Typography>
          <Typography variant="caption">
            {t("versions.staffCheck.bouncedBy", {
              by: item.latestBounce.recordedBy,
              at: formatDateTime(item.latestBounce.recordedAt),
            })}
          </Typography>
          {item.latestBounce.reason.split("\n").map((line, index) => (
            <Box
              component="blockquote"
              key={index}
              sx={{
                margin: 0,
                padding: `${tokens.spacing.s3}px`,
                borderLeft: `${tokens.border.quoteWidth}px solid ${tokens.colors.accent}`,
                overflowWrap: "anywhere",
              }}
            >
              {line}
            </Box>
          ))}
        </Box>
      )}
      {item.needsRecheck && (
        <Typography sx={{ color: tokens.colors.warn.main }}>
          {t("versions.staffCheck.needsRecheck")}
        </Typography>
      )}
    </>
  );
}
