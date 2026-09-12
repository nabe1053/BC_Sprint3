"""Human-record input validation and camelCase output contracts."""
from datetime import datetime
from typing import Literal
from pydantic import field_validator
from app.api.schemas_base import CamelModel
from app.api.common.schemas.drafts import StrictRequest
from app.domain.record_types import (
    ItemEditInput,
    UndoInput,
    ConfirmationInput,
    JudgementInput,
)


class ItemEditRequest(ItemEditInput, StrictRequest):
    pass


class UndoRequest(UndoInput, StrictRequest):
    pass


class ConfirmationRequest(ConfirmationInput, StrictRequest):
    pass


class JudgementRequest(JudgementInput, StrictRequest):
    @field_validator("note", mode="before")
    @classmethod
    def empty_note(cls, value):
        return None if value == "" else value


class ItemEditRecord(CamelModel):
    edit_id: int
    item_id: int
    field: Literal[
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
    old_value: str | None
    old_state: Literal[
        "stated", "tba", "not_stated", "not_applicable", "numeric"
    ] | None
    new_value: str | None
    new_state: Literal[
        "stated", "tba", "not_stated", "not_applicable", "numeric"
    ] | None
    reason: str
    recorded_by: str
    recorded_at: datetime
    undone_at: datetime | None
    undone_by: str | None


class EditsResponse(CamelModel):
    edits: list[ItemEditRecord]


class EditUndone(CamelModel):
    edit_id: int
    undone_at: datetime
    undone_by: str


class ConfirmationRecord(CamelModel):
    confirmation_id: int
    kind: Literal["row_match", "coverage"]
    item_id: int | None
    recorded_by: str
    recorded_at: datetime


class ConfirmationUndone(CamelModel):
    confirmation_id: int
    undone_at: datetime
    undone_by: str


class JudgementRecord(CamelModel):
    judgement_id: int
    question_id: int
    status: Literal["open", "in_progress", "judged"]
    resolution: Literal["unresolved", "resolved"]
    note: str | None
    recorded_by: str
    recorded_at: datetime


def record_response(schema, row, id_field, **extra):
    """Copy only declared response attributes, renaming the persistence ID."""
    return schema(
        **{
            field: extra[field]
            if field in extra
            else getattr(row, "id" if field == id_field else field)
            for field in schema.model_fields
        }
    )
