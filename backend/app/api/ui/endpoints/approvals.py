"""UI approval history and writes; policy and time remain in the service."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_approval_service
from app.services.approval_service import ApprovalService
from app.api.ui.schemas.approvals import (
    StateEventRequest,
    BounceCommentRequest,
    BounceRequest,
    SendoffDecisionRequest,
    StateEventRecord,
    BounceCommentRecord,
    BounceCreatedRecord,
    BounceRecord,
    SendoffDecisionRecord,
    ConfirmationHistoryRecord,
    RecordsResponse,
)
from app.api.ui.schemas.records import ItemEditRecord, JudgementRecord, record_response

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[ApprovalService, Depends(get_approval_service)]


@router.get("/versions/{versionId}/records", response_model=RecordsResponse)
async def list_records(versionId: Id, service: Service):
    data = await service.list_records(versionId)
    return RecordsResponse(
        edits=[
            record_response(ItemEditRecord, row, "edit_id") for row in data["edits"]
        ],
        confirmations=[
            record_response(ConfirmationHistoryRecord, row, "confirmation_id")
            for row in data["confirmations"]
        ],
        judgements=[
            record_response(JudgementRecord, row, "judgement_id")
            for row in data["judgements"]
        ],
        state_events=[
            record_response(StateEventRecord, row, "state_event_id")
            for row in data["state_events"]
        ],
        bounces=[
            record_response(
                BounceRecord,
                row["bounce"],
                "bounce_id",
                comments=[
                    record_response(BounceCommentRecord, comment, "bounce_comment_id")
                    for comment in row["comments"]
                ],
            )
            for row in data["bounces"]
        ],
        unlinked_comments=[
            record_response(BounceCommentRecord, row, "bounce_comment_id")
            for row in data["unlinked_comments"]
        ],
        sendoff_decisions=[
            record_response(SendoffDecisionRecord, row, "sendoff_decision_id")
            for row in data["sendoff_decisions"]
        ],
    )


@router.post(
    "/versions/{versionId}/state-events",
    status_code=201,
    response_model=StateEventRecord,
)
async def record_state_event(versionId: Id, body: StateEventRequest, service: Service):
    row = await service.transition(versionId, body.model_dump())
    return record_response(StateEventRecord, row, "state_event_id")


@router.post(
    "/versions/{versionId}/bounce-comments",
    status_code=201,
    response_model=BounceCommentRecord,
)
async def record_bounce_comment(
    versionId: Id, body: BounceCommentRequest, service: Service
):
    row = await service.comment(versionId, body.model_dump())
    return record_response(BounceCommentRecord, row, "bounce_comment_id")


@router.post(
    "/versions/{versionId}/bounces", status_code=201, response_model=BounceCreatedRecord
)
async def record_bounce(versionId: Id, body: BounceRequest, service: Service):
    row = await service.bounce(versionId, body.model_dump())
    return record_response(BounceCreatedRecord, row, "bounce_id")


@router.post(
    "/versions/{versionId}/sendoff-decisions",
    status_code=201,
    response_model=SendoffDecisionRecord,
)
async def record_sendoff_decision(
    versionId: Id, body: SendoffDecisionRequest, service: Service
):
    row = await service.decide_sendoff(versionId, body.model_dump())
    return record_response(SendoffDecisionRecord, row, "sendoff_decision_id")
