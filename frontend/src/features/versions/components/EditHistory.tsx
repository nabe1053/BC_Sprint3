"use client";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { ItemEditRecord } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { valueLabelKey } from "../model";
import { formatDateTime } from "@/shared/lib/datetime";
export function EditHistory({
  history,
  onUndo,
  busy,
  readOnly = false,
}: {
  history: ItemEditRecord[];
  onUndo?: (editId: number) => void;
  readOnly?: boolean;
  busy: boolean;
}) {
  const { t } = useTranslation();
  const text = (value: string | null, state: string | null) => {
    const key = valueLabelKey(state);
    return key ? t(key) : (value ?? t("versions.values.empty"));
  };
  return (
    <Box>
      <Typography variant="h3">{t("versions.edit.history")}</Typography>
      {history.length ? (
        history.map((edit) => (
          <Box
            key={edit.editId}
            sx={{
              paddingBlock: `${tokens.spacing.s3}px`,
              borderBottom: `${tokens.border.width}px solid ${tokens.colors.hair}`,
            }}
          >
            <Typography>{t(`versions.edit.fields.${edit.field}`)}</Typography>
            <Typography>
              {t("versions.edit.change", {
                old: text(edit.oldValue, edit.oldState),
                new: text(edit.newValue, edit.newState),
              })}
            </Typography>
            <Typography>{edit.reason}</Typography>
            <Typography variant="caption">
              {t("versions.recorded", {
                by: edit.recordedBy,
                at: formatDateTime(edit.recordedAt),
              })}
            </Typography>
            {edit.undoneAt ? (
              <>
                <Typography>{t("versions.edit.undone")}</Typography>
                <Typography variant="caption">
                  {t("versions.recorded", {
                    by: edit.undoneBy,
                    at: formatDateTime(edit.undoneAt),
                  })}
                </Typography>
              </>
            ) : !readOnly && onUndo ? (
              <Button
                variant="outlined"
                disabled={busy}
                onClick={() => onUndo(edit.editId)}
              >
                {t("versions.edit.undo")}
              </Button>
            ) : null}
          </Box>
        ))
      ) : (
        <Typography>{t("versions.edit.emptyHistory")}</Typography>
      )}
    </Box>
  );
}
