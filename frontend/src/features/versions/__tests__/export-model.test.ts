import { parseExportFileName, exportErrorKey } from "../model";
import { ApiError } from "@/shared/api/mutator";

describe("parseExportFileName", () => {
  it("Content-Dispositionのfilenameを取り出す", () => {
    const headers = new Headers({
      "Content-Disposition": 'attachment; filename="S-01__v2_draft.xlsx"',
    });
    expect(parseExportFileName(headers)).toEqual({
      name: "S-01__v2_draft.xlsx",
      fromHeader: true,
    });
  });
  it("filename*（RFC5987）を優先して復号する", () => {
    const headers = new Headers({
      "Content-Disposition":
        "attachment; filename=\"fallback.xlsx\"; filename*=UTF-8''S-01__v2_draft.xlsx",
    });
    expect(parseExportFileName(headers)).toEqual({
      name: "S-01__v2_draft.xlsx",
      fromHeader: true,
    });
  });
  it("引用符なしのfilenameも読む", () => {
    const headers = new Headers({
      "Content-Disposition": "attachment; filename=plain.xlsx",
    });
    expect(parseExportFileName(headers).name).toBe("plain.xlsx");
  });
  it("ヘッダが無い・壊れているときは既定名にし、由来を区別できる", () => {
    expect(parseExportFileName(new Headers())).toEqual({
      name: "export.xlsx",
      fromHeader: false,
    });
    expect(
      parseExportFileName(new Headers({ "Content-Disposition": "attachment" })),
    ).toEqual({ name: "export.xlsx", fromHeader: false });
    expect(parseExportFileName(undefined)).toEqual({
      name: "export.xlsx",
      fromHeader: false,
    });
  });
  it("パス区切りを含む名前を単純名に落とす（保存先を誘導させない）", () => {
    const headers = new Headers({
      "Content-Disposition": 'attachment; filename="../../etc/passwd.xlsx"',
    });
    expect(parseExportFileName(headers).name).toBe("passwd.xlsx");
  });
});

describe("exportErrorKey", () => {
  it("APIのcodeごとに原因の分かる文言キーを返す", () => {
    expect(
      exportErrorKey(new ApiError(409, { code: "E_VERSION_NOT_FINALIZED" })),
    ).toBe("versions.export.errors.notFinalized");
    expect(exportErrorKey(new ApiError(404, { code: "E_NOT_FOUND" }))).toBe(
      "versions.export.errors.notFound",
    );
    expect(exportErrorKey(new Error("offline"))).toBe(
      "versions.export.errors.failed",
    );
  });
});
