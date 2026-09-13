import { act, waitFor, renderHook } from "@testing-library/react";
import { useQueryClient } from "@tanstack/react-query";
import {
  renderHookWithProviders,
  createTestQueryClient,
} from "@/shared/testing/test-utils";
import { Providers } from "@/app/providers";
import { ApiError } from "@/shared/api/mutator";
import * as api from "../api";
import * as hooks from "../hooks";
import { approvalData } from "../testing/fixtures";
jest.mock("../api");
const mock = jest.mocked(api);
const names = {
  transition: "recordStateEvent",
  bounceComment: "recordBounceComment",
  bounce: "recordBounce",
  sendoff: "recordSendoffDecision",
} as const;
beforeEach(() => {
  jest.resetAllMocks();
  const d = approvalData();
  mock.listRecords.mockResolvedValue(d.records);
  mock.getVersion.mockResolvedValue(d.version);
  mock.listVersions.mockResolvedValue([d.listItem]);
  mock.listItems.mockResolvedValue(d.items);
  mock.listQuestions.mockResolvedValue(d.questions);
});
it.each(
  (Object.keys(names) as (keyof typeof names)[]).flatMap((name) =>
    [201, 409, 404, 400].map((status) => ({ name, status })),
  ),
)("$name/$statusはrecords・版・版一覧だけ再取得", async ({ name, status }) => {
  const client = createTestQueryClient(),
    d = approvalData();
  const { result } = renderHookWithProviders(
    () => ({
      records: hooks.useRecords(9),
      version: hooks.useVersion(9),
      versions: hooks.useVersionHistory(8),
      items: hooks.useItems(9),
      questions: hooks.useQuestions(9),
      mutations: hooks.useApprovalMutations(8, 9),
    }),
    client,
  );
  await waitFor(() =>
    expect(
      [
        result.current.records,
        result.current.version,
        result.current.versions,
        result.current.items,
        result.current.questions,
      ].every((q) => q.isSuccess),
    ).toBe(true),
  );
  const nextRecords = { ...d.records, unlinkedComments: [] },
    nextVersion = { ...d.version, currentState: "review_checked" as const },
    nextList = [{ ...d.listItem, needsRecheck: true }];
  mock.listRecords.mockResolvedValue(nextRecords);
  mock.getVersion.mockResolvedValue(nextVersion);
  mock.listVersions.mockResolvedValue(nextList);
  const action = mock[names[name]];
  if (status === 201) action.mockResolvedValue({} as never);
  else
    action.mockRejectedValue(
      new ApiError(status, {
        code:
          status === 400
            ? "E_RECORDER_REQUIRED"
            : status === 404
              ? "E_NOT_FOUND"
              : "E_STATE_ORDER",
      }),
    );
  await act(async () => {
    try {
      const mutation = result.current.mutations;
      if (name === "transition")
        await mutation.transition.mutateAsync({
          toState: "review_checked",
          recordedBy: "人",
        });
      if (name === "bounceComment")
        await mutation.bounceComment.mutateAsync({
          itemId: 4,
          comment: "確認",
          recordedBy: "人",
        });
      if (name === "bounce")
        await mutation.bounce.mutateAsync({ recordedBy: "人" });
      if (name === "sendoff")
        await mutation.sendoff.mutateAsync({
          decision: "undecided",
          reason: null,
          recordedBy: "人",
        });
    } catch {
      /* cache assertions below cover failure paths */
    }
  });
  await waitFor(() =>
    expect(client.getQueryData(hooks.recordsKey(9))).toEqual(nextRecords),
  );
  expect(client.getQueryData(hooks.versionKey(9))).toEqual(nextVersion);
  expect(client.getQueryData(hooks.versionsKey(8))).toEqual(nextList);
  expect(mock.listItems).toHaveBeenCalledTimes(1);
  expect(mock.listQuestions).toHaveBeenCalledTimes(1);
  expect(action).toHaveBeenCalledTimes(1);
});
it("本番Providersでも承認400 POSTは1回、mutation retry設定を優先", async () => {
  const original = global.fetch,
    request = jest.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ code: "E_RECORDER_REQUIRED" }),
    });
  global.fetch = request;
  mock.recordStateEvent.mockImplementation(
    jest.requireActual<typeof api>("../api").recordStateEvent,
  );
  const { result, rerender } = renderHook(
    () => ({
      mutations: hooks.useApprovalMutations(8, 9),
      client: useQueryClient(),
    }),
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
        result.current.mutations.transition.mutateAsync({
          toState: "review_checked",
          recordedBy: "",
        }),
      ).rejects.toMatchObject({ code: "E_RECORDER_REQUIRED" });
    });
    expect(request).toHaveBeenCalledTimes(1);
  } finally {
    global.fetch = original;
  }
});
