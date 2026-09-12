import { startAgentRun, getAgentRun, getAgentRunSteps } from "../api";
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
it("起動はPOST202をunwrapしcamelCaseの明示確認だけを送る", async () => {
  const accepted = {
    runId: 3,
    versionId: 9,
    startedAt: "2026-09-12T12:00:00Z",
  };
  respond(202, accepted);
  expect(await startAgentRun(8, { acknowledgedCarryOver: true })).toEqual(
    accepted,
  );
  expect(request.mock.calls[0][0]).toMatch(
    /\/api\/v1\/ui\/cases\/8\/agent-runs$/,
  );
  expect(JSON.parse(request.mock.calls[0][1].body)).toEqual({
    acknowledgedCarryOver: true,
  });
  expect(request).toHaveBeenCalledTimes(1);
});
it("GET200進捗とstepsを実生成クライアントで取得しsignalを渡す", async () => {
  const signal = new AbortController().signal;
  respond(200, { runId: 3, outcome: "running" });
  expect(await getAgentRun(3, signal)).toMatchObject({ runId: 3 });
  expect(request.mock.calls[0][1].signal).toBe(signal);
  respond(200, { steps: [{ stepId: 8, seq: 1 }] });
  expect(await getAgentRunSteps(3, signal)).toEqual([{ stepId: 8, seq: 1 }]);
  expect(request.mock.calls[1][0]).toMatch(
    /\/api\/v1\/ui\/agent-runs\/3\/steps$/,
  );
});
it.each([
  [400, "E_NO_READABLE_DOCUMENT"],
  [400, "E_CARRY_OVER_NOT_ACKNOWLEDGED"],
  [409, "E_RUN_IN_PROGRESS"],
  [413, "E_LIMIT_EXCEEDED"],
  [503, "E_EXTERNAL_SEND_NOT_APPROVED"],
  [503, "E_JOB_START_FAILED"],
])("POST %s %s の実応答をApiErrorとして1回で伝える", async (status, code) => {
  respond(status, {
    code,
    details: { kind: "documents", actual: 51, limit: 50 },
  });
  const result = startAgentRun(8, {});
  await expect(result).rejects.toBeInstanceOf(ApiError);
  await expect(result).rejects.toMatchObject({ status, code });
  expect(request).toHaveBeenCalledTimes(1);
});
it("GET404は新しいrunの作成を伴わない", async () => {
  respond(404, { code: "E_NOT_FOUND" });
  await expect(getAgentRun(3)).rejects.toMatchObject({ status: 404 });
  expect(request).toHaveBeenCalledTimes(1);
});
it("別runIdの応答を進捗として受け入れない", async () => {
  respond(200, { runId: 99, outcome: "running" });
  await expect(getAgentRun(3)).rejects.toMatchObject({
    code: "E_UNEXPECTED_RESPONSE",
  });
});
