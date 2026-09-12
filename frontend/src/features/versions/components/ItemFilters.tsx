"use client";
import { Box, Button, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { ItemCurrentResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { emptyFilters, filterStates, type Filters } from "../model";
export function ItemFilters({
  items,
  filters,
  onChange,
  count,
}: {
  items: ItemCurrentResponse[];
  filters: Filters;
  onChange: (filters: Filters) => void;
  count: number;
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
        InputLabelProps={{ shrink: true }}
        label={t("versions.filters.keyword")}
        value={filters.keyword}
        onChange={(event) =>
          onChange({ ...filters, keyword: event.target.value })
        }
      />
      {(["kind", "grade", "connection"] as const).map((field) => (
        <TextField
          InputLabelProps={{ shrink: true }}
          key={field}
          select
          SelectProps={{ native: true }}
          label={t(`versions.filters.${field}`)}
          value={filters[field]}
          onChange={(event) =>
            onChange({ ...filters, [field]: event.target.value })
          }
        >
          <option value="">{t("versions.filters.all")}</option>
          {Array.from(
            new Set(
              items.map((item) => item[field]).filter((v): v is string => !!v),
            ),
          )
            .sort()
            .map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
        </TextField>
      ))}
      <TextField
        InputLabelProps={{ shrink: true }}
        select
        SelectProps={{ native: true }}
        label={t("versions.filters.status")}
        value={filters.status}
        onChange={(event) =>
          onChange({
            ...filters,
            status: event.target.value as Filters["status"],
          })
        }
      >
        {filterStates.map((status) => (
          <option key={status} value={status}>
            {t(`versions.filters.${status}`)}
          </option>
        ))}
      </TextField>
      <Button variant="outlined" onClick={() => onChange({ ...emptyFilters })}>
        {t("versions.filters.clear")}
      </Button>
      <Typography>
        {t("versions.filters.count", { count, total: items.length })}
      </Typography>
    </Box>
  );
}
