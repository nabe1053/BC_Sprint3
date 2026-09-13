"use client";
import Link from "next/link";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { ApiError } from "@/shared/api/mutator";
import { approvalErrorKey, staffCheckDetails } from "../model";
export function ApprovalError({
  error,
  caseId,
  versionId,
  sendoff = false,
  staff = false,
}: {
  error: unknown;
  caseId: number;
  versionId: number;
  sendoff?: boolean;
  staff?: boolean;
}) {
  const { t } = useTranslation();
  if (!error) return null;
  const code = error instanceof ApiError ? error.code : null,
    details = staffCheckDetails(error);
  const key =
    sendoff && code === "E_RECORDER_REQUIRED"
      ? "versions.approval.errors.E_RECORDER_REQUIRED_SENDOFF"
      : staff && code === "E_STAFF_CHECK_INCOMPLETE"
        ? "versions.staffCheck.errors.E_STAFF_CHECK_INCOMPLETE"
        : approvalErrorKey(error);
  return (
    <Box role="alert">
      <Typography>
        {t(key, {
          unmatched: details.rowCodes.length,
          rowCodes: details.rowCodes.join(", "),
          coverage: t(
            `versions.coverageState.${details.coverageRecorded ? "yes" : "no"}`,
          ),
        })}
      </Typography>
      {(code === "E_STAFF_CHECK_INCOMPLETE" ||
        code === "E_COVERAGE_NOT_RECORDED") && (
        <Button
          component={Link}
          href={`/cases/${caseId}/versions/${versionId}/inventory`}
        >
          {t("versions.staffCheck.toInventory")}
        </Button>
      )}
    </Box>
  );
}
