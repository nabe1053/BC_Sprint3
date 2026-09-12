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
