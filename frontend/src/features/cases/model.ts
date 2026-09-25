/**
 * features/cases/model.ts — 案件一覧の純粋関数（F-15）。
 *
 * 版の記録（#28）を種別ごとの配列から、新しい順の 1 本の列に並べる。
 * 同時刻は種別をまたいで順序を決められないため、記録 ID の降順で安定させる。
 */
import type { RecordsResponse } from "@/shared/api/generated/model";

export type TimelineKind =
  | "edit"
  | "rowMatch"
  | "coverage"
  | "judgement"
  | "state"
  | "bounce"
  | "sendoff";

export type TimelineEntry = {
  key: string;
  kind: TimelineKind;
  by: string;
  at: string;
  /** 状態は遷移先、送付可否は判断、判断は解決状態。その他は null。 */
  value: string | null;
  undone: { by: string | null; at: string } | null;
};

const undone = (row: { undoneAt: string | null; undoneBy: string | null }) =>
  row.undoneAt ? { by: row.undoneBy, at: row.undoneAt } : null;

export function recordTimeline(records: RecordsResponse): TimelineEntry[] {
  const rows: (TimelineEntry & { id: number })[] = [
    ...records.edits.map((r) => ({
      key: `edit-${r.editId}`,
      id: r.editId,
      kind: "edit" as const,
      by: r.recordedBy,
      at: r.recordedAt,
      value: null,
      undone: undone(r),
    })),
    ...records.confirmations.map((r) => ({
      key: `confirmation-${r.confirmationId}`,
      id: r.confirmationId,
      kind:
        r.kind === "coverage" ? ("coverage" as const) : ("rowMatch" as const),
      by: r.recordedBy,
      at: r.recordedAt,
      value: null,
      undone: undone(r),
    })),
    ...records.judgements.map((r) => ({
      key: `judgement-${r.judgementId}`,
      id: r.judgementId,
      kind: "judgement" as const,
      by: r.recordedBy,
      at: r.recordedAt,
      value: r.resolution,
      undone: null,
    })),
    ...records.stateEvents.map((r) => ({
      key: `state-${r.stateEventId}`,
      id: r.stateEventId,
      kind: "state" as const,
      by: r.recordedBy,
      at: r.recordedAt,
      value: r.toState,
      undone: null,
    })),
    ...records.bounces.map((r) => ({
      key: `bounce-${r.bounceId}`,
      id: r.bounceId,
      kind: "bounce" as const,
      by: r.recordedBy,
      at: r.recordedAt,
      value: null,
      undone: null,
    })),
    ...records.sendoffDecisions.map((r) => ({
      key: `sendoff-${r.sendoffDecisionId}`,
      id: r.sendoffDecisionId,
      kind: "sendoff" as const,
      by: r.recordedBy,
      at: r.recordedAt,
      value: r.decision,
      undone: null,
    })),
  ];
  return rows
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at) || b.id - a.id)
    .map(({ id: _id, ...entry }) => entry);
}
