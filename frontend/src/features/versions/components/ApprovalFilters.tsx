"use client";
import { Box, Button, MenuItem, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { tokens } from "@/shared/theme/tokens";
import { approvalFilters, type ApprovalFilter } from "../model";
export function ApprovalFilters({
  value,
  onChange,
  shown,
  total,
  changes,
  unresolved,
  onLists,
}: {
  value: ApprovalFilter;
  onChange: (value: ApprovalFilter) => void;
  shown: number;
  total: number;
  changes: number;
  unresolved: number;
  onLists: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: `${tokens.spacing.s3}px`,
        alignItems: "center",
      }}
    >
      <TextField
        select
        label={t("versions.approval.filters.label")}
        value={value}
        onChange={(e) => onChange(e.target.value as ApprovalFilter)}
      >
        {approvalFilters.map((key) => (
          <MenuItem key={key} value={key}>
            {t(`versions.approval.filters.${key}`)}
          </MenuItem>
        ))}
      </TextField>
      <Typography role="status">
        {t("versions.approval.filters.shown", { shown, total })}
      </Typography>
      <Button variant="outlined" onClick={onLists}>
        {t("versions.approval.lists.open", { changes, unresolved })}
      </Button>
    </Box>
  );
}
