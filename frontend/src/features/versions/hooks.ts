"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/mutator";
import type {
  StateEventRequest,
  BounceCommentRequest,
  BounceRequest,
  SendoffDecisionRequest,
  ConfirmationRequest,
  ItemEditRequest,
  JudgementRequest,
  UndoRequest,
} from "@/shared/api/generated/model";
import * as api from "./api";

export const versionsKey = (caseId: number) => ["versions", caseId] as const;
export const versionKey = (versionId: number) =>
  ["version", versionId] as const;
export const inventoryKey = (versionId: number) =>
  ["version", versionId, "inventory"] as const;
export const itemsKey = (versionId: number) =>
  ["version", versionId, "items"] as const;
export const questionsKey = (versionId: number) =>
  ["version", versionId, "questions"] as const;
export const evidenceKey = (versionId: number, itemId: number) =>
  ["version", versionId, "items", itemId, "evidence"] as const;
export function useVersionHistory(caseId: number) {
  return useQuery({
    queryKey: versionsKey(caseId),
    queryFn: () => api.listVersions(caseId),
  });
}
export function useVersion(versionId: number) {
  return useQuery({
    queryKey: versionKey(versionId),
    queryFn: () => api.getVersion(versionId),
  });
}
export function useItems(versionId: number) {
  return useQuery({
    queryKey: itemsKey(versionId),
    queryFn: () => api.listItems(versionId),
  });
}
export function useQuestions(versionId: number) {
  return useQuery({
    queryKey: questionsKey(versionId),
    queryFn: () => api.listQuestions(versionId),
  });
}
export function useEvidence(versionId: number, itemId: number) {
  return useQuery({
    queryKey: evidenceKey(versionId, itemId),
    queryFn: () => api.listEvidence(versionId, itemId),
  });
}
function useRecordMutation<Input, Result>(
  versionId: number,
  mutationFn: (input: Input) => Promise<Result>,
  resource: "items" | "questions" | "inventory" | "approvals",
  caseId?: number,
) {
  const client = useQueryClient();
  const refresh = () =>
    Promise.all([
      client.invalidateQueries({
        queryKey: versionKey(versionId),
        exact: true,
      }),
      client.invalidateQueries({
        queryKey:
          resource === "approvals"
            ? recordsKey(versionId)
            : resource === "inventory"
              ? inventoryKey(versionId)
              : resource === "items"
                ? itemsKey(versionId)
                : questionsKey(versionId),
        exact: true,
      }),
      ...(caseId !== undefined
        ? [
            client.invalidateQueries({
              queryKey: versionsKey(caseId),
              exact: true,
            }),
          ]
        : []),
    ]);
  return useMutation<Result, ApiError, Input>({
    mutationFn,
    retry: false,
    onSuccess: refresh,
    onError: (error) => {
      if (
        resource === "approvals" ||
        error.status === 409 ||
        error.status === 404 ||
        error.code === "E_TARGET_INVALID"
      )
        return refresh();
    },
  });
}
export function useRecordMutations(versionId: number, caseId?: number) {
  const edit = useRecordMutation(
    versionId,
    (input: ItemEditRequest) => api.editItem(versionId, input),
    "items",
    caseId,
  );
  const undoEdit = useRecordMutation(
    versionId,
    ({ editId, ...input }: UndoRequest & { editId: number }) =>
      api.undoEdit(versionId, editId, input),
    "items",
    caseId,
  );
  const confirm = useRecordMutation(
    versionId,
    (input: ConfirmationRequest) => api.confirm(versionId, input),
    "items",
    caseId,
  );
  const undoConfirmation = useRecordMutation(
    versionId,
    ({ confirmationId, ...input }: UndoRequest & { confirmationId: number }) =>
      api.undoConfirmation(versionId, confirmationId, input),
    "items",
    caseId,
  );
  const judge = useRecordMutation(
    versionId,
    ({ questionId, ...input }: JudgementRequest & { questionId: number }) =>
      api.judge(versionId, questionId, input),
    "questions",
    caseId,
  );
  return { edit, undoEdit, confirm, undoConfirmation, judge };
}

export function useInventory(versionId: number) {
  return useQuery({
    queryKey: inventoryKey(versionId),
    queryFn: () => api.getInventory(versionId),
  });
}
export function useCoverageMutations(versionId: number) {
  const confirm = useRecordMutation(
    versionId,
    (input: ConfirmationRequest) => api.confirm(versionId, input),
    "inventory",
  );
  const undoConfirmation = useRecordMutation(
    versionId,
    ({ confirmationId, ...input }: UndoRequest & { confirmationId: number }) =>
      api.undoConfirmation(versionId, confirmationId, input),
    "inventory",
  );
  return { confirm, undoConfirmation };
}

export const recordsKey = (versionId: number) =>
  ["version", versionId, "records"] as const;
export function useRecords(versionId: number) {
  return useQuery({
    queryKey: recordsKey(versionId),
    queryFn: () => api.listRecords(versionId),
  });
}
export function useApprovalMutations(caseId: number, versionId: number) {
  const transition = useRecordMutation(
    versionId,
    (input: StateEventRequest) => api.recordStateEvent(versionId, input),
    "approvals",
    caseId,
  );
  const bounceComment = useRecordMutation(
    versionId,
    (input: BounceCommentRequest) => api.recordBounceComment(versionId, input),
    "approvals",
    caseId,
  );
  const bounce = useRecordMutation(
    versionId,
    (input: BounceRequest) => api.recordBounce(versionId, input),
    "approvals",
    caseId,
  );
  const sendoff = useRecordMutation(
    versionId,
    (input: SendoffDecisionRequest) =>
      api.recordSendoffDecision(versionId, input),
    "approvals",
    caseId,
  );
  return { transition, bounceComment, bounce, sendoff };
}

export const exportsKey = (versionId: number) =>
  ["version", versionId, "exports"] as const;
export function useExports(versionId: number) {
  return useQuery({
    queryKey: exportsKey(versionId),
    queryFn: () => api.listExports(versionId),
  });
}
export const createExportKey = (versionId: number) =>
  ["version", versionId, "exports", "create"] as const;
/** #38。再送は別の出力レコードを作るため retry を必ず false にする。
 * mutationKey を版ごとに持ち、同じ版の出力ボタンが複数あっても同時 POST にならない
 * （呼び出し側は useIsMutating で進行中を共有する）。 */
export function useCreateExport(versionId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationKey: createExportKey(versionId),
    mutationFn: () => api.createExport(versionId),
    retry: false,
    onSuccess: () =>
      client.invalidateQueries({ queryKey: exportsKey(versionId) }),
  });
}
