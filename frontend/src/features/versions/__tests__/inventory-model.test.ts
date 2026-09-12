import {
  sortEntries,
  sortItems,
  inventoryState,
  inventoryCounts,
  documentNames,
  buildCoverageRequest,
  inventoryErrorKey,
} from "../model";
import { inventory } from "../testing/fixtures";
import { ApiError } from "@/shared/api/mutator";
it("資料側は不整合・欠落・seq/id、入力を変えない", () => {
  const input = [...inventory.entries].reverse();
  const before = [...input];
  expect(sortEntries(input).map((row) => row.entryId)).toEqual([
    15, 14, 11, 12, 13,
  ]);
  expect(input).toEqual(before);
  const ties = [
    { ...inventory.entries[0], seq: 1, entryId: 30 },
    { ...inventory.entries[0], seq: 1, entryId: 20 },
  ];
  expect(sortEntries(ties).map((row) => row.entryId)).toEqual([20, 30]);
});
it("明細側は対応元なし・seq/id、入力を変えない", () => {
  const input = [...inventory.items].reverse();
  const before = [...input];
  expect(sortItems(input).map((row) => row.rowCode)).toEqual([
    "R3",
    "R1",
    "R2",
  ]);
  expect(input).toEqual(before);
});
it.each([
  ["inconsistent", "danger"],
  ["missing", "warn"],
  ["mapped", "ok"],
  ["split", "ok"],
  ["excluded", null],
] as const)("%sの文字とトーン", (state, tone) =>
  expect(inventoryState(state)).toEqual({
    key: `versions.inventory.judgement.${state}`,
    tone,
  }),
);
it("9件数は3数値と6配列長であり行照合から推測しない", () =>
  expect(inventoryCounts(inventory.summary)).toEqual({
    sourceEntry: 5,
    sourceItem: 4,
    outputRow: 3,
    split: 1,
    excluded: 1,
    unmapped: 1,
    orphan: 1,
    multiMapped: 1,
    inconsistent: 2,
  }));
it("資料名は初出順distinct、未解決名をnullで保つ", () =>
  expect(documentNames(inventory.entries)).toEqual(["明細.pdf", null]));
it("coverage要求は名前とkindだけ、IDと時刻なし", () =>
  expect(buildCoverageRequest("  確認者  ")).toEqual({
    kind: "coverage",
    recordedBy: "確認者",
  }));
it.each(["", " \n\t "])("空白名はクライアントで拒否 %p", (name) =>
  expect(() => buildCoverageRequest(name)).toThrow(
    expect.objectContaining({ code: "E_RECORDER_REQUIRED" }),
  ),
);
it("既存確認の競合は網羅性向けの文言にする", () =>
  expect(
    inventoryErrorKey(new ApiError(409, { code: "E_ALREADY_CONFIRMED" })),
  ).toBe("versions.inventory.errors.E_ALREADY_CONFIRMED"));
it.each([
  "E_RECORDER_REQUIRED",
  "E_ALREADY_UNDONE",
  "E_NOT_FOUND",
  "E_TARGET_INVALID",
])("既知%sは既存文言へ", (code) =>
  expect(inventoryErrorKey(new ApiError(400, { code }))).toBe(
    `versions.errors.${code}`,
  ),
);
it.each([new Error("private"), new ApiError(500, { code: "private" })])(
  "未知エラーは固定文言",
  (error) => expect(inventoryErrorKey(error)).toBe("versions.errors.unknown"),
);
