const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
const original = global.fetch;
afterEach(() => {
  if (configured === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
  else process.env.NEXT_PUBLIC_API_BASE_URL = configured;
  global.fetch = original;
  jest.resetModules();
});
it.each([
  [undefined, "http://localhost:8000"],
  ["https://api.example.test", "https://api.example.test"],
])("原資料リンク用baseURLはfetchと同じ（設定=%s）", async (value, expected) => {
  if (value === undefined) delete process.env.NEXT_PUBLIC_API_BASE_URL;
  else process.env.NEXT_PUBLIC_API_BASE_URL = value;
  jest.resetModules();
  const { apiBaseUrl, customInstance } = await import("../mutator");
  expect(apiBaseUrl).toBe(expected);
  const request = jest
    .fn()
    .mockResolvedValue({ ok: true, status: 204, headers: new Headers() });
  global.fetch = request;
  await customInstance("/api/v1/ui/documents/1/file");
  expect(request.mock.calls[0][0]).toBe(
    apiBaseUrl + "/api/v1/ui/documents/1/file",
  );
});
