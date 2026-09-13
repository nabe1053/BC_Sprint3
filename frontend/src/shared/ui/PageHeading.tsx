"use client";
import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.heading`: 眉ラベル（SCR-xx / 区分）＋ h1 ＋ 説明 ＋ 右にアクション、下罫 a200。 */
export function PageHeading({
  eyebrow,
  title,
  description,
  actions,
  after,
}: {
  eyebrow: string;
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
        <Typography
          component="span"
          sx={{
            display: "inline-block",
            fontFamily: tokens.typography.mono,
            fontSize: `${tokens.typography.size.fs1}px`,
            letterSpacing: tokens.typography.letterSpacing.caps,
            textTransform: "uppercase",
            color: tokens.colors.accent,
          }}
        >
          {eyebrow}
        </Typography>
        <Typography variant="h1" sx={{ margin: "6px 0 4px" }}>
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
