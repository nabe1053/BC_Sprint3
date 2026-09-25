"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/**
 * 失敗・要確認の通知（F-16）。状態色は枠と文字にだけ使い、面は塗らない（design-guidelines）。
 * MUI の Alert は JS で色を演算するため oklch の状態色トークンを扱えず、使わない。
 * 状態は色だけで伝えず、必ず原因と直し方の文言を中に置く。
 */
export function StatusNotice({
  tone,
  children,
}: {
  tone: "danger" | "warn";
  children: ReactNode;
}) {
  const color = tokens.colors[tone];
  return (
    <Box
      role="alert"
      data-tone={tone}
      sx={{
        padding: `${tokens.spacing.s2}px ${tokens.spacing.s3}px`,
        border: `${tokens.border.width}px solid ${color.main}`,
        borderLeft: `${tokens.border.quoteWidth}px solid ${color.main}`,
        borderRadius: `${tokens.radius.md}px`,
        background: tokens.colors.paper,
        color: color[800],
        "& p": { color: "inherit" },
      }}
    >
      {children}
    </Box>
  );
}
