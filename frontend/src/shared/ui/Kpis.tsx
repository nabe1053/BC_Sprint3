"use client";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.kpis`: a100 の帯に「小さなラベル＋大きな数値」を並べる。 */
export function Kpis({
  items,
}: {
  items: readonly {
    label: string;
    value: string | number;
    note?: string;
  }[];
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: `${tokens.spacing.s2}px ${tokens.spacing.s8}px`,
        padding: `${tokens.spacing.s3}px ${tokens.spacing.s4}px`,
        marginBottom: `${tokens.spacing.s3}px`,
        background: tokens.colors.a[100],
        border: `${tokens.border.width}px solid ${tokens.colors.a[200]}`,
        borderRadius: `${tokens.radius.md}px`,
        fontSize: `${tokens.typography.size.fs2}px`,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color: tokens.colors.n[500],
      }}
    >
      {items.map((item) => (
        <Box key={item.label} sx={{ whiteSpace: "nowrap" }}>
          {item.label}
          <Typography
            component="b"
            sx={{
              display: "block",
              margin: "2px 0 0",
              fontSize: `${tokens.typography.size.fs6}px`,
              fontWeight: tokens.typography.weight.semibold,
              letterSpacing: "-0.02em",
              color: tokens.colors.text,
              fontVariantNumeric: "tabular-nums",
              textTransform: "none",
            }}
          >
            {item.value}
          </Typography>
          {item.note && (
            <Typography
              component="small"
              sx={{
                display: "block",
                marginTop: "3px",
                fontSize: `${tokens.typography.size.fs2}px`,
                color: tokens.colors.n[600],
                textTransform: "none",
                letterSpacing: 0,
              }}
            >
              {item.note}
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  );
}
