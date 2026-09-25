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
  RecordsResponse,
} from "@/shared/api/generated/model";
import type { ApiError } from "@/shared/api/mutator";
import { CASES_QUERY_KEY } from "@/shared/api/queryKeys";
import {
  createCase,
  listCases,
  getCase,
  listVersionRecords,
} from "@/features/cases/api";

export type CreateCaseInput = CaseCreateRequest;

export const casesQueryKey = () => CASES_QUERY_KEY;
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

/** F-15: 行を展開したときだけ版の記録を取得する（一覧表示のたびに全版を引かない）。 */
export function useCaseRecords(versionId: number, enabled: boolean) {
  return useQuery<RecordsResponse, ApiError>({
    queryKey: ["cases", "records", versionId] as const,
    queryFn: () => listVersionRecords(versionId),
    enabled,
  });
}
