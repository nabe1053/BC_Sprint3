"""Pure completion checks. Violation names are defined by 05-api-ipo.md §3.4."""
from collections import Counter
from dataclasses import dataclass


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


def _present(value):
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _field_key(value):
    """確認事項の targetField の表記揺れ（quoteDeadlineAt / quote_deadline_raw）を比較用に畳む。"""
    return (value or "").replace("_", "").lower()


def validate_snapshot(snapshot) -> ValidationResult:
    violations = []
    for document_id, locator in sorted(
        snapshot.readable_ranges - snapshot.scanned_ranges - snapshot.excused_ranges
    ):
        violations.append(
            Violation(
                "unscanned_range",
                "読取成功範囲が未走査です",
                document_id=document_id,
                locator=locator,
            )
        )
    evidence_fields = {
        (e.item_id, e.field)
        for e in snapshot.evidences
        if _present(e.document_id) and _present(e.locator) and _present(e.quote)
    }
    groups = Counter(row.group_code for row in snapshot.items if row.group_code)
    item_ids = {row.id for row in snapshot.items}
    for row in snapshot.items:
        if not _present(row.source_no):
            violations.append(
                Violation("missing_source_no", "原項番がありません", row.id)
            )
        if row.group_code and groups[row.group_code] < 2:
            violations.append(
                Violation("orphan_candidate", "選択グループに候補が1件だけです", row.id)
            )
        required = {"kind"}
        for name in (
            "qty",
            "od",
            "wall",
            "weight",
            "grade",
            "connection",
            "length",
            "due",
            "place",
        ):
            if getattr(row, name + "_state", None) in ("tba", "not_applicable"):
                required.add(name)
        for name in ("qty", "od", "wall", "weight", "length"):
            if getattr(row, name + "_value", None) is not None:
                required.add(name)
                if not _present(getattr(row, name + "_unit", None)):
                    violations.append(
                        Violation("missing_unit", name + " の単位がありません", row.id)
                    )
        for name, attr in (
            ("grade", "grade"),
            ("connection", "connection"),
            ("length", "range_class"),
            ("due", "due_raw"),
            ("place", "place_raw"),
            ("usage_note", "usage_note"),
            ("note", "note"),
            ("qty", "qty_reference_note"),
        ):
            if _present(getattr(row, attr, None)):
                required.add(name)
        for name in sorted(required):
            if (row.id, name) not in evidence_fields:
                violations.append(
                    Violation("missing_evidence", name + " の出典がありません", row.id)
                )
    for end in snapshot.ends:
        for name, attr in (
            ("od", "od_value"),
            ("connection", "connection"),
            ("thread_end", "thread_end"),
        ):
            if _present(getattr(end, attr, None)):
                evidence_field = end.side + "." + name
                if (end.item_id, evidence_field) not in evidence_fields:
                    violations.append(
                        Violation(
                            "missing_evidence",
                            evidence_field + " の出典がありません",
                            end.item_id,
                        )
                    )
        if end.od_value is not None and not _present(end.od_unit):
            violations.append(
                Violation(
                    "missing_unit", end.side + ".od の単位がありません", end.item_id
                )
            )
    if snapshot.header is None:
        violations.append(Violation("missing_evidence", "案件情報が登録されていません"))
    else:
        for name, attr in (
            ("inquiry_no", "inquiry_no"),
            ("customer_name", "customer_name"),
            ("due", "due_raw"),
            ("place", "place_raw"),
            ("incoterms", "incoterms"),
            ("quote_deadline", "quote_deadline_raw"),
        ):
            has_source_value = _present(getattr(snapshot.header, attr, None))
            explicit_state = getattr(snapshot.header, name + "_state", None) in (
                "tba",
                "not_applicable",
            )
            if (has_source_value or explicit_state) and (
                None,
                name,
            ) not in evidence_fields:
                violations.append(
                    Violation("missing_evidence", name + " の出典がありません")
                )
    for question in snapshot.questions:
        if (
            question.item_id is not None and question.item_id not in item_ids
        ) or not _present(question.target_field):
            violations.append(
                Violation(
                    "orphan_question", "確認事項の対象が不正です", question.item_id
                )
            )
    header = snapshot.header
    if (
        header is not None
        and _present(getattr(header, "quote_deadline_raw", None))
        and getattr(header, "quote_deadline_tz_state", None) == "missing"
    ):
        # 04-db case_headers: quote_deadline_tz_state=missing なら確認事項が立つ（案件レベル）。
        # 期限の記載自体が無い（raw NULL）場合は時刻・TZ の不足ではないので対象外。
        if not any(
            question.item_id is None
            and _field_key(question.target_field).startswith("quotedeadline")
            for question in snapshot.questions
        ):
            violations.append(
                Violation(
                    "missing_question",
                    "見積期限の時刻・タイムゾーン不足の確認事項（案件レベル）がありません",
                )
            )
    grouped = {row.id for row in snapshot.items if row.group_code}
    for question in snapshot.questions:
        # 数量の矛盾は1行に抱えず、CFL-n の候補2行で残す（X04・04-db 3.3）。
        if (
            getattr(question, "category", None) == "conflict"
            and question.item_id in item_ids
            and question.item_id not in grouped
            and _field_key(question.target_field).startswith("qty")
        ):
            violations.append(
                Violation(
                    "unsplit_conflict",
                    "数量の矛盾が1行のままです。候補2行（同一 groupCode）で残してください",
                    question.item_id,
                )
            )
    for entry in snapshot.inventory:
        if entry.status == "excluded" and not _present(entry.basis):
            violations.append(
                Violation("excluded_without_basis", "除外根拠がありません")
            )
    return ValidationResult(
        violations,
        {
            "items": len(snapshot.items),
            "questions": len(snapshot.questions),
            "inventory": len(snapshot.inventory),
        },
    )
