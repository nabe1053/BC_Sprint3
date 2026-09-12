import type {
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
export function rowState(
  item: ItemCurrentResponse,
  questions: readonly QuestionResponse[],
) {
  const key =
    item.qtyState === "tba"
      ? "tba"
      : item.groupCode
        ? "choice"
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
      unresolved: qs.some((q) => q.latest?.resolution !== "resolved"),
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
