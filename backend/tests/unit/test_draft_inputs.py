from tests.fixtures.draft_data import item_data, header_data
from copy import deepcopy
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.draft_types import (
    HeaderInput,
    ItemInput,
    EvidenceInput,
    QuestionInput,
    InventoryInput,
)


def test_exact_decimal_and_no_implicit_values():
    row = ItemInput(**item_data())
    assert row.od_value == Decimal("13.375")
    assert row.qty_value == Decimal("150")
    assert row.wall_value is None
    assert row.connection is None


@pytest.mark.parametrize(
    "state,value", [("tba", "0"), ("not_stated", "1"), ("numeric", None)]
)
def test_quantity_state_conflicts(state, value):
    data = item_data() | dict(qty_state=state, qty_value=value)
    with pytest.raises(ValidationError):
        ItemInput(**data)


@pytest.mark.parametrize("field", ["od", "wall", "weight", "length", "qty"])
def test_numeric_value_requires_nonblank_unit(field):
    data = item_data() | {
        field + "_value": "1",
        field + "_unit": " ",
        field + "_state": "numeric" if field == "qty" else "stated",
    }
    with pytest.raises(ValidationError):
        ItemInput(**data)


@pytest.mark.parametrize(
    "field",
    ["od", "wall", "weight", "grade", "connection", "length", "qty", "due", "place"],
)
def test_each_important_state_is_required(field):
    data = item_data()
    del data[field + "_state"]
    with pytest.raises(ValidationError):
        ItemInput(**data)


@pytest.mark.parametrize(
    "name,value",
    [
        ("convertedValue", "100"),
        ("converted_value", "100"),
        ("conversionNote", "converted"),
        ("total_qty", "200"),
        ("qty_value", 1.1),
        ("od_value", "NaN"),
        ("qty_value", "Infinity"),
    ],
)
def test_conversion_fields_totals_and_lossy_numbers_are_rejected(name, value):
    with pytest.raises(ValidationError):
        ItemInput(**(item_data() | {name: value}))


def test_candidates_require_group():
    with pytest.raises(ValidationError):
        ItemInput(**(item_data() | {"candidate_label": "A"}))


def test_header_value_state_and_timezone_are_consistent():
    HeaderInput(**header_data())
    with pytest.raises(ValidationError):
        HeaderInput(**(header_data() | {"customer_name": "Synthetic customer"}))
    with pytest.raises(ValidationError):
        HeaderInput(**(header_data() | {"quote_deadline_at": "2026-09-12T12:00:00"}))


def test_unknown_nested_conversion_fields_are_rejected():
    data = deepcopy(item_data())
    data["ends"] = [{"side": "end_a", "convertedValue": "10"}]
    with pytest.raises(ValidationError):
        ItemInput(**data)


def test_question_requires_target_and_reason():
    with pytest.raises(ValidationError):
        QuestionInput(question_code="Q1", reason="Please confirm", target_field=" ")


def test_exclusion_requires_nonblank_basis():
    with pytest.raises(ValidationError):
        InventoryInput(
            document_id=1,
            position="p.1",
            seq=1,
            excerpt="total",
            status="excluded",
            basis=" ",
        )


def test_evidence_has_no_conversion_input():
    evidence = dict(
        field="qty",
        raw_value="150 MT",
        adopted_value="150 MT",
        document_id=1,
        locator="p.1",
        quote="150 MT",
    )
    EvidenceInput(**evidence)
    with pytest.raises(ValidationError):
        EvidenceInput(**(evidence | {"conversion_note": "converted"}))


@pytest.mark.parametrize("value", ["not-a-number", {}, [], True])
def test_invalid_decimal_types_become_validation_errors(value):
    with pytest.raises(ValidationError):
        ItemInput(**(item_data() | {"qty_value": value}))


def test_number_schema_matches_validator_and_excludes_json_floats():
    # A: the advertised schema must not accept what the validator rejects.
    schema = ItemInput.model_json_schema()["properties"]["odValue"]

    def walk(node):
        yield node
        for child in node.get("anyOf", []):
            yield from walk(child)

    nodes = list(walk(schema))
    types = {node["type"] for node in nodes if "type" in node}
    assert types == {"string", "integer", "null"}
    assert any("文字列" in node.get("description", "") for node in nodes)
    with pytest.raises(ValidationError):
        ItemInput(**(item_data() | {"od_value": 13.375}))
    assert ItemInput(**(item_data() | {"od_value": 13})).od_value == Decimal("13")


def test_all_consistency_violations_are_reported_in_check_order():
    # C: one call must surface every conflict so the caller can fix them at once.
    data = item_data() | dict(
        od_value=None,
        grade=None,
        range_class="R3",
        length_state="not_stated",
        candidate_label="A",
    )
    with pytest.raises(ValidationError) as exc:
        ItemInput(**data)
    errors = exc.value.errors()
    assert [(e["type"], e["loc"]) for e in errors] == [
        ("E_STATE_VALUE_CONFLICT", ("odState",)),
        ("E_STATE_VALUE_CONFLICT", ("gradeState",)),
        ("E_STATE_VALUE_CONFLICT", ("lengthState",)),
        ("E_GROUP_REQUIRED", ("groupCode",)),
    ]
    length = errors[2]["msg"]
    assert "rangeClass" in length and "lengthValue" in length
    assert "R3" not in str([e["msg"] for e in errors])


def test_quantity_and_unit_errors_still_come_first():
    data = item_data() | dict(qty_unit=None, od_value="1", od_unit=None, grade=None)
    with pytest.raises(ValidationError) as exc:
        ItemInput(**data)
    assert [e["type"] for e in exc.value.errors()] == [
        "E_QTY_UNIT_REQUIRED",
        "E_UNIT_REQUIRED",
        "E_STATE_VALUE_CONFLICT",
    ]


def test_conflict_hint_covers_value_given_with_non_stated_state():
    # A value with tba must not be steered toward "stated" (would record TBA as stated).
    data = item_data() | dict(due_state="tba", due_raw="TBA")
    with pytest.raises(ValidationError) as exc:
        ItemInput(**data)
    [error] = exc.value.errors()
    assert error["loc"] == ("dueState",)
    assert "dueRaw を渡さない" in error["msg"]
    assert "TBA" not in error["msg"]
