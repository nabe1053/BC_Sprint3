import { createCase, listCases, getCase } from "../api";
import { ApiError } from "@/shared/api/mutator";

const originalFetch = global.fetch;
const fetchMock = jest.fn();
beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock;
});
afterAll(() => {
  global.fetch = originalFetch;
});
function respond(status: number, body: unknown) {
  fetchMock.mockResolvedValue({
    ok: status < 300,
    status,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => body,
  });
}
it("実クライアントがGET200一覧・詳細とPOST201をunwrapする", async () => {
  const item = {
    caseId: 8,
    caseCode: "NEW",
    title: null,
    customerName: null,
    createdAt: "2026-09-12",
  };
  respond(200, { cases: [item] });
  expect(await listCases()).toEqual([item]);
  respond(200, item);
  expect(await getCase(8)).toEqual(item);
  expect(fetchMock.mock.calls.at(-1)[0]).toMatch(/\/api\/v1\/ui\/cases\/8$/);
  respond(201, item);
  expect(await createCase({ caseCode: "NEW" })).toEqual(item);
  expect(JSON.parse(fetchMock.mock.calls.at(-1)[1].body)).toEqual({
    caseCode: "NEW",
  });
});
it("HTTP409はApiErrorとしてUI境界へ伝える", async () => {
  respond(409, { code: "E_DUPLICATE_CASE_CODE" });
  await expect(createCase({ caseCode: "DUP" })).rejects.toBeInstanceOf(
    ApiError,
  );
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
