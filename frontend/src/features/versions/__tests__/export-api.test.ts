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

it("createExportは実URLへbody無しでPOSTし、Blobとファイル名を返す", async () => {
  const blob = new Blob(["xlsx"], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  request.mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({
      "Content-Type":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition": 'attachment; filename="S-01__v2_draft.xlsx"',
      "X-Export-Id": "12",
    }),
    blob: async () => blob,
  });
  const result = await api.createExport(7);
  const [url, init] = request.mock.calls[0];
  expect(url).toContain("/api/v1/ui/versions/7/exports");
  expect(init.method).toBe("POST");
  expect(init.body).toBeUndefined();
  expect(result.blob).toBe(blob);
  expect(result.fileName).toBe("S-01__v2_draft.xlsx");
});

it("createExportの非2xxはApiErrorのcodeを保つ", async () => {
  request.mockResolvedValue({
    ok: false,
    status: 409,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => ({ code: "E_VERSION_NOT_FINALIZED" }),
  });
  await expect(api.createExport(7)).rejects.toMatchObject({
    code: "E_VERSION_NOT_FINALIZED",
    status: 409,
  });
});

it("createExportは想定外の成功statusを成功として流さない", async () => {
  request.mockResolvedValue({
    ok: true,
    status: 204,
    headers: new Headers(),
    blob: async () => new Blob(),
  });
  await expect(api.createExport(7)).rejects.toBeInstanceOf(ApiError);
});

it("listExportsは出力履歴の配列を返す", async () => {
  const exports = [{ exportId: 1, fileName: "a.xlsx", integrity: "intact" }];
  request.mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => ({ exports }),
  });
  await expect(api.listExports(7)).resolves.toEqual(exports);
  expect(request.mock.calls[0][1].method).toBe("GET");
});
