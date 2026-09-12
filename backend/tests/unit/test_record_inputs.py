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
