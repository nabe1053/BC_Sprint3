"use client";
import { useRef, useState } from "react";
import { Box, Button, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { BounceCommentRecord } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { formatDateTime } from "@/shared/lib/datetime";
export function BounceCommentCell({
  itemId,
  rowCode,
  comments,
  onRecord,
  busy,
}: {
  itemId: number;
  rowCode: string;
  comments: BounceCommentRecord[];
  onRecord: (itemId: number, comment: string) => Promise<boolean>;
  busy: boolean;
}) {
  const { t } = useTranslation(),
    [value, setValue] = useState(""),
    [attempted, setAttempted] = useState(false),
    lock = useRef(false);
  async function save() {
    if (lock.current) return;
    lock.current = true;
    setAttempted(true);
    try {
      if (await onRecord(itemId, value)) {
        setValue("");
        setAttempted(false);
      }
    } finally {
      lock.current = false;
    }
  }
  return (
    <Box sx={{ minWidth: `${tokens.spacing.s8 * 6}px`, whiteSpace: "normal" }}>
      <TextField
        fullWidth
        label={t("versions.approval.bounce.label", { row: rowCode })}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        InputLabelProps={{ shrink: true }}
        inputProps={{ "aria-invalid": attempted && !value.trim() }}
      />
      <Button disabled={busy} onClick={() => void save()}>
        {t("versions.approval.bounce.record")}
      </Button>
      {comments.map((c) => (
        <Typography
          key={c.bounceCommentId}
          variant="caption"
          component="div"
          sx={{ overflowWrap: "anywhere" }}
        >
          {t("versions.approval.bounce.recorded", {
            comment: c.comment,
            by: c.recordedBy,
            at: formatDateTime(c.recordedAt),
          })}
        </Typography>
      ))}
    </Box>
  );
}
