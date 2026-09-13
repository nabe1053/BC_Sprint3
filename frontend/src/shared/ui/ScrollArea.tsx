"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.scroll`: 表を囲む枠。横スクロールはこの中だけで起こす。 */
export function ScrollArea({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        overflow: "auto",
        border: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
        borderRadius: `${tokens.radius.md}px`,
      }}
    >
      {children}
    </Box>
  );
}
