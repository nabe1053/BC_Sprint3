"use client";

import { useEffect, useRef } from "react";
import { ApiError } from "@/shared/api/mutator";
import { useMutation, useQuery } from "@tanstack/react-query";
import type {
  AgentRunAccepted,
  AgentRunRequest,
  AgentRunResponse,
  RunStepResponse,
} from "@/shared/api/generated/model";
import {
  startAgentRun,
  getAgentRun,
  getAgentRunSteps,
  getRunResume,
  listCarryOver,
} from "./api";

export function useStartAgentRun(caseId: number) {
  const pending = useRef<Promise<AgentRunAccepted> | null>(null);
  useEffect(() => {
    pending.current = null;
  }, [caseId]);
  const mutation = useMutation<AgentRunAccepted, Error, AgentRunRequest>({
    mutationKey: ["agent-runs", "start", caseId],
    mutationFn: (input) => startAgentRun(caseId, input),
    retry: false,
  });
  function mutateAsync(input: AgentRunRequest = {}) {
    if (pending.current) return pending.current;
    const promise = mutation.mutateAsync(input).finally(() => {
      // 別案件へ移った後の旧要求が、新しい案件の進行中要求を消さない。
      if (pending.current === promise) pending.current = null;
    });
    pending.current = promise;
    return promise;
  }
  // 生のmutateを公開せず、同時要求が必ず同じPromiseを経由するようにする。
  return {
    mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data,
  };
}

export function useAgentRun(runId: number | null) {
  return useQuery<AgentRunResponse, Error>({
    queryKey: ["agent-runs", "progress", runId],
    queryFn: ({ signal }) => getAgentRun(runId!, signal),
    enabled: runId !== null && Number.isSafeInteger(runId) && runId > 0,
    // 一時的な失敗（500・通信断）は3回まで再試行し、1回で「通信中断」にしない（F-17）。
    // run が無い（404）・応答の契約違反など一時的でない失敗は再試行しない。
    retry: (count, error) =>
      count < 3 && (!(error instanceof ApiError) || error.status >= 500),
    retryDelay: 2000,
    retryOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    refetchOnMount: false,
    staleTime: Infinity,
    refetchInterval: (query) =>
      query.state.status === "error" ||
      (query.state.data && query.state.data.outcome !== "running")
        ? false
        : 2000,
  });
}

export function useAgentRunSteps(runId: number | null, open: boolean) {
  return useQuery<RunStepResponse[], Error>({
    queryKey: ["agent-runs", "steps", runId],
    queryFn: ({ signal }) => getAgentRunSteps(runId!, signal),
    enabled: open && runId !== null,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: Infinity,
  });
}

// 画面表示時に1回だけ、案件の実行中runと直近のrunを確認する（ポーリングはuseAgentRunが担う）。
// 直近のrunは、画面を離れている間に終わった結果を戻ったときに示すために使う（F-17）。
export function useActiveRun(caseId: number) {
  return useQuery<{ runId: number | null; latestRunId: number | null }, Error>({
    queryKey: ["agent-runs", "active", caseId],
    queryFn: ({ signal }) => getRunResume(caseId, signal),
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: 0,
    gcTime: 0,
  });
}

// 引き継ぎ警告は資料投入画面でだけ使う（enabled=false の画面では取得しない）。
export function useCarryOver(caseId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["agent-runs", "carry-over", caseId],
    queryFn: ({ signal }) => listCarryOver(caseId, signal),
    enabled,
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 0,
  });
}
