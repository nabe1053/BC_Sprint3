"use client";
import type { ReactNode } from "react";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.panel`。角のレジストレーションマーク（製図の見当合わせ）が印。 */
const corner = {
  content: '""',
  position: "absolute",
  width: "11px",
  height: "11px",
  pointerEvents: "none",
  background:
    "linear-gradient(currentColor,currentColor) center/1px 100% no-repeat,linear-gradient(currentColor,currentColor) center/100% 1px no-repeat",
  color: `color-mix(in srgb,${tokens.colors.text} 55%,transparent)`,
} as const;

export function Panel({
  title,
  children,
  component = "article",
  sx,
}: {
  title?: ReactNode;
  children: ReactNode;
  component?: React.ElementType;
  sx?: object;
}) {
  return (
    <Box
      component={component}
      sx={{
        position: "relative",
        padding: `${tokens.spacing.s5}px`,
        border: `${tokens.border.width}px solid ${tokens.colors.divider}`,
        borderRadius: `${tokens.radius.lg}px`,
        background: tokens.colors.paper,
        boxShadow: tokens.shadow.sm,
        minWidth: 0,
        "&::before": { ...corner, top: "-6px", left: "-6px" },
        "&::after": { ...corner, bottom: "-6px", right: "-6px" },
        ...sx,
      }}
    >
      {title !== undefined && <PanelTitle>{title}</PanelTitle>}
      {children}
    </Box>
  );
}

/** モックの `h2`: 15px / 下罫 a200。 */
export function PanelTitle({ children }: { children: ReactNode }) {
  return (
    <Typography
      component="h2"
      sx={{
        fontSize: `${tokens.typography.size.fs5}px`,
        fontWeight: tokens.typography.weight.semibold,
        margin: `0 0 ${tokens.spacing.s3}px`,
        paddingBottom: "6px",
        borderBottom: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
      }}
    >
      {children}
    </Typography>
  );
}
