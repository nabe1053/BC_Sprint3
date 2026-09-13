import {
  createExportApiV1UiVersionsVersionIdExportsPost,
  listExportsApiV1UiVersionsVersionIdExportsGet,
  listVersionEvidenceApiV1UiVersionsVersionIdEvidenceGet,
} from "../generated/ui";
import { ApiError, customInstance } from "../mutator";

const original = global.fetch;
afterEach(() => {
  global.fetch = original;
});

it("出力の生成関数は本文なしPOSTでBlob・ファイル名・出力IDを返す", async () => {
  const blob = new Blob([new Uint8Array([80, 75, 3, 4, 0, 255])], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const headers = new Headers({
    "Content-Type": blob.type,
    "Content-Disposition": 'attachment; filename="synthetic.xlsx"',
    "X-Export-Id": "17",
  });
  const readBlob = jest.fn().mockResolvedValue(blob),
    readJson = jest.fn();
  const request = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers,
    blob: readBlob,
    json: readJson,
  });
  global.fetch = request;
  const result = await createExportApiV1UiVersionsVersionIdExportsPost(9);
  expect(result.status).toBe(200);
  if (result.status !== 200) throw new Error("Expected binary success");
  const received: Blob = result.data;
  expect(received).toBe(blob);
  expect(received.size).toBe(6);
  expect(result.headers.get("Content-Disposition")).toBe(
    'attachment; filename="synthetic.xlsx"',
  );
  expect(result.headers.get("X-Export-Id")).toBe("17");
  expect(request).toHaveBeenCalledTimes(1);
  const [url, options] = request.mock.calls[0];
  expect(url).toBe("http://localhost:8000/api/v1/ui/versions/9/exports");
  expect(options.method).toBe("POST");
  expect(options.body).toBeUndefined();
  expect(readBlob).toHaveBeenCalledTimes(1);
  expect(readJson).not.toHaveBeenCalled();
});

it.each([400, 404, 409, 422, 500])(
  "出力%s JSONエラーをApiErrorにしBlob化・リトライしない",
  async (status) => {
    const body = {
      code: "E_VERSION_NOT_FINALIZED",
      message: "未確定です",
      details: {},
    };
    const readBlob = jest.fn(),
      readJson = jest.fn().mockResolvedValue(body);
    const request = jest.fn().mockResolvedValue({
      ok: false,
      status,
      headers: new Headers({ "Content-Type": "application/json" }),
      blob: readBlob,
      json: readJson,
    });
    global.fetch = request;
    await expect(
      createExportApiV1UiVersionsVersionIdExportsPost(9),
    ).rejects.toMatchObject({
      status,
      code: body.code,
      message: body.message,
      details: {},
    });
    expect(request).toHaveBeenCalledTimes(1);
    expect(readJson).toHaveBeenCalledTimes(1);
    expect(readBlob).not.toHaveBeenCalled();
  },
);

it("非JSON失敗もApiErrorとして1回だけ返す", async () => {
  const readBlob = jest.fn();
  const request = jest.fn().mockResolvedValue({
    ok: false,
    status: 503,
    headers: new Headers({ "Content-Type": "text/plain" }),
    blob: readBlob,
  });
  global.fetch = request;
  await expect(
    createExportApiV1UiVersionsVersionIdExportsPost(9),
  ).rejects.toBeInstanceOf(ApiError);
  expect(readBlob).not.toHaveBeenCalled();
  expect(request).toHaveBeenCalledTimes(1);
});

it.each([
  ["exports", listExportsApiV1UiVersionsVersionIdExportsGet, { exports: [] }],
  [
    "evidence",
    listVersionEvidenceApiV1UiVersionsVersionIdEvidenceGet,
    { evidences: [] },
  ],
] as const)("%sの生成GETは既存JSONを保持", async (suffix, read, data) => {
  const request = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ "Content-Type": "application/json" }),
    json: async () => data,
  });
  global.fetch = request;
  const result = await read(9);
  expect(result).toMatchObject({ status: 200, data });
  expect(request.mock.calls[0][0]).toBe(
    `http://localhost:8000/api/v1/ui/versions/9/${suffix}`,
  );
  expect(request.mock.calls[0][1].method).toBe("GET");
});

it("既存JSON mutatorの204は本文undefinedを維持", async () => {
  const readBlob = jest.fn();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 204,
    headers: new Headers(),
    blob: readBlob,
  });
  await expect(
    customInstance("/api/v1/ui/synthetic", { method: "POST" }),
  ).resolves.toMatchObject({ status: 204, data: undefined });
  expect(readBlob).not.toHaveBeenCalled();
});
