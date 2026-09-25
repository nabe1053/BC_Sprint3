/**
 * features/documents/hooks.ts — Business Logic（資料一覧・資料投入）。
 *
 * AD-005: 415（E_UNSUPPORTED_FORMAT）は「投入の事実を記録した上でのエラー」なので
 * 一覧を再取得する。413（E_LIMIT_EXCEEDED）は記録を残さないため再取得しない。
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DocumentExclusionRecord,
  DocumentIntakeResponse,
  DocumentSummary,
  ExcludedDocument,
} from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import {
  excludeDocument,
  intakeDocument,
  listDocumentExclusions,
  listDocuments,
} from "@/features/documents/api";
import { CASES_QUERY_KEY } from "@/shared/api/queryKeys";

export function documentsQueryKey(caseId: number) {
  return ["documents", caseId] as const;
}

export function useDocuments(caseId: number) {
  return useQuery<DocumentSummary[], ApiError>({
    queryKey: documentsQueryKey(caseId),
    queryFn: () => listDocuments(caseId),
  });
}

export function useIntakeDocument(caseId: number) {
  const queryClient = useQueryClient();

  return useMutation<DocumentIntakeResponse, ApiError, File>({
    mutationFn: (file) => intakeDocument(caseId, file),
    onSuccess: () => {
      // invalidateQueries の完了を待ってから mutateAsync を解決させる
      // （呼び出し側が待ち終えた時点で一覧の再取得まで完了していることを保証する）。
      return queryClient.invalidateQueries({
        queryKey: documentsQueryKey(caseId),
      });
    },
    onError: (error) => {
      // 415 は投入の事実が記録されるため、一覧を再取得して反映する。
      if (error instanceof ApiError && error.code === "E_UNSUPPORTED_FORMAT") {
        return queryClient.invalidateQueries({
          queryKey: documentsQueryKey(caseId),
        });
      }
      return undefined;
    },
  });
}

export function documentExclusionsQueryKey(caseId: number) {
  return ["documents", caseId, "exclusions"] as const;
}

/** F-16: 除外済みの資料。「除外済みの資料を表示」を開いたときだけ取得する。 */
export function useDocumentExclusions(caseId: number, enabled: boolean) {
  return useQuery<ExcludedDocument[], ApiError>({
    queryKey: documentExclusionsQueryKey(caseId),
    queryFn: () => listDocumentExclusions(caseId),
    enabled,
  });
}

/** F-16: 資料の除外。成功したら受付一覧・除外済み一覧・案件一覧を取り直す。 */
export function useExcludeDocument(caseId: number) {
  const queryClient = useQueryClient();
  return useMutation<
    DocumentExclusionRecord,
    ApiError,
    { documentId: number; recordedBy: string }
  >({
    mutationFn: ({ documentId, recordedBy }) =>
      excludeDocument(caseId, documentId, recordedBy),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: documentsQueryKey(caseId) }),
        queryClient.invalidateQueries({ queryKey: CASES_QUERY_KEY }),
      ]).then(() => undefined),
  });
}
