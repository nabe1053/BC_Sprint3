"""Human-record inputs; no HTTP, ORM, clock or agent dependencies."""
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import Field, StringConstraints, model_validator
from pydantic_core import PydanticCustomError

from app.domain.draft_types import Input, exact_decimal

Recorder = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
EditableField = Literal[
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
]
EDITABLE_FIELDS = get_args(EditableField)
EditState = Literal["stated", "tba", "not_stated", "not_applicable", "numeric"]
STATE_FIELDS = {
    **{
        field: prefix + "_state"
        for prefix in ("od", "wall", "weight", "length", "qty")
        for field in (prefix + "_value", prefix + "_unit")
    },
    "grade": "grade_state",
    "connection": "connection_state",
    "range_class": "length_state",
}


class ItemEditInput(Input):
    field_error_codes = {
        "reason": "E_REASON_REQUIRED",
        "recorded_by": "E_RECORDER_REQUIRED",
        "field": "E_FIELD_NOT_EDITABLE",
        "new_value": "E_STATE_VALUE_CONFLICT",
        "new_state": "E_STATE_VALUE_CONFLICT",
        "qty_unit": "E_QTY_UNIT_REQUIRED",
    }
    # Declaration order preserves reason -> recorder -> field error precedence.
    reason: Recorder
    recorded_by: Recorder
    field: EditableField
    item_id: int = Field(gt=0)
    new_value: Recorder | None = None
    new_state: EditState | None = None
    qty_unit: Recorder | None = None

    @model_validator(mode="after")
    def consistent(self):
        state_field = STATE_FIELDS.get(self.field)
        has_value = self.new_value is not None
        value_state = "numeric" if state_field == "qty_state" else "stated"
        if (
            (not has_value and self.new_state is None)
            or (self.new_state is not None and state_field is None)
            or (
                self.new_state in ("stated", "numeric")
                and self.new_state != value_state
            )
            or (
                self.new_state is not None
                and (self.new_state == value_state) != has_value
            )
        ):
            raise PydanticCustomError(
                "E_STATE_VALUE_CONFLICT", "E_STATE_VALUE_CONFLICT"
            )
        if has_value and self.field.endswith("_value"):
            try:
                exact_decimal(self.new_value)
            except ValueError as exc:
                raise PydanticCustomError(
                    "E_STATE_VALUE_CONFLICT", "E_STATE_VALUE_CONFLICT"
                ) from exc
        if self.field == "qty_value" and has_value and not self.qty_unit:
            raise PydanticCustomError("E_QTY_UNIT_REQUIRED", "E_QTY_UNIT_REQUIRED")
        return self


class UndoInput(Input):
    field_error_codes = {"recorded_by": "E_RECORDER_REQUIRED"}
    recorded_by: Recorder


class ConfirmationInput(UndoInput):
    field_error_codes = {
        **UndoInput.field_error_codes,
        "kind": "E_TARGET_INVALID",
        "item_id": "E_TARGET_INVALID",
    }
    kind: Literal["row_match", "coverage"]
    item_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def target(self):
        if (self.kind == "row_match") != (self.item_id is not None):
            raise PydanticCustomError("E_TARGET_INVALID", "E_TARGET_INVALID")
        return self


class JudgementInput(UndoInput):
    status: Literal["open", "in_progress", "judged"]
    resolution: Literal["unresolved", "resolved"]
    note: str | None = None


@dataclass(frozen=True)
class RowMatch:
    confirmation_id: int
    recorded_by: str
    recorded_at: datetime


@dataclass(frozen=True)
class CurrentItem:
    values: dict
    history: list
    row_match: RowMatch | None = None
