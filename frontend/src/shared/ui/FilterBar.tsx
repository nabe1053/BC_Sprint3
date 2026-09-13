"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.column-filters`: a100 の帯にラベル付きの入力を並べる。 */
export function FilterBar({
  children,
  component = "div",
  ...rest
}: {
  children: ReactNode;
  component?: React.ElementType;
  [key: string]: unknown;
}) {
  return (
    <Box
      component={component}
      {...rest}
      sx={{
        display: "flex",
        alignItems: "flex-end",
        flexWrap: "wrap",
        gap: `${tokens.spacing.s2}px ${tokens.spacing.s3}px`,
        padding: `${tokens.spacing.s3}px`,
        margin: `${tokens.spacing.s2}px 0`,
        background: tokens.colors.a[100],
        border: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
        borderRadius: `${tokens.radius.md}px`,
      }}
    >
      {children}
    </Box>
  );
}
