import * as api from "../api";
import { ApiError } from "@/shared/api/mutator";
const originalFetch = global.fetch;
const request = jest.fn();
beforeEach(() => {
  request.mockReset();
  global.fetch = request;
});
afterAll(() => {
  global.fetch = originalFetch;
});
function respond(status: number, data: unknown) {
  request.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => data,
  });
}
it.each([
  [() => api.listVersions(8), "/cases/8/versions", { versions: [] }, []],
  [() => api.getVersion(9), "/versions/9", { versionId: 9 }, { versionId: 9 }],
  [() => api.listItems(9), "/versions/9/items", { items: [] }, []],
  [() => api.listQuestions(9), "/versions/9/questions", { questions: [] }, []],
  [
    () => api.listEvidence(9, 4),
    "/versions/9/items/4/evidence",
    { itemId: 4, evidences: [] },
    [],
  ],
])(
  "GET200を生成クライアントで解包する: %#",
  async (call, path, response, expected) => {
    respond(200, response);
    expect(await call()).toEqual(expected);
    expect(request.mock.calls[0][0]).toContain("/api/v1/ui" + path);
    expect(request.mock.calls[0][1].method).toBe("GET");
  },
);
it("訂正201で10進文字列とcamelCaseのみを送り応答日時を受け取る", async () => {
  const input = {
    itemId: 4,
    field: "qty_value" as const,
    newValue: "9007199254740993.0010",
    newState: "numeric" as const,
    qtyUnit: "本",
    reason: "照合",
    recordedBy: "担当",
  };
  const result = { edits: [{ editId: 2, recordedAt: "2026-09-13T01:00:00Z" }] };
  respond(201, result);
  expect(await api.editItem(9, input)).toEqual(result.edits);
  expect(JSON.parse(request.mock.calls[0][1].body)).toEqual(input);
  expect(request.mock.calls[0][1].body).not.toContain("recordedAt");
  expect(request.mock.calls[0][1].method).toBe("POST");
});
it.each([
  [
    () => api.undoEdit(9, 2, { recordedBy: "担当" }),
    "/versions/9/edits/2/undo",
    200,
  ],
  [
    () => api.confirm(9, { kind: "row_match", itemId: 4, recordedBy: "担当" }),
    "/versions/9/confirmations",
    201,
  ],
  [
    () => api.undoConfirmation(9, 3, { recordedBy: "担当" }),
    "/versions/9/confirmations/3/undo",
    200,
  ],
  [
    () =>
      api.judge(9, 5, {
        status: "judged",
        resolution: "unresolved",
        recordedBy: "担当",
        note: "照会",
      }),
    "/versions/9/questions/5/judgements",
    201,
  ],
])("記録と取消の成功statusを区別する: %#", async (call, path, status) => {
  respond(status, { recordedBy: "担当" });
  expect(await call()).toEqual({ recordedBy: "担当" });
  expect(request.mock.calls[0][0]).toContain("/api/v1/ui" + path);
  expect(request.mock.calls[0][1].method).toBe("POST");
  expect(JSON.parse(request.mock.calls[0][1].body).recordedBy).toBe("担当");
});
it.each([
  [400, "E_RECORDER_REQUIRED"],
  [409, "E_ALREADY_CONFIRMED"],
  [404, "E_NOT_FOUND"],
  [500, "E_INTERNAL"],
])("非2xx %sを再送せずApiErrorにする", async (status, code) => {
  respond(status, { code, message: "private", details: { input: "private" } });
  const promise = api.confirm(9, {
    kind: "row_match",
    itemId: 4,
    recordedBy: "担当",
  });
  await expect(promise).rejects.toBeInstanceOf(ApiError);
  await expect(promise).rejects.toMatchObject({ status, code });
  expect(request).toHaveBeenCalledTimes(1);
});
