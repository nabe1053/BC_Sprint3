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


VersionState = Literal["draft", "staff_checked", "review_checked"]
CheckedState = Literal["staff_checked", "review_checked"]


class StateEventInput(UndoInput):
    field_error_codes = {
        **UndoInput.field_error_codes,
        "to_state": "E_STATE_ROLLBACK_FORBIDDEN",
    }
    to_state: CheckedState


class BounceCommentInput(UndoInput):
    field_error_codes = {**UndoInput.field_error_codes, "comment": "E_COMMENT_REQUIRED"}
    item_id: int = Field(gt=0)
    comment: Recorder


class BounceInput(UndoInput):
    pass


SendoffState = Literal["undecided", "hold", "approved"]


class SendoffInput(UndoInput):
    field_error_codes = {
        **UndoInput.field_error_codes,
        "reason": "E_SENDOFF_REASON_REQUIRED",
    }
    decision: SendoffState
    reason: Recorder | None = None

    @model_validator(mode="after")
    def requires_reason(self):
        if self.decision != "undecided" and self.reason is None:
            raise PydanticCustomError(
                "E_SENDOFF_REASON_REQUIRED", "E_SENDOFF_REASON_REQUIRED"
            )
        return self


@dataclass(frozen=True)
class CarryOver:
    edit_count: int
    row_match_confirmed: int
    row_match_total: int
    coverage_recorded: bool
    judgement_count: int


@dataclass(frozen=True)
class Transition:
    from_state: VersionState
    to_state: CheckedState


def unresolved_question_ids(rows):
    return {
        row["question"].id
        for row in rows
        if row["latest"] is None or row["latest"].resolution == "unresolved"
    }


def apply_edits(item, edits):
    values = {
        key: value
        for key, value in (item if isinstance(item, dict) else vars(item)).items()
        if not key.startswith("_")
    }
    history = sorted(edits, key=lambda edit: (edit.recorded_at, edit.id))
    for edit in history:
        if edit.undone_at is not None or edit.field not in EDITABLE_FIELDS:
            continue
        state_field = STATE_FIELDS.get(edit.field)
        state = edit.new_state
        if state_field and state is None and edit.new_value is not None:
            state = "numeric" if state_field == "qty_state" else "stated"
        if state_field:
            values[state_field] = state
        if state is not None and state not in ("stated", "numeric"):
            for field, related in STATE_FIELDS.items():
                if related == state_field:
                    values[field] = None
        else:
            values[edit.field] = (
                exact_decimal(edit.new_value)
                if edit.field.endswith("_value") and edit.new_value is not None
                else edit.new_value
            )
    return CurrentItem(values, history)
