/**
 * F-15 RED: 案件一覧の行を展開したときの記録一覧（#28 の各記録を新しい順の1本の列に並べる）。
 */
import type { RecordsResponse } from "@/shared/api/generated/model";
import { recordTimeline } from "../model";

const empty: RecordsResponse = {
  edits: [],
  confirmations: [],
  judgements: [],
  stateEvents: [],
  bounces: [],
  unlinkedComments: [],
  sendoffDecisions: [],
};

it("各記録を種別つきで新しい順に並べ、取消を区別する", () => {
  const rows = recordTimeline({
    ...empty,
    edits: [
      {
        editId: 1,
        itemId: 4,
        field: "grade",
        oldValue: "K55",
        oldState: "stated",
        newValue: "L80",
        newState: "stated",
        reason: "原資料と照合",
        recordedBy: "担当",
        recordedAt: "2026-09-13T01:00:00Z",
        undoneAt: "2026-09-13T03:00:00Z",
        undoneBy: "取消者",
      },
    ],
    confirmations: [
      {
        confirmationId: 2,
        kind: "row_match",
        itemId: 4,
        recordedBy: "担当",
        recordedAt: "2026-09-13T02:00:00Z",
        undoneAt: null,
        undoneBy: null,
      },
      {
        confirmationId: 3,
        kind: "coverage",
        itemId: null,
        recordedBy: "担当",
        recordedAt: "2026-09-13T02:30:00Z",
        undoneAt: null,
        undoneBy: null,
      },
    ],
    judgements: [
      {
        judgementId: 4,
        questionId: 5,
        status: "judged",
        resolution: "resolved",
        note: null,
        recordedBy: "担当",
        recordedAt: "2026-09-13T04:00:00Z",
      },
    ],
    stateEvents: [
      {
        stateEventId: 5,
        fromState: "draft",
        toState: "staff_checked",
        recordedBy: "山田",
        recordedAt: "2026-09-13T05:00:00Z",
        unresolvedCount: 0,
      },
    ],
    bounces: [
      {
        bounceId: 6,
        reason: "R1: 数量",
        recordedBy: "上司",
        recordedAt: "2026-09-13T06:00:00Z",
        comments: [],
      },
    ],
    sendoffDecisions: [
      {
        sendoffDecisionId: 7,
        decision: "hold",
        reason: "確認中",
        recordedBy: "上司",
        recordedAt: "2026-09-13T07:00:00Z",
      },
    ],
  });
  expect(rows.map((row) => row.kind)).toEqual([
    "sendoff",
    "bounce",
    "state",
    "judgement",
    "coverage",
    "rowMatch",
    "edit",
  ]);
  expect(rows[0]).toMatchObject({ by: "上司", value: "hold" });
  expect(rows[2]).toMatchObject({ by: "山田", value: "staff_checked" });
  expect(rows[6]).toMatchObject({
    by: "担当",
    undone: { by: "取消者", at: "2026-09-13T03:00:00Z" },
  });
  expect(rows[5].undone).toBeNull();
});

it("同時刻は種別の記録 ID の降順で安定して並ぶ", () => {
  const at = "2026-09-13T01:00:00Z";
  const rows = recordTimeline({
    ...empty,
    judgements: [1, 2].map((judgementId) => ({
      judgementId,
      questionId: 5,
      status: "judged" as const,
      resolution: "unresolved" as const,
      note: null,
      recordedBy: `p${judgementId}`,
      recordedAt: at,
    })),
  });
  expect(rows.map((row) => row.by)).toEqual(["p2", "p1"]);
});

it("記録が無ければ空配列", () => {
  expect(recordTimeline(empty)).toEqual([]);
});
