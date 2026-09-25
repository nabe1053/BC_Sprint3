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
/**
 * 担当者確認の操作と結果表示を分ける（F-13）。ボタンは見出し右端に置き、
 * 未解決の注記・失敗表示は見出しの下の行に出して、押下前後でボタンの位置を動かさない。
 */
export function useStaffCheck({
  caseId,
  versionId,
  recordedBy,
  onRecorderInvalid,
}: {
  caseId: number;
  versionId: number;
  recordedBy: string;
  onRecorderInvalid: (invalid: boolean) => void;
}) {
  const router = useRouter(),
    mutations = useApprovalMutations(caseId, versionId),
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
      router.push(`/cases/${caseId}/versions/${versionId}/approval`);
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
  return { check, pending, error };
}

export function StaffCheckButton({
  caseId,
  version,
  pending,
  onCheck,
}: {
  caseId: number;
  version: VersionResponse;
  pending: boolean;
  onCheck: () => void;
}) {
  const { t } = useTranslation();
  return version.currentState === "draft" ? (
    <Button variant="contained" disabled={pending} onClick={onCheck}>
      {t("versions.staffCheck.button")}
    </Button>
  ) : (
    <Button
      component={Link}
      href={`/cases/${caseId}/versions/${version.versionId}/approval`}
    >
      {t("versions.staffCheck.link")}
    </Button>
  );
}

export function StaffCheckNotice({
  caseId,
  version,
  error,
}: {
  caseId: number;
  version: VersionResponse;
  error: unknown;
}) {
  const { t } = useTranslation();
  const note =
    version.currentState === "draft" && version.counts.unresolvedCount > 0;
  if (!note && !error) return null;
  return (
    <Box>
      {note && (
        <Typography variant="body2" sx={{ color: tokens.colors.warn.main }}>
          {t("versions.staffCheck.unresolvedNote", {
            unresolved: version.counts.unresolvedCount,
          })}
        </Typography>
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
