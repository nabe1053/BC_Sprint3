import pytest
from pydantic import ValidationError

from tests.fixtures.record_data import edit_data


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"reason": "  "}, "E_REASON_REQUIRED"),
        ({"recorded_by": "  "}, "E_RECORDER_REQUIRED"),
        ({"field": "grade_raw"}, "E_FIELD_NOT_EDITABLE"),
        ({"field": "due_raw"}, "E_FIELD_NOT_EDITABLE"),
        ({"new_value": None, "new_state": None}, "E_STATE_VALUE_CONFLICT"),
        ({"new_state": "tba"}, "E_STATE_VALUE_CONFLICT"),
        (
            {"field": "qty_value", "new_value": "200", "new_state": "numeric"},
            "E_QTY_UNIT_REQUIRED",
        ),
    ],
)
def test_edit_business_validation(changes, code):
    from app.domain.record_types import ItemEditInput

    with pytest.raises(ValidationError) as error:
        ItemEditInput.model_validate(edit_data(**changes))
    assert error.value.errors()[0]["type"] == code


def test_edit_error_precedence_and_recorder_required():
    from app.domain.record_types import ItemEditInput

    with pytest.raises(ValidationError) as error:
        ItemEditInput.model_validate(edit_data(reason="", recorded_by="", field="bad"))
    assert error.value.errors()[0]["type"] == "E_REASON_REQUIRED"
    missing = edit_data()
    del missing["recorded_by"]
    with pytest.raises(ValidationError) as error:
        ItemEditInput.model_validate(missing)
    assert error.value.errors()[0]["type"] == "E_RECORDER_REQUIRED"


def test_state_only_and_quantity_inputs_are_valid():
    from app.domain.record_types import ItemEditInput

    state = ItemEditInput.model_validate(
        edit_data(new_value=None, new_state="tba", recorded_by=" 担当者 ")
    )
    assert state.new_value is None and state.recorded_by == "担当者"
    qty = ItemEditInput.model_validate(
        edit_data(
            field="qty_value", new_value="200", new_state="numeric", qty_unit="本"
        )
    )
    assert qty.qty_unit == "本"


def test_judged_unresolved_and_coverage_are_separate_valid_contracts():
    from app.domain.record_types import ConfirmationInput, JudgementInput, UndoInput

    assert (
        JudgementInput(
            status="judged", resolution="unresolved", recorded_by="担当者"
        ).resolution
        == "unresolved"
    )
    assert ConfirmationInput(kind="coverage", recorded_by="担当者").item_id is None
    with pytest.raises(ValidationError) as error:
        ConfirmationInput(kind="row_match", recorded_by="担当者")
    assert error.value.errors()[0]["type"] == "E_TARGET_INVALID"
    with pytest.raises(ValidationError) as error:
        UndoInput(recorded_by=" ")
    assert error.value.errors()[0]["type"] == "E_RECORDER_REQUIRED"


@pytest.mark.parametrize(
    "schema,data,code",
    [
        (
            "StateEventInput",
            {"recorded_by": " ", "to_state": "draft"},
            "E_RECORDER_REQUIRED",
        ),
        (
            "StateEventInput",
            {"recorded_by": "person", "to_state": "draft"},
            "E_STATE_ROLLBACK_FORBIDDEN",
        ),
        (
            "BounceCommentInput",
            {"recorded_by": " ", "item_id": 1, "comment": "text"},
            "E_RECORDER_REQUIRED",
        ),
        (
            "BounceCommentInput",
            {"recorded_by": "person", "item_id": 1, "comment": " \t"},
            "E_COMMENT_REQUIRED",
        ),
        ("BounceInput", {"recorded_by": " "}, "E_RECORDER_REQUIRED"),
        (
            "SendoffInput",
            {"recorded_by": " ", "decision": "hold"},
            "E_RECORDER_REQUIRED",
        ),
        (
            "SendoffInput",
            {"recorded_by": "person", "decision": "hold"},
            "E_SENDOFF_REASON_REQUIRED",
        ),
        (
            "SendoffInput",
            {"recorded_by": "person", "decision": "approved", "reason": " "},
            "E_SENDOFF_REASON_REQUIRED",
        ),
    ],
)
def test_approval_input_codes_and_recorder_precedence(schema, data, code):
    from app.domain import record_types

    with pytest.raises(ValidationError) as error:
        getattr(record_types, schema).model_validate(data)
    assert error.value.errors()[0]["type"] == code


def test_approval_inputs_trim_names_and_keep_decisions_independent():
    from app.domain.record_types import (
        StateEventInput,
        BounceCommentInput,
        BounceInput,
        SendoffInput,
    )

    assert (
        StateEventInput(recorded_by=" actor ", to_state="staff_checked").recorded_by
        == "actor"
    )
    assert (
        BounceCommentInput(recorded_by="actor", item_id=1, comment=" note ").comment
        == "note"
    )
    assert BounceInput(recorded_by="actor").model_dump() == {"recorded_by": "actor"}
    assert SendoffInput(recorded_by="actor", decision="undecided").reason is None
    assert (
        SendoffInput(
            recorded_by="actor", decision="approved", reason=" condition "
        ).reason
        == "condition"
    )
