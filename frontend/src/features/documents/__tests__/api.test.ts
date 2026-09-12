import { intakeDocument, listDocuments } from "../api";
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
it("HTTP201 multipart投入とHTTP200一覧を実クライアント経由で扱う", async () => {
  const file = new File(["source"], "a.txt", { type: "text/plain" });
  respond(201, { documentId: 7, readStatus: "partial" });
  expect(await intakeDocument(8, file)).toEqual({
    documentId: 7,
    readStatus: "partial",
  });
  const [url, request] = fetchMock.mock.calls[0];
  expect(url).toMatch(/\/api\/v1\/ui\/cases\/8\/documents$/);
  expect(request.body.get("file")).toBe(file);
  expect(request.headers.has("Content-Type")).toBe(false);
  respond(200, {
    documents: [
      { documentId: 7, fileName: "a.txt", kind: "text", readStatus: "partial" },
    ],
  });
  expect(await listDocuments(8)).toHaveLength(1);
});
it.each(["file_size", "document_count", "pdf_pages", "xlsx_sheets"])(
  "HTTP413 %s の契約を保持して1回で失敗する",
  async (limit) => {
    const details = { limit, max: 20, actual: 25 };
    respond(413, { code: "E_LIMIT_EXCEEDED", details });
    await expect(
      intakeDocument(8, new File(["a"], "a.pdf")),
    ).rejects.toMatchObject({ status: 413, code: "E_LIMIT_EXCEEDED", details });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  },
);
it("HTTP415の記録済みdocumentIdを保持する", async () => {
  respond(415, { code: "E_UNSUPPORTED_FORMAT", details: { documentId: 9 } });
  const response = intakeDocument(8, new File(["a"], "a.zip"));
  await expect(response).rejects.toBeInstanceOf(ApiError);
  await expect(response).rejects.toMatchObject({
    status: 415,
    details: { documentId: 9 },
  });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
