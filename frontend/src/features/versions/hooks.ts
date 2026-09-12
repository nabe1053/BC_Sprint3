"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/mutator";
import type {
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
  resource: "items" | "questions" | "inventory",
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
          resource === "inventory"
            ? inventoryKey(versionId)
            : resource === "items"
              ? itemsKey(versionId)
              : questionsKey(versionId),
        exact: true,
      }),
    ]);
  return useMutation<Result, ApiError, Input>({
    mutationFn,
    retry: false,
    onSuccess: refresh,
    onError: (error) => {
      if (
        error.status === 409 ||
        error.status === 404 ||
        error.code === "E_TARGET_INVALID"
      )
        return refresh();
    },
  });
}
export function useRecordMutations(versionId: number) {
  const edit = useRecordMutation(
    versionId,
    (input: ItemEditRequest) => api.editItem(versionId, input),
    "items",
  );
  const undoEdit = useRecordMutation(
    versionId,
    ({ editId, ...input }: UndoRequest & { editId: number }) =>
      api.undoEdit(versionId, editId, input),
    "items",
  );
  const confirm = useRecordMutation(
    versionId,
    (input: ConfirmationRequest) => api.confirm(versionId, input),
    "items",
  );
  const undoConfirmation = useRecordMutation(
    versionId,
    ({ confirmationId, ...input }: UndoRequest & { confirmationId: number }) =>
      api.undoConfirmation(versionId, confirmationId, input),
    "items",
  );
  const judge = useRecordMutation(
    versionId,
    ({ questionId, ...input }: JudgementRequest & { questionId: number }) =>
      api.judge(versionId, questionId, input),
    "questions",
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
