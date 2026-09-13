"use client";
import { Box, Typography } from "@mui/material";
import { tokens } from "@/shared/theme/tokens";

/** モックの `.prog`: 「n/4 段階名」＋ 4 本のピップ。色を外しても段階名で判断できる。 */
export function ProgressPips({
  label,
  step,
  total,
  note,
}: {
  label: string;
  step: number;
  total: number;
  note?: string;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: "5px",
        whiteSpace: "nowrap",
      }}
    >
      <Typography
        component="b"
        sx={{
          fontWeight: tokens.typography.weight.semibold,
          fontSize: `${tokens.typography.size.fs3}px`,
          color: tokens.colors.text,
        }}
      >
        {label}
      </Typography>
      <Box
        aria-hidden="true"
        sx={{ display: "inline-flex", gap: "3px", margin: 0 }}
      >
        {Array.from({ length: total }, (_, index) => (
          <Box
            key={index}
            sx={{
              display: "block",
              width: "22px",
              height: "4px",
              borderRadius: "2px",
              background:
                index + 1 < step
                  ? tokens.colors.a[400]
                  : index + 1 === step
                    ? tokens.colors.accent
                    : tokens.colors.n[300],
            }}
          />
        ))}
      </Box>
      {note && (
        <Typography
          component="small"
          sx={{
            fontSize: `${tokens.typography.size.fs2}px`,
            color: tokens.colors.n[600],
            whiteSpace: "normal",
          }}
        >
          {note}
        </Typography>
      )}
    </Box>
  );
}
