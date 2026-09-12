/**
 * features/cases/hooks.ts — Business Logic（案件一覧・案件作成）。
 *
 * TanStack Query の薄い wrap。作成成功時に一覧のキャッシュを無効化して再取得させる。
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CaseCreateRequest,
  CaseListItem,
  CaseResponse,
} from "@/shared/api/generated/model";
import type { ApiError } from "@/shared/api/mutator";
import { createCase, listCases, getCase } from "@/features/cases/api";

export type CreateCaseInput = CaseCreateRequest;

export const casesQueryKey = () => ["cases"] as const;
export const caseQueryKey = (caseId: number) => ["cases", caseId] as const;

export function useCases() {
  return useQuery<CaseListItem[], ApiError>({
    queryKey: casesQueryKey(),
    queryFn: listCases,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();

  return useMutation<CaseResponse, ApiError, CreateCaseInput>({
    mutationFn: (input) => createCase(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: casesQueryKey() });
    },
  });
}

export function useCase(caseId: number) {
  return useQuery<CaseResponse, ApiError>({
    queryKey: caseQueryKey(caseId),
    queryFn: () => getCase(caseId),
  });
}
