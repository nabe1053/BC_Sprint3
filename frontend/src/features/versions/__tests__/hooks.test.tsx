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
  useVersion,
  useItems,
  useQuestions,
  useVersionHistory,
  useEvidence,
  useRecordMutations,
  versionKey,
  itemsKey,
  questionsKey,
  versionsKey,
  evidenceKey,
} from "../hooks";
import { item, question, version } from "../testing/fixtures";
jest.mock("../api", () => ({
  listVersions: jest.fn(),
  getVersion: jest.fn(),
  listItems: jest.fn(),
  listQuestions: jest.fn(),
  listEvidence: jest.fn(),
  editItem: jest.fn(),
  undoEdit: jest.fn(),
  confirm: jest.fn(),
  undoConfirmation: jest.fn(),
  judge: jest.fn(),
}));
const mock = jest.mocked(api);
beforeEach(() => {
  jest.resetAllMocks();
  mock.listVersions.mockResolvedValue([]);
  mock.getVersion.mockResolvedValue(version);
  mock.listItems.mockResolvedValue([item]);
  mock.listQuestions.mockResolvedValue([question]);
  mock.listEvidence.mockResolvedValue([]);
});
const inputs = {
  edit: {
    itemId: 4,
    field: "grade",
    newValue: "L80",
    newState: "stated",
    reason: "照合",
    recordedBy: "担当",
  },
  undoEdit: { editId: 2, recordedBy: "担当" },
  confirm: { kind: "row_match", itemId: 4, recordedBy: "担当" },
  undoConfirmation: { confirmationId: 3, recordedBy: "担当" },
  judge: {
    questionId: 5,
    status: "judged",
    resolution: "unresolved",
    recordedBy: "担当",
  },
};
const names = [
  "edit",
  "undoEdit",
  "confirm",
  "undoConfirmation",
  "judge",
] as const;
it.each(
  names.flatMap((name) => [200, 409, 404].map((status) => ({ name, status }))),
)(
  "$name / $status は同じquery clientで必要なデータを再取得する",
  async ({ name, status }) => {
    const client = createTestQueryClient();
    const { result } = renderHookWithProviders(
      () => ({
        summary: useVersion(9),
        items: useItems(9),
        questions: useQuestions(9),
        mutations: useRecordMutations(9),
      }),
      client,
    );
    await waitFor(() =>
      expect(
        result.current.summary.isSuccess &&
          result.current.items.isSuccess &&
          result.current.questions.isSuccess,
      ).toBe(true),
    );
    const next = { ...version, counts: { ...version.counts, editCount: 88 } };
    mock.getVersion.mockResolvedValue(next);
    mock.listItems.mockResolvedValue([{ ...item, rowCode: "changed" }]);
    mock.listQuestions.mockResolvedValue([{ ...question, reason: "changed" }]);
    const method = name === "edit" ? mock.editItem : mock[name];
    if (status === 200) method.mockResolvedValue({} as never);
    else
      method.mockRejectedValue(
        new ApiError(status, {
          code: status === 409 ? "E_ALREADY_UNDONE" : "E_NOT_FOUND",
        }),
      );
    await act(async () => {
      try {
        await result.current.mutations[name].mutateAsync(inputs[name] as never);
      } catch {
        /* asserted below */
      }
    });
    await waitFor(() =>
      expect(client.getQueryData(versionKey(9))).toEqual(next),
    );
    if (name === "judge") {
      await waitFor(() =>
        expect(client.getQueryData(questionsKey(9))).toEqual([
          { ...question, reason: "changed" },
        ]),
      );
      expect(mock.listItems).toHaveBeenCalledTimes(1);
    } else {
      await waitFor(() =>
        expect(client.getQueryData(itemsKey(9))).toEqual([
          { ...item, rowCode: "changed" },
        ]),
      );
      expect(mock.listQuestions).toHaveBeenCalledTimes(1);
    }
    expect(method).toHaveBeenCalledTimes(1);
    if (status !== 200)
      expect(result.current.mutations[name].error).toMatchObject({ status });
  },
);
it("版履歴と根拠のキーを案件・版・行で分離する", async () => {
  const client = createTestQueryClient();
  const { result } = renderHookWithProviders(
    () => ({ history: useVersionHistory(8), evidence: useEvidence(9, 4) }),
    client,
  );
  await waitFor(() =>
    expect(
      result.current.history.isSuccess && result.current.evidence.isSuccess,
    ).toBe(true),
  );
  expect(versionsKey(8)).toEqual(["versions", 8]);
  expect(evidenceKey(9, 4)).toEqual(["version", 9, "items", 4, "evidence"]);
  expect(client.getQueryData(versionsKey(8))).toEqual([]);
  expect(client.getQueryData(evidenceKey(9, 4))).toEqual([]);
});
it("本番Providersの400 POSTは一度だけ、hookのretry:falseは既定retry設定にも優先する", async () => {
  const fetch = global.fetch;
  const request = jest.fn().mockResolvedValue({
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
    () => ({ mutations: useRecordMutations(9), client: useQueryClient() }),
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
          kind: "row_match",
          itemId: 4,
          recordedBy: "",
        }),
      ).rejects.toMatchObject({ code: "E_RECORDER_REQUIRED" });
    });
    expect(request).toHaveBeenCalledTimes(1);
  } finally {
    global.fetch = fetch;
  }
});
