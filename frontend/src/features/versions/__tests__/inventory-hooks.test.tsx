import { act, waitFor, renderHook } from "@testing-library/react";
import { useQueryClient } from "@tanstack/react-query";
import {
  renderHookWithProviders,
  createTestQueryClient,
} from "@/shared/testing/test-utils";
import { Providers } from "@/app/providers";
import { ApiError } from "@/shared/api/mutator";
import * as api from "../api";
import {
  useInventory,
  useCoverageMutations,
  useVersion,
  useItems,
  inventoryKey,
  versionKey,
  itemsKey,
} from "../hooks";
import { inventory, item, version } from "../testing/fixtures";
jest.mock("../api");
const mock = jest.mocked(api);
beforeEach(() => {
  jest.resetAllMocks();
  mock.getInventory.mockResolvedValue(inventory);
  mock.getVersion.mockResolvedValue(version);
  mock.listItems.mockResolvedValue([item]);
});
it.each(
  (["confirm", "undoConfirmation"] as const).flatMap((name) =>
    [200, 409, 404, 400].map((status) => ({ name, status })),
  ),
)(
  "$name / $status はinventoryと版を更新しitemsに触らない",
  async ({ name, status }) => {
    const client = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({
        data: useInventory(9),
        version: useVersion(9),
        items: useItems(9),
        mutations: useCoverageMutations(9),
      }),
      client,
    );
    await waitFor(() =>
      expect(
        result.current.data.isSuccess &&
          result.current.version.isSuccess &&
          result.current.items.isSuccess,
      ).toBe(true),
    );
    expect(inventoryKey(9)).toEqual(["version", 9, "inventory"]);
    const next = {
      ...inventory,
      summary: {
        ...inventory.summary,
        coverage: {
          confirmationId: 51,
          recordedBy: "応答者",
          recordedAt: "2026-09-13T01:00:00Z",
        },
      },
    };
    mock.getInventory.mockResolvedValue(next);
    mock.getVersion.mockResolvedValue({ ...version, coverageConfirmed: true });
    if (status === 200) mock[name].mockResolvedValue({} as never);
    else
      mock[name].mockRejectedValue(
        new ApiError(status, {
          code:
            status === 409
              ? "E_ALREADY_CONFIRMED"
              : status === 404
                ? "E_NOT_FOUND"
                : "E_TARGET_INVALID",
        }),
      );
    await act(async () => {
      try {
        if (name === "confirm")
          await result.current.mutations.confirm.mutateAsync({
            kind: "coverage",
            recordedBy: "担当",
          });
        else
          await result.current.mutations.undoConfirmation.mutateAsync({
            confirmationId: 51,
            recordedBy: "取消担当",
          });
      } catch {
        /* assert below */
      }
    });
    await waitFor(() =>
      expect(client.getQueryData(inventoryKey(9))).toEqual(next),
    );
    expect(client.getQueryData(versionKey(9))).toEqual({
      ...version,
      coverageConfirmed: true,
    });
    expect(client.getQueryData(itemsKey(9))).toEqual([item]);
    expect(mock.listItems).toHaveBeenCalledTimes(1);
    expect(mock[name]).toHaveBeenCalledTimes(1);
    if (name === "confirm")
      expect(mock.confirm).toHaveBeenCalledWith(9, {
        kind: "coverage",
        recordedBy: "担当",
      });
    else
      expect(mock.undoConfirmation).toHaveBeenCalledWith(9, 51, {
        recordedBy: "取消担当",
      });
  },
);
it("本番Providersで400 POSTは1回、既定retryよりhook設定を優先", async () => {
  const original = global.fetch,
    request = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ code: "E_RECORDER_REQUIRED" }),
    });
  global.fetch = request;
  mock.confirm.mockImplementation(
    jest.requireActual<typeof api>("../api").confirm,
  );
  const { result, rerender } = renderHook(
    () => ({ mutations: useCoverageMutations(9), client: useQueryClient() }),
    { wrapper: Providers },
  );
  act(() => {
    result.current.client.setDefaultOptions({
      mutations: { retry: 1, retryDelay: 0 },
    });
    rerender();
  });
  try {
    await act(async () => {
      await expect(
        result.current.mutations.confirm.mutateAsync({
          kind: "coverage",
          recordedBy: "",
        }),
      ).rejects.toMatchObject({ code: "E_RECORDER_REQUIRED" });
    });
    expect(request).toHaveBeenCalledTimes(1);
  } finally {
    global.fetch = original;
  }
});
