"use client";

import { useEffect, useRef } from "react";
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
  getActiveRunId,
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
    retry: false,
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

// 画面表示時に1回だけ、案件の実行中runを確認する（ポーリングはuseAgentRunが担う）。
export function useActiveRun(caseId: number) {
  return useQuery<{ runId: number | null }, Error>({
    queryKey: ["agent-runs", "active", caseId],
    queryFn: async ({ signal }) => ({
      runId: await getActiveRunId(caseId, signal),
    }),
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: 0,
    gcTime: 0,
  });
}
