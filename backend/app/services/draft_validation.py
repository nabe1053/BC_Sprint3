"""Pure completion checks. Violation names are defined by 05-api-ipo.md §3.4."""
from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Violation:
    kind: str
    detail: str
    item_id: int | None = None
    document_id: int | None = None
    locator: str | None = None


@dataclass
class ValidationResult:
    violations: list[Violation]
    counts: dict[str, int]


@dataclass
class DraftSnapshot:
    items: list[Any] = field(default_factory=list)
    header: Any = None
    evidences: list[Any] = field(default_factory=list)
    questions: list[Any] = field(default_factory=list)
    inventory: list[Any] = field(default_factory=list)
    readable_ranges: set[tuple[int, str]] = field(default_factory=set)
    scanned_ranges: set[tuple[int, str]] = field(default_factory=set)
    excused_ranges: set[tuple[int, str]] = field(default_factory=set)
    has_issues: bool = False


def _present(value):
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def validate_snapshot(snapshot) -> ValidationResult:
    violations = []
    for document_id, locator in sorted(
            snapshot.readable_ranges - snapshot.scanned_ranges - snapshot.excused_ranges):
        violations.append(Violation("unscanned_range", "読取成功範囲が未走査です",
                                    document_id=document_id, locator=locator))
    evidence_fields = {(e.item_id, e.field) for e in snapshot.evidences
                       if _present(e.document_id) and _present(e.locator) and _present(e.quote)}
    groups = Counter(row.group_code for row in snapshot.items if row.group_code)
    item_ids = {row.id for row in snapshot.items}
    for row in snapshot.items:
        if not _present(row.source_no):
            violations.append(Violation("missing_source_no", "原項番がありません", row.id))
        if row.group_code and groups[row.group_code] < 2:
            violations.append(Violation("orphan_candidate", "選択グループに候補が1件だけです", row.id))
        required = {"kind"}
        for name in ("qty", "od", "wall", "weight", "length"):
            if getattr(row, name+"_value", None) is not None:
                required.add(name)
                if not _present(getattr(row, name+"_unit", None)):
                    violations.append(Violation("missing_unit", name+" の単位がありません", row.id))
        for name, attr in (("grade", "grade"), ("connection", "connection"),
                           ("length", "range_class"), ("due", "due_raw"), ("place", "place_raw"),
                           ("usage_note", "usage_note"), ("note", "note"),
                           ("qty", "qty_reference_note")):
            if _present(getattr(row, attr, None)):
                required.add(name)
        # TBA / missing states also retain the evidence locating the original row.
        if not any(item_id == row.id for item_id, _ in evidence_fields):
            required.add("source")
        for name in sorted(required):
            if (row.id, name) not in evidence_fields:
                violations.append(Violation("missing_evidence", name+" の出典がありません", row.id))
    if snapshot.header is None:
        violations.append(Violation("missing_evidence", "案件情報が登録されていません"))
    else:
        for name, attr in (("inquiry_no", "inquiry_no"), ("customer_name", "customer_name"),
                           ("due", "due_raw"), ("place", "place_raw"), ("incoterms", "incoterms"),
                           ("quote_deadline", "quote_deadline_raw")):
            if _present(getattr(snapshot.header, attr, None)) and (None, name) not in evidence_fields:
                violations.append(Violation("missing_evidence", name+" の出典がありません"))
    for question in snapshot.questions:
        if ((question.item_id is not None and question.item_id not in item_ids)
                or not _present(question.target_field)):
            violations.append(Violation("orphan_question", "確認事項の対象が不正です", question.item_id))
    for entry in snapshot.inventory:
        if entry.status == "excluded" and not _present(entry.basis):
            violations.append(Violation("excluded_without_basis", "除外根拠がありません"))
    return ValidationResult(violations, {"items": len(snapshot.items),
        "questions": len(snapshot.questions), "inventory": len(snapshot.inventory)})
