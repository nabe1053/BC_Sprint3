import { act, waitFor } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import type { AgentRunResponse } from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";
import { renderHookWithProviders } from "@/shared/testing/test-utils";
import { useStartAgentRun, useAgentRun, useAgentRunSteps } from "../hooks";
import { startAgentRun, getAgentRun, getAgentRunSteps } from "../api";
jest.mock("../api", () => ({
  startAgentRun: jest.fn(),
  getAgentRun: jest.fn(),
  getAgentRunSteps: jest.fn(),
}));
const start = startAgentRun as jest.Mock;
const get = getAgentRun as jest.Mock;
const steps = getAgentRunSteps as jest.Mock;
const run = (outcome: AgentRunResponse["outcome"] = "running", runId = 3) => ({
  runId,
  outcome,
  stage: "reading",
  stageDetail: null,
  turns: 0,
  elapsedSec: 1,
  stopReason: outcome === "success" ? "completed" : null,
  versionId: outcome === "success" ? 9 : null,
  isComplete: outcome === "success",
  limits: {
    maxTurns: null,
    innerTimeoutS: null,
    inactivityTimeoutS: null,
    outerTimeoutS: null,
  },
});
beforeEach(() => {
  jest.resetAllMocks();
  jest.useFakeTimers();
});
afterEach(() => {
  jest.useRealTimers();
});
async function advance(ms: number) {
  await act(async () => {
    await jest.advanceTimersByTimeAsync(ms);
  });
}
it("runIdなしでは取得せず、実行中は2秒ごとに取得する", async () => {
  get.mockResolvedValue(run());
  const { result, rerender } = renderHookWithProviders(
    ({ id }: { id: number | null }) => useAgentRun(id),
    undefined,
    { initialProps: { id: null as number | null } },
  );
  await advance(5000);
  expect(get).not.toHaveBeenCalled();
  rerender({ id: 3 });
  await waitFor(() => expect(result.current.data?.runId).toBe(3));
  expect(get).toHaveBeenCalledTimes(1);
  await advance(1000);
  expect(get).toHaveBeenCalledTimes(1);
  await advance(1000);
  expect(get).toHaveBeenCalledTimes(2);
});
it.each(["success", "failed", "stopped"] as const)(
  "%s終端後は時間・focus・再接続でも取得を停止",
  async (outcome) => {
    get.mockResolvedValueOnce(run()).mockResolvedValue(run(outcome));
    const { result } = renderHookWithProviders(() => ({ ...useAgentRun(3) }));
    await waitFor(() => expect(result.current.data?.outcome).toBe("running"));
    await advance(2000);
    await waitFor(() => expect(result.current.data?.outcome).toBe(outcome));
    window.dispatchEvent(new Event("focus"));
    window.dispatchEvent(new Event("online"));
    await advance(10000);
    expect(get).toHaveBeenCalledTimes(2);
  },
);
it("GET404（run が無い）は再試行せずポーリングを止め、最後の進捗と通信エラーを維持", async () => {
  get
    .mockResolvedValueOnce(run())
    .mockRejectedValueOnce(new ApiError(404, { code: "E_NOT_FOUND" }))
    .mockResolvedValue(run());
  const { result } = renderHookWithProviders(() => ({ ...useAgentRun(3) }));
  await waitFor(() => expect(result.current.data?.outcome).toBe("running"));
  await advance(2000);
  await waitFor(() => expect(result.current.isError).toBe(true));
  await advance(10000);
  expect(get).toHaveBeenCalledTimes(2);
  expect(result.current.isError).toBe(true);
  expect(result.current.data?.runId).toBe(3);
  expect(start).not.toHaveBeenCalled();
});
// F-17: 一時的な失敗（500・通信断）1回で恒久的に「通信中断」にしない。
it.each([
  ["500", () => new ApiError(500, { code: "E_UNKNOWN" })],
  ["通信断", () => new TypeError("offline")],
])(
  "GET %s が1回だけなら再試行して進捗の表示を続ける",
  async (_label, error) => {
    get
      .mockResolvedValueOnce(run())
      .mockRejectedValueOnce(error())
      .mockResolvedValue(run("success"));
    const { result } = renderHookWithProviders(() => ({ ...useAgentRun(3) }));
    await waitFor(() => expect(result.current.data?.outcome).toBe("running"));
    await advance(2000);
    await advance(3000);
    await waitFor(() => expect(result.current.data?.outcome).toBe("success"));
    expect(result.current.isError).toBe(false);
  },
);
it("応答の契約違反（200 の ApiError）は再試行しない", async () => {
  get
    .mockResolvedValueOnce(run())
    .mockRejectedValue(new ApiError(200, { code: "E_UNEXPECTED_RESPONSE" }));
  const { result } = renderHookWithProviders(() => ({ ...useAgentRun(3) }));
  await waitFor(() => expect(result.current.data?.outcome).toBe("running"));
  await advance(2000);
  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(get).toHaveBeenCalledTimes(2);
});
it("GET の一時的な失敗が続けば3回再試行した後に通信エラーにする", async () => {
  get
    .mockResolvedValueOnce(run())
    .mockRejectedValue(new ApiError(500, { code: "E_UNKNOWN" }));
  const { result } = renderHookWithProviders(() => ({ ...useAgentRun(3) }));
  await waitFor(() => expect(result.current.data?.outcome).toBe("running"));
  await advance(2000);
  await advance(20000);
  await waitFor(() => expect(result.current.isError).toBe(true));
  expect(get).toHaveBeenCalledTimes(1 + 1 + 3);
  expect(result.current.data?.runId).toBe(3);
});
it("POSTはQueryClientのretry既定が1でも再送しない", async () => {
  start.mockRejectedValue(new TypeError("offline"));
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: 1 } },
  });
  const { result } = renderHookWithProviders(() => useStartAgentRun(8), client);
  let response!: Promise<unknown>;
  act(() => {
    response = result.current.mutateAsync({});
  });
  const rejected = expect(response).rejects.toThrow("offline");
  await advance(5000);
  await rejected;
  expect(start).toHaveBeenCalledTimes(1);
  client.clear();
});
it("同一hookへの同時起動要求は1回のPOSTへまとめる", async () => {
  let resolve!: (value: unknown) => void;
  start.mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  const { result } = renderHookWithProviders(() => useStartAgentRun(8));
  let first!: Promise<unknown>, second!: Promise<unknown>;
  act(() => {
    first = result.current.mutateAsync({});
    second = result.current.mutateAsync({});
  });
  await advance(0);
  expect(start).toHaveBeenCalledTimes(1);
  await act(async () => {
    resolve({ runId: 3, versionId: 9, startedAt: "2026-09-12" });
    await Promise.all([first, second]);
  });
});
it("run切替で前の要求をabortし、遅い応答を新runに表示しない", async () => {
  let resolve!: (value: unknown) => void;
  let signal!: AbortSignal;
  get
    .mockImplementationOnce((_id, s) => {
      signal = s;
      return new Promise((r) => {
        resolve = r;
      });
    })
    .mockResolvedValue(run("running", 4));
  const { result, rerender } = renderHookWithProviders(
    ({ id }: { id: number }) => useAgentRun(id),
    undefined,
    { initialProps: { id: 3 } },
  );
  rerender({ id: 4 });
  await waitFor(() => expect(result.current.data?.runId).toBe(4));
  expect(signal.aborted).toBe(true);
  await act(async () => {
    resolve(run("success", 3));
  });
  expect(result.current.data?.runId).toBe(4);
});
it("stepsは開いた時だけ取得し、失敗しても主進捗を壊さない", async () => {
  get.mockResolvedValue(run());
  steps.mockRejectedValue(new Error("offline"));
  const { result, rerender } = renderHookWithProviders(
    ({ open }: { open: boolean }) => ({
      run: useAgentRun(3),
      steps: useAgentRunSteps(3, open),
    }),
    undefined,
    { initialProps: { open: false } },
  );
  await waitFor(() => expect(result.current.run.data?.runId).toBe(3));
  expect(steps).not.toHaveBeenCalled();
  rerender({ open: true });
  await waitFor(() => expect(result.current.steps.isError).toBe(true));
  expect(result.current.run.isError).toBe(false);
  expect(result.current.run.data?.outcome).toBe("running");
});
it("案件切替で進行中POSTの共有を解除し、旧要求の完了は新要求の保持を消さない", async () => {
  const resolvers: Array<(value: unknown) => void> = [];
  start.mockImplementation(
    () =>
      new Promise((resolve) => {
        resolvers.push(resolve);
      }),
  );
  const { result, rerender } = renderHookWithProviders(
    ({ caseId }: { caseId: number }) => useStartAgentRun(caseId),
    undefined,
    { initialProps: { caseId: 8 } },
  );
  let first!: Promise<unknown>,
    second!: Promise<unknown>,
    third!: Promise<unknown>;
  act(() => {
    first = result.current.mutateAsync({});
  });
  await advance(0);
  rerender({ caseId: 9 });
  act(() => {
    second = result.current.mutateAsync({});
  });
  await advance(0);
  expect(start).toHaveBeenNthCalledWith(1, 8, {});
  expect(start).toHaveBeenNthCalledWith(2, 9, {});
  await act(async () => {
    resolvers[0]({ runId: 3 });
    await first;
  });
  act(() => {
    third = result.current.mutateAsync({});
  });
  await advance(0);
  expect(start).toHaveBeenCalledTimes(2);
  await act(async () => {
    resolvers[1]({ runId: 4 });
    await Promise.all([second, third]);
  });
});
