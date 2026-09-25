import type { AgentRunResponse } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";

const stopReasons = [
  "completed",
  "failed",
  "max_turns",
  "inner_timeout",
  "inactivity_timeout",
  "outer_timeout",
  "repeated_call",
  "no_readable_document",
  "validation_loop",
] as const;
const stages = ["reading", "extracting", "self_checking", "done"] as const;

export function stopReasonLabelKey(reason: string | null) {
  return `agentRuns.stopReason.${stopReasons.find((value) => value === reason) ?? "unknown"}`;
}
export function stageLabelKey(stage: string | null) {
  return `agentRuns.stage.${stages.find((value) => value === stage) ?? "pending"}`;
}

// 06 TEST-04 #1「資料 n/N 読取中 → 抽出中 → 自己点検中」の3段階。done は確定処理中。
export const stageSteps = ["reading", "extracting", "self_checking"] as const;
export function stepMark(stage: string | null, index: number) {
  const position =
    stage === "done"
      ? stageSteps.length
      : stageSteps.findIndex((value) => value === stage);
  if (position < 0) return "pending" as const;
  return index < position
    ? ("done" as const)
    : index === position
      ? ("current" as const)
      : ("pending" as const);
}

export type BlockedReason =
  "loading" | "documentsError" | "noReadable" | "limitExceeded" | "uploading";
export function readProgress(detail: string | null) {
  if (!detail) return null;
  try {
    const value: unknown = JSON.parse(detail);
    if (
      !value ||
      typeof value !== "object" ||
      !("documentsRead" in value) ||
      !("documentsTotal" in value)
    )
      return null;
    const { documentsRead, documentsTotal } = value;
    if (
      typeof documentsRead !== "number" ||
      typeof documentsTotal !== "number" ||
      !Number.isSafeInteger(documentsRead) ||
      !Number.isSafeInteger(documentsTotal) ||
      documentsRead < 0 ||
      documentsTotal < documentsRead
    )
      return null;
    return { read: documentsRead, total: documentsTotal };
  } catch {
    return null;
  }
}
export function hasDraft(run: AgentRunResponse) {
  return (
    run.outcome === "success" &&
    run.stopReason === "completed" &&
    typeof run.versionId === "number" &&
    Number.isSafeInteger(run.versionId) &&
    run.versionId > 0 &&
    typeof run.isComplete === "boolean"
  );
}
const diagnostics = [
  "worker_failed",
  "process_interrupted",
  "job_start_failed",
  "draft_not_finalized",
  "agent_implementation_pending",
  "terminal_recovery",
  "trace_write_failed",
  "tool_rejected",
  "local_dummy_unsupported",
  "validation_unresolved",
] as const;
export function diagnosticCode(detail: string | null) {
  return diagnostics.find((code) => code === detail);
}
export function startFailure(error: unknown) {
  if (!(error instanceof ApiError)) return "unknown";
  switch (error.code) {
    case "E_CARRY_OVER_NOT_ACKNOWLEDGED":
      return "carryOver";
    case "E_NO_READABLE_DOCUMENT":
      return "noReadable";
    case "E_LIMIT_EXCEEDED":
      return "limitExceeded";
    case "E_RUN_IN_PROGRESS":
      return "inProgress";
    case "E_EXTERNAL_SEND_NOT_APPROVED":
      return "externalSend";
    case "E_REQUEST_INVALID":
      return "invalid";
    case "E_NOT_FOUND":
      return "notFound";
    default:
      return "unknown";
  }
}

export function runLimitDetails(value: unknown) {
  if (
    !value ||
    typeof value !== "object" ||
    !("kind" in value) ||
    !("actual" in value) ||
    !("limit" in value)
  )
    return null;
  const kind = (
    ["documents", "fileBytes", "pdfPages", "xlsxSheets"] as const
  ).find((kind) => kind === value.kind);
  const { actual, limit } = value;
  if (
    !kind ||
    typeof actual !== "number" ||
    !Number.isSafeInteger(actual) ||
    actual < 0 ||
    typeof limit !== "number" ||
    !Number.isSafeInteger(limit) ||
    limit < 0
  )
    return null;
  const documentId =
    "documentId" in value &&
    typeof value.documentId === "number" &&
    Number.isSafeInteger(value.documentId) &&
    value.documentId > 0
      ? value.documentId
      : null;
  return { kind, actual, limit, documentId };
}

export type CarryOverRow = {
  versionId: number;
  versionNo: number;
  editCount: number;
  rowMatchConfirmed: number;
  rowMatchTotal: number;
  coverageRecorded: boolean;
  judgementCount: number;
};
// サーバーの引き継ぎ判定（未取消の訂正・確認、判断の有無）と同じ条件で、記録のある版だけを残す。
export const carryOverVersions = (rows: readonly CarryOverRow[]) =>
  rows.filter(
    (row) =>
      row.editCount > 0 ||
      row.rowMatchConfirmed > 0 ||
      row.coverageRecorded ||
      row.judgementCount > 0,
  );
