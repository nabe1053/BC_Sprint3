import * as model from "../model";
import { approvalData, item, version } from "../testing/fixtures";
import { ApiError } from "@/shared/api/mutator";

it("要約7値は個別API材料から取り、コメントは未紐付けだけ数える", () => {
  const d = approvalData();
  d.records.bounces = [
    {
      bounceId: 1,
      reason: "past",
      recordedBy: "old",
      recordedAt: "old",
      comments: [{ ...d.records.unlinkedComments[0], bounceId: 1 }],
    },
  ];
  expect(model.findVersionListItem([d.listItem], 9)).toBe(d.listItem);
  expect(model.findVersionListItem([d.listItem], 99)).toBeUndefined();
  expect(model.approvalSummary(d.version, d.listItem, d.records)).toEqual({
    state: "staff_checked",
    sendoff: "undecided",
    noSendoff: true,
    matched: 1,
    total: 2,
    coverage: true,
    edits: 1,
    unresolved: 2,
    bounceComments: 1,
    bounced: false,
    needsRecheck: false,
  });
});
it("記録者は最新staff/reviewと未取消coverage、入力を変更しない", () => {
  const d = approvalData();
  d.records.confirmations.push({
    ...d.records.confirmations[0],
    confirmationId: 99,
    recordedBy: "取消済み",
    undoneAt: "later",
  });
  d.records.stateEvents.push(
    { ...d.records.stateEvents[0], stateEventId: 51, recordedBy: "再確認担当" },
    {
      ...d.records.stateEvents[0],
      stateEventId: 52,
      fromState: "staff_checked",
      toState: "review_checked",
      recordedBy: "評価者",
    },
  );
  const before = JSON.stringify(d.records);
  expect(model.recorderMeta(d.records)).toMatchObject({
    staff: { recordedBy: "再確認担当" },
    coverage: { recordedBy: "網羅担当" },
    review: { recordedBy: "評価者" },
  });
  expect(JSON.stringify(d.records)).toBe(before);
  expect(
    model.recorderMeta({ ...d.records, stateEvents: [], confirmations: [] }),
  ).toEqual({ staff: null, coverage: null, review: null });
});
it("変更タグ5種と取消除外、未解決述語・5絞り込みが既存表示と一致", () => {
  const d = approvalData(),
    before = JSON.stringify(d);
  expect(model.changeTags(d.items[0], d.questions)).toEqual([
    "choice",
    "tba",
    "inherit",
    "edited",
    "judged",
  ]);
  expect(model.hasChanges({ ...item, qtyState: "not_stated" }, [])).toBe(false);
  expect(
    model.changeTags(
      {
        ...item,
        qtyState: "not_stated",
        history: [{ ...d.records.edits[0], undoneAt: "cancelled" }],
      },
      [],
    ),
  ).toEqual([]);
  expect(model.unresolvedQuestions(d.questions)).toHaveLength(2);
  expect(model.rowUnresolved(d.questions, 4)).toHaveLength(1);
  expect(model.caseLevelUnresolved(d.questions)).toHaveLength(1);
  expect(model.rowBounceComments(d.records, 4)).toEqual(
    d.records.unlinkedComments,
  );
  expect(model.approvalFilters).toEqual([
    "all",
    "changes",
    "edited",
    "unresolved",
    "bounce",
  ]);
  for (const filter of model.approvalFilters)
    expect(
      model.filterApprovalRows(d.items, d.questions, d.records, filter),
    ).toHaveLength(filter === "all" ? 2 : 1);
  expect(
    model.filterApprovalRows(d.items, d.questions, d.records, "unresolved"),
  ).toEqual(
    model.filterItems(d.items, d.questions, {
      ...model.emptyFilters,
      status: "unresolved",
    }),
  );
  expect(JSON.stringify(d)).toBe(before);
});
it.each(["draft", "staff_checked", "review_checked"] as const)(
  "canReview %s",
  (state) => {
    expect(model.canReview(state)).toBe(
      {
        draft: "incomplete",
        staff_checked: "ready",
        review_checked: "reviewed",
      }[state],
    );
  },
);
it("要求は名前から検査し採時を含めず、未判断の空理由をnullにする", () => {
  expect(() => model.buildStateEventRequest("staff_checked", " ")).toThrow(
    "E_RECORDER_REQUIRED",
  );
  expect(model.buildStateEventRequest("review_checked", " 人 ")).toEqual({
    toState: "review_checked",
    recordedBy: "人",
  });
  expect(() => model.buildBounceCommentRequest(4, " ", " ")).toThrow(
    "E_RECORDER_REQUIRED",
  );
  expect(() => model.buildBounceCommentRequest(4, " ", "人")).toThrow(
    "E_COMMENT_REQUIRED",
  );
  expect(model.buildBounceCommentRequest(4, " <b>link</b> ", "人")).toEqual({
    itemId: 4,
    comment: "<b>link</b>",
    recordedBy: "人",
  });
  expect(() => model.buildBounceRequest(" ", 0)).toThrow("E_RECORDER_REQUIRED");
  expect(() => model.buildBounceRequest("人", 0)).toThrow(
    "E_NO_BOUNCE_COMMENT",
  );
  expect(model.buildBounceRequest("人", 1)).toEqual({ recordedBy: "人" });
  expect(() => model.buildSendoffRequest("hold", "", " ")).toThrow(
    "E_RECORDER_REQUIRED",
  );
  expect(() => model.buildSendoffRequest("hold", " ", "人")).toThrow(
    "E_SENDOFF_REASON_REQUIRED",
  );
  expect(() => model.buildSendoffRequest("approved", " ", "人")).toThrow(
    "E_SENDOFF_REASON_REQUIRED",
  );
  expect(model.buildSendoffRequest("undecided", " ", " 人 ")).toEqual({
    decision: "undecided",
    reason: null,
    recordedBy: "人",
  });
  expect(model.buildSendoffRequest("approved", " 条件 ", "人")).toEqual({
    decision: "approved",
    reason: "条件",
    recordedBy: "人",
  });
});
it.each([
  "E_STAFF_CHECK_INCOMPLETE",
  "E_COVERAGE_NOT_RECORDED",
  "E_STATE_ORDER",
  "E_STATE_ROLLBACK_FORBIDDEN",
  "E_NO_BOUNCE_COMMENT",
  "E_SENDOFF_REASON_REQUIRED",
  "E_COMMENT_REQUIRED",
  "E_RECORDER_REQUIRED",
])("%sは承認文言へ、他は既存fallback", (code) => {
  expect(model.approvalErrorKey(new ApiError(409, { code }))).toBe(
    `versions.approval.errors.${code}`,
  );
});
it("状態詳細は行IDだけを抽出し内部IDや生メッセージを返さない", () => {
  const error = new ApiError(409, {
    code: "E_STAFF_CHECK_INCOMPLETE",
    message: "secret",
    details: {
      unmatchedItemIds: [98765],
      unmatchedRowCodes: ["R1", "R2"],
      coverageRecorded: false,
    },
  });
  expect(model.staffCheckDetails(error)).toEqual({
    rowCodes: ["R1", "R2"],
    coverageRecorded: false,
  });
  expect(
    model.approvalErrorKey(new ApiError(404, { code: "E_NOT_FOUND" })),
  ).toBe("versions.errors.E_NOT_FOUND");
  expect(model.approvalErrorKey(new Error("private"))).toBe(
    "versions.errors.unknown",
  );
  expect(model.staffCheckDetails(null)).toEqual({
    rowCodes: [],
    coverageRecorded: false,
  });
  expect(model.sendoffTone("hold")).toBe("warn");
  expect(model.sendoffTone("approved")).toBe("ok");
  expect(model.sendoffTone("undecided")).toBeNull();
  expect(model.stateTone(version.currentState)).toBeNull();
  expect(model.stateTone("review_checked")).toBe("ok");
});
it("変更タグは CFL-n を矛盾候補、それ以外のグループを択一として分ける（X04）", () => {
  expect(
    model.changeTags({ ...item, qtyState: "numeric", groupCode: "CFL-2" }, []),
  ).toEqual(["conflict"]);
  expect(
    model.changeTags({ ...item, qtyState: "numeric", groupCode: "ALT-1" }, []),
  ).toEqual(["choice"]);
});
