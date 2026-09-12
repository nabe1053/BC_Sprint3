"""Finalized-version read contracts; explicit response field whitelists."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import Field
from app.api.schemas_base import CamelModel
from app.api.ui.schemas.records import ItemEditRecord, JudgementRecord

ValueState = Literal["stated", "tba", "not_stated", "not_applicable"]
VersionState = Literal["draft", "staff_checked", "review_checked"]


class VersionListItem(CamelModel):
    version_id: int
    version_no: int
    current_state: VersionState
    finalized_at: datetime
    is_complete: bool
    created_at: datetime


class VersionsResponse(CamelModel):
    versions: list[VersionListItem]


class CaseHeaderResponse(CamelModel):
    inquiry_no: str | None = None
    inquiry_no_state: Literal["stated", "not_stated"]
    customer_name: str | None = None
    customer_name_state: Literal["stated", "not_stated"]
    due_raw: str | None = None
    due_state: Literal["stated", "tba", "not_stated"]
    due_granularity: Literal[
        "date", "month", "quarter", "period", "month_end", "unknown"
    ] | None = None
    due_basis: Literal["shipment", "arrival", "unknown"] | None = None
    place_raw: str | None = None
    place_state: Literal["stated", "not_stated", "not_applicable"]
    incoterms: str | None = None
    incoterms_state: Literal["stated", "not_stated", "not_applicable"]
    quote_deadline_raw: str | None = None
    quote_deadline_at: datetime | None = None
    quote_deadline_tz_state: Literal["stated", "missing"]


class VersionCounts(CamelModel):
    item_count: int
    question_item_count: int
    tba_item_count: int
    choice_group_count: int
    matched_count: int
    edit_count: int
    edited_item_count: int
    unresolved_count: int


class VersionResponse(CamelModel):
    version_id: int
    case_id: int
    version_no: int
    current_state: VersionState
    is_complete: bool
    finalized_at: datetime
    case_header: CaseHeaderResponse | None
    counts: VersionCounts
    coverage_confirmed: bool


class ItemCurrentResponse(CamelModel):
    item_id: int
    row_code: str
    source_no: str
    seq: int = Field(ge=1)
    kind: str
    kind_raw: str
    usage_note: str | None = None
    od_value: Decimal | None = None
    od_unit: str | None = None
    od_raw: str | None = None
    od_state: ValueState
    wall_value: Decimal | None = None
    wall_unit: str | None = None
    wall_raw: str | None = None
    wall_state: ValueState
    weight_value: Decimal | None = None
    weight_unit: str | None = None
    weight_raw: str | None = None
    weight_state: ValueState
    grade: str | None = None
    grade_raw: str
    grade_state: ValueState
    connection: str | None = None
    connection_raw: str | None = None
    connection_state: ValueState
    range_class: str | None = None
    length_value: Decimal | None = None
    length_unit: str | None = None
    length_raw: str | None = None
    length_state: ValueState
    qty_value: Decimal | None = None
    qty_unit: str | None = None
    qty_state: Literal["numeric", "tba", "not_stated", "not_applicable"]
    qty_raw: str
    qty_reference_note: str | None = None
    due_raw: str | None = None
    due_state: ValueState
    place_raw: str | None = None
    place_state: ValueState
    note: str | None = None
    group_code: str | None = None
    candidate_label: str | None = None
    is_inherit_candidate: bool = False
    history: list[ItemEditRecord]


class ItemsResponse(CamelModel):
    items: list[ItemCurrentResponse]


class EvidenceResponse(CamelModel):
    evidence_id: int
    field: str
    raw_value: str
    adopted_value: str
    document_id: int
    locator: str
    quote: str
    applied_condition: str | None
    conversion_note: str | None
    change_reason: str | None
    prior_value: str | None


class ItemEvidenceResponse(CamelModel):
    item_id: int
    evidences: list[EvidenceResponse]


class QuestionResponse(CamelModel):
    question_id: int
    question_code: str
    item_id: int | None
    target_field: str
    reason: str
    candidates: str | None
    category: Literal[
        "unknown",
        "conflict",
        "reference_missing",
        "alternative",
        "condition_missing",
        "inherit_candidate",
    ] | None
    latest: JudgementRecord | None


class QuestionsResponse(CamelModel):
    questions: list[QuestionResponse]
