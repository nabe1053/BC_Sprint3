import * as api from "../api";
import { ApiError } from "@/shared/api/mutator";
const original = global.fetch,
  request = jest.fn();
beforeEach(() => {
  request.mockReset();
  global.fetch = request;
});
afterAll(() => {
  global.fetch = original;
});
const operations = [
  ["listRecords", "records", "GET", undefined, 200],
  [
    "recordStateEvent",
    "state-events",
    "POST",
    { toState: "review_checked", recordedBy: "person" },
    201,
  ],
  [
    "recordBounceComment",
    "bounce-comments",
    "POST",
    { itemId: 4, comment: "<b>https://example.test</b>", recordedBy: "person" },
    201,
  ],
  ["recordBounce", "bounces", "POST", { recordedBy: "person" }, 201],
  [
    "recordSendoffDecision",
    "sendoff-decisions",
    "POST",
    { decision: "undecided", reason: null, recordedBy: "person" },
    201,
  ],
] as const;
it.each(operations)(
  "%sの実URL・method・body・成功応答",
  async (name, path, method, body, status) => {
    const response = { value: "synthetic" };
    request.mockResolvedValue({
      ok: true,
      status,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => response,
    });
    const fn = api[name as keyof typeof api] as (
      id: number,
      input: unknown,
    ) => Promise<unknown>;
    expect(await fn(9, body)).toEqual(response);
    expect(request.mock.calls[0][0]).toContain(`/api/v1/ui/versions/9/${path}`);
    expect(request.mock.calls[0][1].method).toBe(method);
    if (body) expect(JSON.parse(request.mock.calls[0][1].body)).toEqual(body);
    expect(request).toHaveBeenCalledTimes(1);
  },
);
it.each(operations)("%sは非2xxをApiErrorで1回だけ返す", async (name) => {
  request.mockResolvedValue({
    ok: false,
    status: 409,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => ({ code: "E_STATE_ORDER", message: "private" }),
  });
  const fn = api[name as keyof typeof api] as (
    id: number,
    input: unknown,
  ) => Promise<unknown>;
  const result = fn(9, {});
  await expect(result).rejects.toBeInstanceOf(ApiError);
  await expect(result).rejects.toMatchObject({
    status: 409,
    code: "E_STATE_ORDER",
  });
  expect(request).toHaveBeenCalledTimes(1);
});
