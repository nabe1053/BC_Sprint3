"use client";
import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.heading`: h1 ＋ 説明 ＋ 右にアクション、下罫 a200（画面 ID の眉ラベルは出さない。memory AD-036 ⑤）。 */
export function PageHeading({
  title,
  description,
  actions,
  after,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  after?: ReactNode;
}) {
  return (
    <Box
      component="header"
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: `${tokens.spacing.s5}px`,
        margin: `0 0 ${tokens.spacing.s5}px`,
        paddingBottom: `${tokens.spacing.s4}px`,
        borderBottom: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
        flexWrap: "wrap",
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="h1" sx={{ margin: "0 0 4px" }}>
          {title}
        </Typography>
        {description !== undefined && (
          <Typography sx={{ color: tokens.colors.n[800] }}>
            {description}
          </Typography>
        )}
        {after}
      </Box>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: `${tokens.spacing.s2}px`,
          alignItems: "center",
          justifyContent: "flex-end",
        }}
      >
        {actions}
      </Box>
    </Box>
  );
}
