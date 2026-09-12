"""Strict camelCase HTTP contracts; domain validation remains shared with tools."""
from datetime import datetime
from typing import Literal
from pydantic import ConfigDict, Field
from app.api.schemas_base import CamelModel, CamelRequestModel
from app.domain.draft_types import (
    EndInput,
    ItemInput,
    HeaderInput,
    EvidenceInput,
    QuestionInput,
    InventoryInput,
)


class StrictRequest(CamelRequestModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=False,
        validate_by_name=False,
        validate_by_alias=True,
    )


class EndRequest(EndInput, StrictRequest):
    pass


class ItemRequest(ItemInput, StrictRequest):
    ends: list[EndRequest] = Field(default_factory=list)


class HeaderRequest(HeaderInput, StrictRequest):
    pass


class EvidenceRequest(EvidenceInput, StrictRequest):
    pass


class QuestionRequest(QuestionInput, StrictRequest):
    pass


class InventoryRequest(InventoryInput, StrictRequest):
    pass


class ItemsRequest(StrictRequest):
    rows: list[ItemRequest] = Field(min_length=1)


class InventoryBatchRequest(StrictRequest):
    entries: list[InventoryRequest] = Field(min_length=1)


class HeaderCreated(CamelModel):
    header_id: int


class ItemCreated(CamelModel):
    item_id: int
    row_code: str


class ItemsCreated(CamelModel):
    items: list[ItemCreated]
    # Atomic batches have no partially rejected rows; JSON still serializes as [].
    rejected: tuple[()] = ()


class EvidenceCreated(CamelModel):
    evidence_id: int


class QuestionCreated(CamelModel):
    question_id: int


class EntryCreated(CamelModel):
    entry_id: int


class InventoryCreated(CamelModel):
    entries: list[EntryCreated]


class ViolationResponse(CamelModel):
    kind: Literal[
        "missing_evidence",
        "missing_source_no",
        "orphan_candidate",
        "missing_unit",
        "unscanned_range",
        "orphan_question",
        "excluded_without_basis",
    ]
    detail: str
    item_id: int | None = None
    document_id: int | None = None
    locator: str | None = None


class ValidationCounts(CamelModel):
    items: int = Field(ge=0)
    questions: int = Field(ge=0)
    inventory: int = Field(ge=0)


class ValidationResponse(CamelModel):
    violations: list[ViolationResponse]
    counts: ValidationCounts


class FinalizedResponse(CamelModel):
    version_id: int
    current_state: Literal["draft"]
    is_complete: bool
    finalized_at: datetime
