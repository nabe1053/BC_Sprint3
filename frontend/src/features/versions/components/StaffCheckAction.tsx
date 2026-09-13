"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Box, Button, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import type { VersionResponse } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { tokens } from "@/shared/theme/tokens";
import { useApprovalMutations } from "../hooks";
import { buildStateEventRequest } from "../model";
import { ApprovalError } from "./ApprovalError";
export function StaffCheckAction({
  caseId,
  version,
  recordedBy,
  onRecorderInvalid,
}: {
  caseId: number;
  version: VersionResponse;
  recordedBy: string;
  onRecorderInvalid: (invalid: boolean) => void;
}) {
  const { t } = useTranslation(),
    router = useRouter(),
    mutations = useApprovalMutations(caseId, version.versionId),
    [error, setError] = useState<unknown>(null),
    [pending, setPending] = useState(false),
    lock = useRef(false);
  async function check() {
    if (lock.current) return;
    lock.current = true;
    setPending(true);
    setError(null);
    onRecorderInvalid(false);
    try {
      await mutations.transition.mutateAsync(
        buildStateEventRequest("staff_checked", recordedBy),
      );
      router.push(`/cases/${caseId}/versions/${version.versionId}/approval`);
    } catch (cause) {
      setError(cause);
      onRecorderInvalid(
        cause instanceof ApiError && cause.code === "E_RECORDER_REQUIRED",
      );
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return (
    <Box>
      {version.currentState === "draft" ? (
        <>
          <Button
            variant="contained"
            disabled={pending}
            onClick={() => void check()}
          >
            {t("versions.staffCheck.button")}
          </Button>
          {version.counts.unresolvedCount > 0 && (
            <Typography
              variant="caption"
              component="div"
              sx={{ color: tokens.colors.warn.main }}
            >
              {t("versions.staffCheck.unresolvedNote", {
                unresolved: version.counts.unresolvedCount,
              })}
            </Typography>
          )}
        </>
      ) : (
        <Button
          component={Link}
          href={`/cases/${caseId}/versions/${version.versionId}/approval`}
        >
          {t("versions.staffCheck.link")}
        </Button>
      )}
      <ApprovalError
        error={error}
        caseId={caseId}
        versionId={version.versionId}
        staff
      />
    </Box>
  );
}
