"""UI approval request validation and explicit human-record responses."""
from datetime import datetime
from pydantic import Field, field_validator
from app.api.schemas_base import CamelModel
from app.api.common.schemas.drafts import StrictRequest
from app.domain.record_types import (
    StateEventInput,
    BounceCommentInput,
    BounceInput,
    SendoffInput,
    VersionState,
    CheckedState,
    SendoffState,
)
from app.api.ui.schemas.records import (
    ItemEditRecord,
    JudgementRecord,
    ConfirmationRecord,
)


class StateEventRequest(StateEventInput, StrictRequest):
    pass


class BounceCommentRequest(BounceCommentInput, StrictRequest):
    pass


class BounceRequest(BounceInput, StrictRequest):
    pass


class SendoffDecisionRequest(SendoffInput, StrictRequest):
    @field_validator("reason", mode="before")
    @classmethod
    def empty_reason(cls, value):
        return None if value == "" else value


class StateEventRecord(CamelModel):
    state_event_id: int
    from_state: VersionState
    to_state: CheckedState
    recorded_by: str
    recorded_at: datetime
    unresolved_count: int = Field(ge=0)


class BounceCommentRecord(CamelModel):
    bounce_comment_id: int
    item_id: int
    bounce_id: int | None
    comment: str
    recorded_by: str
    recorded_at: datetime


class BounceCreatedRecord(CamelModel):
    """The write service returns the bounce row; comments are read through history."""

    bounce_id: int
    reason: str
    recorded_by: str
    recorded_at: datetime


class BounceRecord(BounceCreatedRecord):
    comments: list[BounceCommentRecord]


class SendoffDecisionRecord(CamelModel):
    sendoff_decision_id: int
    decision: SendoffState
    reason: str | None
    recorded_by: str
    recorded_at: datetime


class ConfirmationHistoryRecord(ConfirmationRecord):
    undone_at: datetime | None
    undone_by: str | None


class RecordsResponse(CamelModel):
    edits: list[ItemEditRecord]
    confirmations: list[ConfirmationHistoryRecord]
    judgements: list[JudgementRecord]
    state_events: list[StateEventRecord]
    bounces: list[BounceRecord]
    unlinked_comments: list[BounceCommentRecord]
    sendoff_decisions: list[SendoffDecisionRecord]
