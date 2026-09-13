"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

const { colors, spacing, radius, shadow, border, typography, z } = tokens;

/** モックの `.ver`: 見出し右に置く開閉パネル。開くと右寄せで浮く。 */
export function Popover({
  summary,
  children,
}: {
  summary: ReactNode;
  children: ReactNode;
}) {
  return (
    <Box
      component="details"
      sx={{
        position: "relative",
        "&[open] > summary::after": { content: '"▴"' },
      }}
    >
      <Box
        component="summary"
        sx={{
          listStyle: "none",
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          padding: "7px 12px",
          border: `${border.width}px solid ${colors.divider}`,
          borderRadius: `${radius.md}px`,
          fontSize: `${typography.size.fs4}px`,
          fontWeight: typography.weight.medium,
          whiteSpace: "nowrap",
          cursor: "pointer",
          "&::-webkit-details-marker": { display: "none" },
          "&::after": {
            content: '"▾"',
            fontSize: `${typography.size.fs1}px`,
            color: colors.n[600],
          },
          "&:hover": {
            background: `color-mix(in srgb,${colors.text} 7%,transparent)`,
          },
        }}
      >
        {summary}
      </Box>
      <Box
        sx={{
          position: "absolute",
          right: 0,
          top: "calc(100% + 8px)",
          zIndex: z.pop,
          width: "min(640px,86vw)",
          padding: `${spacing.s4}px`,
          textAlign: "left",
          background: colors.paper,
          borderRadius: `${radius.lg}px`,
          border: `${border.width}px solid ${colors.divider}`,
          boxShadow: shadow.lg,
          display: "grid",
          gap: `${spacing.s2}px`,
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
