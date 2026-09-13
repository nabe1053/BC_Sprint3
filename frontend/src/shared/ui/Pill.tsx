"use client";
import type { ReactNode } from "react";
import { Box } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

export type Tone = "default" | "accent" | "ok" | "warn" | "danger" | "neutral";

const toneStyle: Record<
  Tone,
  { background: string; color: string; border?: string }
> = {
  default: { background: tokens.colors.n[200], color: tokens.colors.n[800] },
  accent: { background: tokens.colors.a[100], color: tokens.colors.a[800] },
  ok: { background: tokens.colors.ok[100], color: tokens.colors.ok[800] },
  warn: { background: tokens.colors.warn[100], color: tokens.colors.warn[800] },
  danger: {
    background: tokens.colors.danger[100],
    color: tokens.colors.danger[800],
  },
  neutral: {
    background: "transparent",
    color: tokens.colors.n[600],
    border: tokens.colors.divider,
  },
};

/** モックの `.pill`。色は文字ラベルの補助であり、単独で情報を伝えない。 */
export function Pill({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  const style = toneStyle[tone];
  return (
    <Box
      component="span"
      sx={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: `${tokens.radius.sm}px`,
        fontSize: `${tokens.typography.size.fs2}px`,
        letterSpacing: tokens.typography.letterSpacing.tight,
        lineHeight: 1.5,
        whiteSpace: "nowrap",
        background: style.background,
        color: style.color,
        border: `${tokens.border.width}px solid ${style.border ?? "transparent"}`,
      }}
    >
      {children}
    </Box>
  );
}
