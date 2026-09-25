"use client";
import { useId } from "react";
import { Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { VersionResponse } from "@/shared/api/generated/model";
import { tokens } from "@/shared/theme/tokens";
import { canReview } from "../model";
export function ReviewCheckPanel({
  state,
  recordedBy,
  onName,
  onApprove,
  onBounce,
  busy,
  rows,
  invalid,
}: {
  state: VersionResponse["currentState"];
  recordedBy: string;
  onName: (name: string) => void;
  onApprove: () => void;
  onBounce: () => void;
  busy: boolean;
  rows: number;
  invalid: boolean;
}) {
  const { t } = useTranslation(),
    ready = canReview(state),
    nameId = useId();
  return (
    <Paper
      component="section"
      variant="outlined"
      aria-labelledby="review-check-title"
      sx={{
        padding: `${tokens.spacing.s4}px`,
        display: "grid",
        alignContent: "start",
        gap: `${tokens.spacing.s3}px`,
        minWidth: 0,
      }}
    >
      <Typography id="review-check-title" variant="h2">
        {t("versions.approval.review.title")}
      </Typography>
      <TextField
        id={nameId}
        label={t("versions.approval.review.recorder")}
        value={recordedBy}
        onChange={(e) => onName(e.target.value)}
        // 拒否理由は欄の下に出す。表の上のエラー行だけでは見落とし、
        // 直前の評価確認の記録行を「記録された」と誤読する（TEST-14 #1）。
        error={invalid}
        helperText={t(
          invalid
            ? "versions.approval.review.recorderRequired"
            : "versions.approval.review.recorderHint",
        )}
        InputLabelProps={{ shrink: true }}
        inputProps={{ "aria-required": true }}
      />
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: `${tokens.spacing.s2}px`,
        }}
      >
        <Button
          variant="contained"
          disabled={busy || ready !== "ready"}
          onClick={onApprove}
        >
          {t("versions.approval.review.approve")}
        </Button>
        <Button
          variant="outlined"
          disabled={busy || ready !== "ready"}
          onClick={onBounce}
        >
          {t("versions.approval.review.bounce")}
        </Button>
      </Box>
      <Typography variant="caption">
        {t(
          ready === "incomplete"
            ? "versions.approval.review.draftHint"
            : ready === "reviewed"
              ? "versions.approval.review.reviewedHint"
              : "versions.approval.review.hint",
          { rows },
        )}
      </Typography>
    </Paper>
  );
}
