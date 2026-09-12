from tests.fixtures.draft_data import snapshot
from types import SimpleNamespace as N

import pytest

from app.services.draft_validation import validate_snapshot


def kinds(s):
    return {v.kind for v in validate_snapshot(s).violations}


def test_valid_draft_has_no_violations():
    result = validate_snapshot(snapshot())
    assert result.violations == []
    assert result.counts == {"items": 1, "questions": 0, "inventory": 1}


@pytest.mark.parametrize(
    "kind",
    [
        "unscanned_range",
        "missing_evidence",
        "missing_unit",
        "missing_source_no",
        "orphan_candidate",
        "orphan_question",
        "excluded_without_basis",
    ],
)
def test_each_violation(kind):
    s = snapshot()
    if kind == "unscanned_range":
        s.scanned_ranges.clear()
    elif kind == "missing_evidence":
        s.evidences.clear()
    elif kind == "missing_unit":
        s.items[0].qty_unit = " "
    elif kind == "missing_source_no":
        s.items[0].source_no = ""
    elif kind == "orphan_candidate":
        s.items[0].group_code = "CFL-1"
    elif kind == "orphan_question":
        s.questions = [N(id=1, item_id=999, target_field="qty")]
    else:
        s.inventory[0].status = "excluded"
        s.inventory[0].basis = " "
    assert kind in kinds(s)


def test_email_parts_cannot_be_omitted_and_sheet_cell_issue_does_not_cover_sheet():
    s = snapshot()
    s.readable_ranges = {
        (2, "email:latest_body:1"),
        (2, "email:postscript:2"),
        (3, "Sheet1"),
    }
    s.scanned_ranges = {(2, "email:latest_body:1")}
    s.excused_ranges = {(3, "Sheet1!B1")}
    result = validate_snapshot(s)
    assert {
        (v.document_id, v.locator)
        for v in result.violations
        if v.kind == "unscanned_range"
    } == {(2, "email:postscript:2"), (3, "Sheet1")}


def test_recorded_unscanned_range_is_accounted_for():
    s = snapshot()
    s.scanned_ranges.clear()
    s.excused_ranges = {(1, "p.1")}
    s.has_issues = True
    assert "unscanned_range" not in kinds(s)


def test_two_candidates_and_case_level_question_are_valid():
    s = snapshot()
    s.items[0].group_code = "ALT-1"
    s.items.append(N(**(vars(s.items[0]) | {"id": 2})))
    s.evidences += [N(**(vars(e) | {"item_id": 2})) for e in list(s.evidences)]
    s.questions = [N(id=1, item_id=None, target_field="quote_deadline")]
    assert not kinds(s)


def test_header_values_need_field_specific_evidence():
    s = snapshot()
    s.header.customer_name = "Synthetic customer"
    assert "missing_evidence" in kinds(s)
    s.evidences.append(
        N(
            item_id=None,
            field="customer_name",
            document_id=1,
            locator="p.1",
            quote="Synthetic customer",
        )
    )
    assert "missing_evidence" not in kinds(s)


def test_tba_quantity_requires_its_own_evidence():
    s = snapshot()
    s.items[0].qty_value = None
    s.items[0].qty_state = "tba"
    s.items[0].qty_raw = "TBA"
    s.evidences = [e for e in s.evidences if e.field == "kind"]
    assert "missing_evidence" in kinds(s)
    s.evidences.append(
        N(item_id=1, field="qty", document_id=1, locator="p.1", quote="TBA")
    )
    assert not kinds(s)


@pytest.mark.parametrize(
    "field",
    ["qty", "od", "wall", "weight", "grade", "connection", "length", "due", "place"],
)
@pytest.mark.parametrize("state", ["tba", "not_applicable"])
def test_every_item_explicit_state_requires_own_evidence(field, state):
    s = snapshot()
    s.items[0].qty_value = None
    setattr(s.items[0], field + "_state", state)
    s.evidences = [e for e in s.evidences if e.field == "kind"]
    missing = validate_snapshot(s).violations
    assert [(v.kind, v.detail, v.item_id) for v in missing] == [
        ("missing_evidence", field + " の出典がありません", 1)
    ]
    s.evidences.append(
        N(item_id=1, field=field, document_id=1, locator="p.1", quote=state)
    )
    assert not kinds(s)


def test_missing_kind_evidence_does_not_invent_source_field():
    s = snapshot()
    s.evidences.clear()
    assert {v.detail for v in validate_snapshot(s).violations} == {
        "kind の出典がありません",
        "qty の出典がありません",
    }


def test_end_missing_unit_identifies_od_field():
    s = snapshot()
    s.ends = [
        N(
            item_id=1,
            side="end_a",
            od_value=1,
            od_unit=None,
            connection=None,
            thread_end=None,
        )
    ]
    assert [
        v.detail for v in validate_snapshot(s).violations if v.kind == "missing_unit"
    ] == ["end_a.od の単位がありません"]


def test_both_ends_have_field_specific_evidence():
    s = snapshot()
    s.ends = [
        N(
            item_id=1,
            side="end_a",
            od_value=1,
            od_unit="in",
            connection="BTC",
            thread_end="BOX",
        ),
        N(
            item_id=1,
            side="end_b",
            od_value=2,
            od_unit="in",
            connection=None,
            thread_end="PIN",
        ),
    ]
    result = validate_snapshot(s)
    missing = [v for v in result.violations if v.kind == "missing_evidence"]
    assert len(missing) == 5
    for field in (
        "end_a.od",
        "end_a.connection",
        "end_a.thread_end",
        "end_b.od",
        "end_b.thread_end",
    ):
        s.evidences.append(
            N(item_id=1, field=field, document_id=1, locator="p.1", quote="both ends")
        )
    assert not kinds(s)


@pytest.mark.parametrize(
    "field,state,attribute",
    [
        ("due", "tba", "due_raw"),
        ("place", "not_applicable", "place_raw"),
        ("incoterms", "not_applicable", "incoterms"),
    ],
)
def test_header_explicit_states_require_evidence(field, state, attribute):
    s = snapshot()
    setattr(s.header, field + "_state", state)
    setattr(s.header, attribute, None)
    assert "missing_evidence" in kinds(s)
    s.evidences.append(
        N(item_id=None, field=field, document_id=1, locator="p.1", quote=state)
    )
    assert not kinds(s)
