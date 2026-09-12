import * as api from "../api";
import { ApiError } from "@/shared/api/mutator";
import { inventory } from "../testing/fixtures";
const original = global.fetch,
  request = jest.fn();
beforeEach(() => {
  request.mockReset();
  global.fetch = request;
});
afterAll(() => {
  global.fetch = original;
});
function respond(status: number, data: unknown) {
  request.mockResolvedValue({
    ok: status === 200,
    status,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => data,
  });
}
it("#27 は生成GETの200を並べ替えず返す", async () => {
  respond(200, inventory);
  expect(await api.getInventory(9)).toEqual(inventory);
  expect(request.mock.calls[0][0]).toContain("/api/v1/ui/versions/9/inventory");
  expect(request.mock.calls[0][1].method).toBe("GET");
});
it.each([404, 500])("#27 の%sはApiErrorで1回のみ", async (status) => {
  respond(status, { code: "E_NOT_FOUND", message: "private" });
  const action = api.getInventory(9);
  await expect(action).rejects.toBeInstanceOf(ApiError);
  await expect(action).rejects.toMatchObject({ status });
  expect(request).toHaveBeenCalledTimes(1);
});
