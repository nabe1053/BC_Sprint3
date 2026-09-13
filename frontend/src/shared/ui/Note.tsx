"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.note`: a100 面・左に鋼色の 3px 罫。注意書きの唯一の形。 */
export function Note({
  children,
  role,
}: {
  children: ReactNode;
  role?: string;
}) {
  return (
    <Box
      role={role}
      sx={{
        position: "relative",
        margin: `${tokens.spacing.s3}px 0`,
        padding: "10px 14px",
        border: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
        background: tokens.colors.a[100],
        borderRadius: `${tokens.radius.md}px`,
        borderLeft: `${tokens.border.quoteWidth}px solid ${tokens.colors.accent}`,
        fontSize: `${tokens.typography.size.fs3}px`,
        lineHeight: 1.7,
        color: tokens.colors.n[700],
        "& b": { color: tokens.colors.text },
      }}
    >
      {children}
    </Box>
  );
}
