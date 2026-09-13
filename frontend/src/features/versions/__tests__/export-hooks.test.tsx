import { act, waitFor } from "@testing-library/react";
import { QueryClient } from "@tanstack/react-query";
import {
  renderHookWithProviders,
  createTestQueryClient,
} from "@/shared/testing/test-utils";
import { ApiError } from "@/shared/api/mutator";
import * as api from "../api";
import * as hooks from "../hooks";
jest.mock("../api");
const mock = jest.mocked(api);
const record = {
  exportId: 1,
  fileName: "S-01__v2_draft.xlsx",
  exportedAt: "2026-09-13T00:00:00Z",
  stateAtExport: "draft",
  sendoffAtExport: null,
  unresolvedAtExport: 2,
  isInitial: true,
  integrity: "intact",
  storagePath: "1/uuid.xlsx",
  contentHash: "abc",
};
beforeEach(() => {
  jest.resetAllMocks();
  mock.listExports.mockResolvedValue([record] as never);
});

it("useExportsは版ごとの出力履歴を返す", async () => {
  const { result } = renderHookWithProviders(
    () => hooks.useExports(9),
    createTestQueryClient(),
  );
  await waitFor(() => expect(result.current.data).toEqual([record]));
  expect(mock.listExports).toHaveBeenCalledWith(9);
});

it("useCreateExportは成功時に当該版の履歴だけを再取得する", async () => {
  mock.createExport.mockResolvedValue({
    blob: new Blob(["x"]),
    exportId: "1",
    fileName: "S-01__v2_draft.xlsx",
    namedByServer: true,
  } as never);
  const client = createTestQueryClient();
  const invalidate = jest.spyOn(client, "invalidateQueries");
  const { result } = renderHookWithProviders(
    () => hooks.useCreateExport(9),
    client,
  );
  await act(async () => {
    await result.current.mutateAsync();
  });
  expect(mock.createExport).toHaveBeenCalledWith(9);
  expect(invalidate).toHaveBeenCalledWith({ queryKey: hooks.exportsKey(9) });
});

it("useCreateExportは失敗しても自動で再POSTしない", async () => {
  mock.createExport.mockRejectedValue(
    new ApiError(409, { code: "E_VERSION_NOT_FINALIZED" }),
  );
  // 既定が retry 有効なクライアントで検証する。テスト用既定に隠れると
  // hooks 側の retry:false を外しても気づけない（RV-046 P2）。
  const retrying = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: 3, retryDelay: 1 },
    },
  });
  const { result } = renderHookWithProviders(
    () => hooks.useCreateExport(9),
    retrying,
  );
  await act(async () => {
    await expect(result.current.mutateAsync()).rejects.toBeInstanceOf(ApiError);
  });
  await waitFor(() => expect(result.current.isPending).toBe(false));
  expect(mock.createExport).toHaveBeenCalledTimes(1);
});
