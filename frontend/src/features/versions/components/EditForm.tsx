"use client";
import { useState } from "react";
import { Box, Button, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { ItemEditRequest } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import {
  buildEditRequest,
  editableFields,
  hasValueState,
  isQuantityField,
  recordErrorKey,
  type EditDraft,
} from "../model";
export function EditForm({
  itemId,
  recordedBy,
  onRecord,
  busy,
}: {
  itemId: number;
  recordedBy: string;
  onRecord: (input: ItemEditRequest) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<EditDraft>({
    field: "grade",
    state: "stated",
    value: "",
    qtyUnit: "",
    reason: "",
    recordedBy,
  });
  const [error, setError] = useState<string | null>(null);
  const valueState = isQuantityField(draft.field) ? "numeric" : "stated";
  const needsValue = !hasValueState(draft.field) || draft.state === valueState;
  const field = (key: keyof EditDraft, value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));
  return (
    <Box
      component="form"
      onSubmit={async (event) => {
        event.preventDefault();
        if (busy) return;
        setError(null);
        try {
          const request = buildEditRequest(itemId, draft);
          if (await onRecord(request))
            setDraft((current) => ({ ...current, reason: "" }));
        } catch (cause) {
          setError(recordErrorKey(cause));
        }
      }}
      sx={{ display: "grid", gap: `${tokens.spacing.s3}px` }}
    >
      <Typography variant="h3">{t("versions.edit.title")}</Typography>
      <TextField
        InputLabelProps={{ shrink: true }}
        select
        SelectProps={{ native: true }}
        label={t("versions.edit.field")}
        value={draft.field}
        disabled={busy}
        onChange={(event) =>
          setDraft((current) => ({
            ...current,
            field: event.target.value,
            state: isQuantityField(event.target.value) ? "numeric" : "stated",
            value: "",
          }))
        }
      >
        {editableFields.map((value) => (
          <option key={value} value={value}>
            {t(`versions.edit.fields.${value}`)}
          </option>
        ))}
      </TextField>
      {hasValueState(draft.field) && (
        <TextField
          InputLabelProps={{ shrink: true }}
          select
          SelectProps={{ native: true }}
          label={t("versions.edit.state")}
          value={draft.state}
          disabled={busy}
          onChange={(event) => field("state", event.target.value)}
        >
          {[valueState, "tba", "not_stated", "not_applicable"].map((value) => (
            <option key={value} value={value}>
              {t(`versions.values.${value}`)}
            </option>
          ))}
        </TextField>
      )}
      {needsValue && (
        <TextField
          InputLabelProps={{ shrink: true }}
          label={t("versions.edit.value")}
          value={draft.value}
          disabled={busy}
          onChange={(event) => field("value", event.target.value)}
          helperText={
            draft.field.endsWith("_value")
              ? t("versions.edit.decimalHint")
              : undefined
          }
        />
      )}
      {needsValue && draft.field === "qty_value" && (
        <TextField
          InputLabelProps={{ shrink: true }}
          label={t("versions.edit.unit")}
          value={draft.qtyUnit}
          disabled={busy}
          onChange={(event) => field("qtyUnit", event.target.value)}
        />
      )}
      <TextField
        InputLabelProps={{ shrink: true }}
        label={t("versions.edit.reason")}
        value={draft.reason}
        disabled={busy}
        onChange={(event) => field("reason", event.target.value)}
        multiline
        minRows={2}
      />
      <TextField
        InputLabelProps={{ shrink: true }}
        label={t("versions.edit.recorder")}
        value={draft.recordedBy}
        disabled={busy}
        onChange={(event) => field("recordedBy", event.target.value)}
      />
      {error && <Typography role="alert">{t(error)}</Typography>}
      <Button variant="contained" type="submit" disabled={busy}>
        {t("versions.edit.submit")}
      </Button>
      <Typography variant="caption">{t("versions.edit.hint")}</Typography>
    </Box>
  );
}
