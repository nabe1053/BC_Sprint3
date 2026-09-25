import {
  rowState,
  filterItems,
  emptyFilters,
  previousValue,
  buildEditRequest,
  valueLabelKey,
  recordErrorKey,
  evidenceKey,
} from "../model";
import { item, edit, question } from "../testing/fixtures";
import { ApiError } from "@/shared/api/mutator";

it.each([
  [
    { ...item, groupCode: "G1", isInheritCandidate: true },
    [question],
    "tba",
    "warn",
  ],
  [
    { ...item, qtyState: "numeric", groupCode: "G1", isInheritCandidate: true },
    [question],
    "choice",
    "warn",
  ],
  [
    { ...item, qtyState: "numeric", isInheritCandidate: true },
    [question],
    "inherit",
    "warn",
  ],
  [{ ...item, qtyState: "numeric" }, [question], "questions", "warn"],
  [{ ...item, qtyState: "numeric" }, [], "clear", "ok"],
] as const)(
  "状態の優先順を文字とトーンで表す %#",
  (row, questions, key, tone) => {
    expect(rowState(row, questions)).toEqual({
      key: `versions.rowState.${key}`,
      tone,
    });
  },
);
it.each([
  "all",
  "questions",
  "tba",
  "choice",
  "unmatched",
  "edited",
  "unresolved",
] as const)("状態フィルタ %s は該当行だけを残す", (status) => {
  const target = { ...item, groupCode: "G1", history: [edit] };
  const other = {
    ...item,
    itemId: 7,
    qtyState: "numeric" as const,
    rowMatch: {
      confirmationId: 8,
      recordedBy: "担当",
      recordedAt: edit.recordedAt,
    },
  };
  const rows = filterItems([target, other], [question], {
    ...emptyFilters,
    status,
  });
  expect(rows.map((x) => x.itemId)).toEqual(status === "all" ? [4, 7] : [4]);
});
it("キーワードと3列をAND検索し、判断済み未解決を残す", () => {
  const judged = {
    ...question,
    latest: {
      judgementId: 1,
      questionId: 5,
      status: "judged" as const,
      resolution: "unresolved" as const,
      note: "照会",
      recordedBy: "担当",
      recordedAt: edit.recordedAt,
    },
  };
  expect(
    filterItems([item], [judged], {
      ...emptyFilters,
      status: "unresolved",
      keyword: " casing ",
      kind: "Casing",
      grade: "K55",
      connection: "",
    }),
  ).toEqual([item]);
  expect(
    filterItems([item], [judged], { ...emptyFilters, grade: "L80" }),
  ).toEqual([]);
});
it("訂正の旧値は取消済みを無視し数量と単位を分ける", () => {
  const history = [
    edit,
    { ...edit, editId: 3, field: "qty_unit" as const, oldValue: "本" },
    { ...edit, editId: 4, oldValue: "private", undoneAt: edit.recordedAt },
  ];
  expect(previousValue(history, "qty_value")).toEqual({
    value: "10.00",
    state: "numeric",
  });
  expect(previousValue(history, "qty_unit")).toEqual({
    value: "本",
    state: "numeric",
  });
  expect(previousValue(history, "grade")).toBeNull();
});
it.each(["tba", "not_stated", "not_applicable"])(
  "%s は空欄や0にならない",
  (state) => expect(valueLabelKey(state)).toBe(`versions.values.${state}`),
);
const draft = {
  field: "qty_value",
  state: "numeric",
  value: "9007199254740993.0010",
  qtyUnit: "本",
  reason: " 照合 ",
  recordedBy: " 担当 ",
};
it("数値文字列を丸めず数量単位と要求を組み立てる", () =>
  expect(buildEditRequest(4, draft)).toEqual({
    itemId: 4,
    field: "qty_value",
    newState: "numeric",
    newValue: draft.value,
    qtyUnit: "本",
    reason: "照合",
    recordedBy: "担当",
  }));
it.each(["tba", "not_stated", "not_applicable"])(
  "状態のみ %s にはnewValueもqtyUnitも載せない",
  (state) => {
    const request = buildEditRequest(4, { ...draft, state });
    expect(request).toEqual({
      itemId: 4,
      field: "qty_value",
      newState: state,
      reason: "照合",
      recordedBy: "担当",
    });
  },
);
it.each(["kind", "usage_note", "note"])("%s にnewStateは載せない", (field) =>
  expect(buildEditRequest(4, { ...draft, field, value: "文字" })).toEqual({
    itemId: 4,
    field,
    newValue: "文字",
    reason: "照合",
    recordedBy: "担当",
  }),
);
it.each([
  [{ reason: " " }, "E_REASON_REQUIRED"],
  [{ recordedBy: " " }, "E_RECORDER_REQUIRED"],
  [{ qtyUnit: "" }, "E_QTY_UNIT_REQUIRED"],
  [{ value: "4/5" }, "E_STATE_VALUE_CONFLICT"],
  [{ value: "" }, "E_STATE_VALUE_CONFLICT"],
  [{ field: "grade_raw" }, "E_FIELD_NOT_EDITABLE"],
])("クライアントで不正要求を止める %#", (change, code) =>
  expect(() => buildEditRequest(4, { ...draft, ...change })).toThrow(code),
);
it("API本文やdetailsを文言に使わない", () => {
  expect(
    recordErrorKey(
      new ApiError(400, {
        code: "E_REQUEST_INVALID",
        message: "secret",
        details: { input: "secret" },
      }),
    ),
  ).toBe("versions.errors.E_REQUEST_INVALID");
  expect(recordErrorKey(new Error("secret"))).toBe("versions.errors.unknown");
});

describe("evidenceKey: 根拠の対象項目を表示グループに正規化する（TEST-04 #3・TEST-05 #2）", () => {
  it.each([
    ["qty", "qty"],
    ["qtyRaw", "qty"],
    ["qty_value", "qty"],
    ["qty_reference_note", "qty"],
    ["od", "od"],
    ["odRaw", "od"],
    ["od_unit", "od"],
    ["weightRaw", "weight"],
    ["kindRaw", "kind"],
    ["gradeRaw", "grade"],
    ["connectionRaw", "connection"],
    ["length", "length"],
    ["lengthRaw", "length"],
    ["rangeClass", "length"],
    ["range_class", "length"],
    ["due", "due"],
    ["dueRaw", "due"],
    ["place_raw", "place"],
    ["usageNote", "usage_note"],
    ["note", "note"],
  ])("%s → %s", (field, key) => {
    expect(evidenceKey(field)).toBe(key);
  });

  it.each(["end_a.od", "end_b.thread_end", "incoterms", ""])(
    "表示グループに無い %s は null（その他の根拠として別に出す）",
    (field) => {
      expect(evidenceKey(field)).toBeNull();
    },
  );
});
it("CFL-n の候補行は択一ではなく資料の矛盾として状態を分ける（X04・04-db group_code）", () => {
  expect(
    rowState({ ...item, qtyState: "numeric", groupCode: "CFL-2" }, []),
  ).toEqual({ key: "versions.rowState.conflict", tone: "warn" });
  expect(
    rowState({ ...item, qtyState: "numeric", groupCode: "ALT-1" }, []),
  ).toEqual({ key: "versions.rowState.choice", tone: "warn" });
});

it("絞り込み「択一・矛盾の候補」は ALT 行と CFL 行の両方を残す", () => {
  const rows = [
    { ...item, itemId: 1, groupCode: "ALT-1" },
    { ...item, itemId: 2, groupCode: "CFL-2" },
    { ...item, itemId: 3, groupCode: null },
  ];
  expect(
    filterItems(rows, [], { ...emptyFilters, status: "choice" }).map(
      (row) => row.itemId,
    ),
  ).toEqual([1, 2]);
});
