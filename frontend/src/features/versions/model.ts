import type {
  RecordsResponse,
  VersionResponse,
  VersionListItem,
  StateEventRequest,
  BounceCommentRequest,
  BounceRequest,
  SendoffDecisionRequest,
  InventoryEntryResponse,
  InventoryItemResponse,
  InventorySummaryResponse,
  ConfirmationRequest,
  ItemCurrentResponse,
  ItemEditRecord,
  ItemEditRequest,
  QuestionResponse,
} from "@/shared/api/generated/model";
import { ApiError } from "@/shared/api/mutator";

export const editableFields = [
  "kind",
  "usage_note",
  "od_value",
  "od_unit",
  "wall_value",
  "wall_unit",
  "weight_value",
  "weight_unit",
  "grade",
  "connection",
  "range_class",
  "length_value",
  "length_unit",
  "qty_value",
  "qty_unit",
  "note",
] as const;
export type EditableField = (typeof editableFields)[number];

// 根拠ドロワーの表示グループ。キーは完了条件の検証器（backend draft_validation）が
// 要求する evidences.field の語彙（kind / od / qty / due …）と同じ。
export const evidenceGroups = [
  { key: "kind", fields: ["kind"] },
  { key: "usage_note", fields: ["usage_note"] },
  { key: "od", fields: ["od_value", "od_unit"] },
  { key: "wall", fields: ["wall_value", "wall_unit"] },
  { key: "weight", fields: ["weight_value", "weight_unit"] },
  { key: "grade", fields: ["grade"] },
  { key: "connection", fields: ["connection"] },
  { key: "length", fields: ["range_class", "length_value", "length_unit"] },
  { key: "qty", fields: ["qty_value", "qty_unit"] },
  { key: "due", fields: ["due_raw"] },
  { key: "place", fields: ["place_raw"] },
  { key: "note", fields: ["note"] },
] as const;
export type EvidenceKey = (typeof evidenceGroups)[number]["key"];
const evidenceAliases: Record<string, EvidenceKey> = {
  range_class: "length",
  qty_reference_note: "qty",
};
// エージェントが登録する field は表記が揺れる（qtyRaw / od_unit / rangeClass 等）。
// 表示グループに正規化し、どこにも当たらないものは null（その他の根拠として出す）。
export function evidenceKey(field: string): EvidenceKey | null {
  const snake = field
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .toLowerCase()
    .trim();
  const base = evidenceAliases[snake]
    ? snake
    : snake.replace(/_(raw|value|unit|state)$/, "");
  const key = evidenceAliases[base] ?? base;
  return evidenceGroups.some((group) => group.key === key)
    ? (key as EvidenceKey)
    : null;
}
export const filterStates = [
  "all",
  "questions",
  "tba",
  "choice",
  "unmatched",
  "edited",
  "unresolved",
] as const;
export type Filters = {
  keyword: string;
  kind: string;
  grade: string;
  connection: string;
  status: (typeof filterStates)[number];
};
export const emptyFilters: Filters = {
  keyword: "",
  kind: "",
  grade: "",
  connection: "",
  status: "all",
};
export const itemQuestions = (
  item: ItemCurrentResponse,
  questions: readonly QuestionResponse[],
) => questions.filter((q) => q.itemId === item.itemId);
export const hasEdits = (item: ItemCurrentResponse) =>
  item.history.some((edit) => edit.undoneAt === null);
// 04-db group_code の命名規則: ALT-n = 客先が選ぶ択一、CFL-n = 資料の記載が相反する併記（X04）。
export const groupKind = (groupCode: string) =>
  groupCode.startsWith("CFL-") ? ("conflict" as const) : ("choice" as const);
export function rowState(
  item: ItemCurrentResponse,
  questions: readonly QuestionResponse[],
) {
  const key =
    item.qtyState === "tba"
      ? "tba"
      : item.groupCode
        ? groupKind(item.groupCode)
        : item.isInheritCandidate
          ? "inherit"
          : itemQuestions(item, questions).length
            ? "questions"
            : "clear";
  return {
    key: `versions.rowState.${key}`,
    tone: key === "clear" ? ("ok" as const) : ("warn" as const),
  };
}
export function valueLabelKey(state: string | null | undefined) {
  return state === "tba" || state === "not_stated" || state === "not_applicable"
    ? `versions.values.${state}`
    : null;
}
export function previousValue(history: ItemEditRecord[], field: EditableField) {
  const latest = history
    .filter((edit) => edit.field === field && edit.undoneAt === null)
    .sort(
      (a, b) => a.recordedAt.localeCompare(b.recordedAt) || a.editId - b.editId,
    )
    .at(-1);
  return latest ? { value: latest.oldValue, state: latest.oldState } : null;
}
export function filterItems(
  items: ItemCurrentResponse[],
  questions: QuestionResponse[],
  filters: Filters,
) {
  return items.filter((item) => {
    const qs = itemQuestions(item, questions);
    const statuses = {
      all: true,
      questions: qs.length > 0,
      tba: item.qtyState === "tba",
      choice: !!item.groupCode,
      unmatched: item.rowMatch === null,
      edited: hasEdits(item),
      unresolved: unresolvedQuestions(qs).length > 0,
    };
    const haystack = [
      ...Object.values(item).filter((v) => typeof v === "string"),
      ...qs.map((q) => q.reason),
      ...item.history.filter((e) => e.undoneAt === null).map((e) => e.reason),
    ]
      .join(" ")
      .toLocaleLowerCase();
    return (
      statuses[filters.status] &&
      haystack.includes(filters.keyword.trim().toLocaleLowerCase()) &&
      (!filters.kind || item.kind === filters.kind) &&
      (!filters.grade || item.grade === filters.grade) &&
      (!filters.connection || item.connection === filters.connection)
    );
  });
}
export const hasValueState = (field: string) =>
  !["kind", "usage_note", "note"].includes(field);
export const isQuantityField = (field: string) =>
  field === "qty_value" || field === "qty_unit";
export type EditDraft = {
  field: string;
  state: string;
  value: string;
  qtyUnit: string;
  reason: string;
  recordedBy: string;
};
function invalid(code: string): never {
  throw new ApiError(400, { code, message: code });
}
export function buildEditRequest(
  itemId: number,
  draft: EditDraft,
): ItemEditRequest {
  if (!draft.reason.trim()) invalid("E_REASON_REQUIRED");
  if (!draft.recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  if (!(editableFields as readonly string[]).includes(draft.field))
    invalid("E_FIELD_NOT_EDITABLE");
  const field = draft.field as EditableField;
  const base = {
    itemId,
    field,
    reason: draft.reason.trim(),
    recordedBy: draft.recordedBy.trim(),
  };
  if (
    hasValueState(field) &&
    ["tba", "not_stated", "not_applicable"].includes(draft.state)
  ) {
    return {
      ...base,
      newState: draft.state as "tba" | "not_stated" | "not_applicable",
    };
  }
  const valueState = isQuantityField(field) ? "numeric" : "stated";
  if (
    !draft.value.trim() ||
    (hasValueState(field) && draft.state !== valueState)
  )
    invalid("E_STATE_VALUE_CONFLICT");
  // Keep the exact decimal text; the server is authoritative for field constraints.
  if (
    field.endsWith("_value") &&
    !/^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$/.test(
      draft.value.trim(),
    )
  )
    invalid("E_STATE_VALUE_CONFLICT");
  if (field === "qty_value" && !draft.qtyUnit.trim())
    invalid("E_QTY_UNIT_REQUIRED");
  return {
    ...base,
    newValue: draft.value.trim(),
    ...(hasValueState(field) ? { newState: valueState } : {}),
    ...(field === "qty_value" ? { qtyUnit: draft.qtyUnit.trim() } : {}),
  };
}
const recordCodes = new Set([
  "E_REASON_REQUIRED",
  "E_RECORDER_REQUIRED",
  "E_QTY_UNIT_REQUIRED",
  "E_STATE_VALUE_CONFLICT",
  "E_TARGET_INVALID",
  "E_REQUEST_INVALID",
  "E_FIELD_NOT_EDITABLE",
  "E_ALREADY_UNDONE",
  "E_ALREADY_CONFIRMED",
  "E_NOT_FOUND",
]);
export function recordErrorKey(error: unknown) {
  return error instanceof ApiError && recordCodes.has(error.code)
    ? `versions.errors.${error.code}`
    : "versions.errors.unknown";
}

export function sortEntries(entries: readonly InventoryEntryResponse[]) {
  const priority = (row: InventoryEntryResponse) =>
    row.judgement === "inconsistent" ? 0 : row.judgement === "missing" ? 1 : 2;
  return [...entries].sort(
    (a, b) =>
      priority(a) - priority(b) || a.seq - b.seq || a.entryId - b.entryId,
  );
}
export function sortItems(items: readonly InventoryItemResponse[]) {
  return [...items].sort(
    (a, b) =>
      Number(a.hasSource) - Number(b.hasSource) ||
      a.seq - b.seq ||
      a.itemId - b.itemId,
  );
}
export function inventoryState(judgement: InventoryEntryResponse["judgement"]) {
  const tones = {
    inconsistent: "danger",
    missing: "warn",
    mapped: "ok",
    split: "ok",
    excluded: null,
  } as const;
  return {
    key: `versions.inventory.judgement.${judgement}`,
    tone: tones[judgement],
  };
}
export function inventoryCounts(summary: InventorySummaryResponse) {
  return {
    sourceEntry: summary.sourceEntryCount,
    sourceItem: summary.sourceItemCount,
    outputRow: summary.outputRowCount,
    split: summary.splitEntryIds.length,
    excluded: summary.excludedEntryIds.length,
    unmapped: summary.unmappedEntryIds.length,
    orphan: summary.orphanItemIds.length,
    multiMapped: summary.multiMappedItemIds.length,
    inconsistent: summary.inconsistentEntryIds.length,
  };
}
export function documentNames(entries: readonly InventoryEntryResponse[]) {
  return [...new Set(entries.map((entry) => entry.documentFileName))];
}
export function buildCoverageRequest(recordedBy: string): ConfirmationRequest {
  if (!recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  return { kind: "coverage", recordedBy: recordedBy.trim() };
}
export function inventoryErrorKey(error: unknown) {
  return error instanceof ApiError && error.code === "E_ALREADY_CONFIRMED"
    ? "versions.inventory.errors.E_ALREADY_CONFIRMED"
    : recordErrorKey(error);
}

export const findVersionListItem = (
  rows: readonly VersionListItem[],
  versionId: number,
) => rows.find((row) => row.versionId === versionId);
export function approvalSummary(
  version: VersionResponse,
  listItem: VersionListItem,
  records: RecordsResponse,
) {
  return {
    state: version.currentState,
    sendoff: listItem.latestSendoff?.decision ?? "undecided",
    noSendoff: listItem.latestSendoff === null,
    matched: version.counts.matchedCount,
    total: version.counts.itemCount,
    coverage: version.coverageConfirmed,
    edits: version.counts.editCount,
    unresolved: version.counts.unresolvedCount,
    bounceComments: records.unlinkedComments.length,
    bounced: listItem.bounced,
    needsRecheck: listItem.needsRecheck,
  };
}
export function recorderMeta(records: RecordsResponse) {
  const events = [...records.stateEvents].sort(
    (a, b) =>
      a.recordedAt.localeCompare(b.recordedAt) ||
      a.stateEventId - b.stateEventId,
  );
  const coverage =
    [...records.confirmations]
      .filter((r) => r.kind === "coverage" && r.undoneAt === null)
      .sort(
        (a, b) =>
          a.recordedAt.localeCompare(b.recordedAt) ||
          a.confirmationId - b.confirmationId,
      )
      .at(-1) ?? null;
  return {
    staff: events.filter((r) => r.toState === "staff_checked").at(-1) ?? null,
    coverage,
    review: events.filter((r) => r.toState === "review_checked").at(-1) ?? null,
  };
}
export function changeTags(
  item: ItemCurrentResponse,
  questions: readonly QuestionResponse[],
) {
  const tags: (
    "choice" | "conflict" | "tba" | "inherit" | "edited" | "judged"
  )[] = [];
  if (item.groupCode) tags.push(groupKind(item.groupCode));
  if (item.qtyState === "tba") tags.push("tba");
  if (item.isInheritCandidate) tags.push("inherit");
  if (hasEdits(item)) tags.push("edited");
  if (itemQuestions(item, questions).some((q) => q.latest != null))
    tags.push("judged");
  return tags;
}
export const hasChanges = (
  item: ItemCurrentResponse,
  questions: readonly QuestionResponse[],
) => changeTags(item, questions).length > 0;
export const unresolvedQuestions = (questions: readonly QuestionResponse[]) =>
  questions.filter((q) => q.latest?.resolution !== "resolved");
export const rowUnresolved = (
  questions: readonly QuestionResponse[],
  itemId: number,
) => unresolvedQuestions(questions).filter((q) => q.itemId === itemId);
export const caseLevelUnresolved = (questions: readonly QuestionResponse[]) =>
  unresolvedQuestions(questions).filter((q) => q.itemId === null);
export const rowBounceComments = (records: RecordsResponse, itemId: number) =>
  records.unlinkedComments.filter((row) => row.itemId === itemId);
export const approvalFilters = [
  "all",
  "changes",
  "edited",
  "unresolved",
  "bounce",
] as const;
export type ApprovalFilter = (typeof approvalFilters)[number];
export function filterApprovalRows(
  items: ItemCurrentResponse[],
  questions: QuestionResponse[],
  records: RecordsResponse,
  filter: ApprovalFilter,
) {
  return items.filter(
    (item) =>
      ({
        all: true,
        changes: hasChanges(item, questions),
        edited: hasEdits(item),
        unresolved: rowUnresolved(questions, item.itemId).length > 0,
        bounce: rowBounceComments(records, item.itemId).length > 0,
      })[filter],
  );
}
export function buildStateEventRequest(
  toState: StateEventRequest["toState"],
  recordedBy: string,
): StateEventRequest {
  if (!recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  return { toState, recordedBy: recordedBy.trim() };
}
export function buildBounceCommentRequest(
  itemId: number,
  comment: string,
  recordedBy: string,
): BounceCommentRequest {
  if (!recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  if (!comment.trim()) invalid("E_COMMENT_REQUIRED");
  return { itemId, comment: comment.trim(), recordedBy: recordedBy.trim() };
}
export function buildBounceRequest(
  recordedBy: string,
  unlinkedCount: number,
): BounceRequest {
  if (!recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  if (unlinkedCount === 0) invalid("E_NO_BOUNCE_COMMENT");
  return { recordedBy: recordedBy.trim() };
}
export function buildSendoffRequest(
  decision: SendoffDecisionRequest["decision"],
  reason: string,
  recordedBy: string,
): SendoffDecisionRequest {
  if (!recordedBy.trim()) invalid("E_RECORDER_REQUIRED");
  if (decision !== "undecided" && !reason.trim())
    invalid("E_SENDOFF_REASON_REQUIRED");
  return {
    decision,
    reason: reason.trim() || null,
    recordedBy: recordedBy.trim(),
  };
}
export const canReview = (state: VersionResponse["currentState"]) =>
  (
    ({
      draft: "incomplete",
      staff_checked: "ready",
      review_checked: "reviewed",
    }) as const
  )[state];
const approvalCodes = new Set([
  "E_STAFF_CHECK_INCOMPLETE",
  "E_COVERAGE_NOT_RECORDED",
  "E_STATE_ORDER",
  "E_STATE_ROLLBACK_FORBIDDEN",
  "E_NO_BOUNCE_COMMENT",
  "E_SENDOFF_REASON_REQUIRED",
  "E_COMMENT_REQUIRED",
  "E_RECORDER_REQUIRED",
]);
export function approvalErrorKey(error: unknown) {
  return error instanceof ApiError && approvalCodes.has(error.code)
    ? `versions.approval.errors.${error.code}`
    : recordErrorKey(error);
}
export function staffCheckDetails(error: unknown) {
  const details =
    error instanceof ApiError &&
    error.details &&
    typeof error.details === "object"
      ? (error.details as Record<string, unknown>)
      : {};
  return {
    rowCodes: Array.isArray(details.unmatchedRowCodes)
      ? details.unmatchedRowCodes.filter(
          (v): v is string => typeof v === "string",
        )
      : [],
    coverageRecorded: details.coverageRecorded === true,
  };
}
export const sendoffTone = (decision: SendoffDecisionRequest["decision"]) =>
  decision === "approved" ? "ok" : decision === "hold" ? "warn" : null;
export const stateTone = (state: VersionResponse["currentState"]) =>
  state === "review_checked" ? "ok" : null;

const DEFAULT_EXPORT_NAME = "export.xlsx";
/** Content-Disposition の filename を取り出す純粋関数。
 * 由来（fromHeader）を返し、既定名へ落ちたことを画面側が区別できるようにする。 */
export function parseExportFileName(headers?: Headers | null): {
  name: string;
  fromHeader: boolean;
} {
  const raw = headers?.get("Content-Disposition") ?? "";
  const extended = /filename\*\s*=\s*[^']*'[^']*'([^;]+)/i.exec(raw);
  const plain = /filename\s*=\s*(?:"([^"]*)"|([^;]+))/i.exec(raw);
  const candidate = extended
    ? decodeUriComponentSafely(extended[1].trim())
    : (plain?.[1] ?? plain?.[2] ?? "").trim();
  // 保存先を誘導させないため、区切りを含む名前は単純名に落とす。
  const name = candidate.split(/[/\\]/).pop()?.trim() ?? "";
  return name
    ? { name, fromHeader: true }
    : { name: DEFAULT_EXPORT_NAME, fromHeader: false };
}
function decodeUriComponentSafely(value: string) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
const exportCodes = new Set(["E_VERSION_NOT_FINALIZED", "E_NOT_FOUND"]);
export function exportErrorKey(error: unknown) {
  if (!(error instanceof ApiError) || !exportCodes.has(error.code))
    return "versions.export.errors.failed";
  return error.code === "E_VERSION_NOT_FINALIZED"
    ? "versions.export.errors.notFinalized"
    : "versions.export.errors.notFound";
}
/** 保全状態は色でなく文字ラベルで伝える（design-guidelines）。 */
export function integrityLabelKey(integrity: string) {
  return `versions.export.integrity.${
    ["intact", "modified", "missing"].includes(integrity)
      ? integrity
      : "unknown"
  }`;
}
