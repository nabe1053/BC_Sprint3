"use client";
import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.meta`: 案件ヘッダの項目をラベル小・値大で横に並べる。 */
export function MetaList({
  items,
}: {
  items: readonly { label: string; value: ReactNode }[];
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: `${tokens.spacing.s3}px ${tokens.spacing.s8}px`,
        padding: `0 0 ${tokens.spacing.s4}px`,
        fontSize: `${tokens.typography.size.fs2}px`,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: tokens.colors.n[500],
      }}
    >
      {items.map((item) => (
        <Box key={item.label} component="div">
          {item.label}
          <Typography
            component="strong"
            sx={{
              display: "block",
              marginTop: "3px",
              fontSize: `${tokens.typography.size.fs4}px`,
              fontWeight: tokens.typography.weight.medium,
              letterSpacing: 0,
              textTransform: "none",
              color: tokens.colors.text,
            }}
          >
            {item.value}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
