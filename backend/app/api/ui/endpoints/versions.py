"""UI-only finalized version reads (#22 minimum and #23–26)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_record_service, get_approval_service
from app.services.approval_service import ApprovalService
from app.api.ui.schemas.approvals import (
    StateEventRecord,
    BounceRecord,
    SendoffDecisionRecord,
)
from app.services.record_service import RecordService
from app.api.ui.schemas.records import ItemEditRecord, JudgementRecord, record_response
from app.api.ui.schemas.versions import (
    VersionListItem,
    CarryOverResponse,
    VersionsResponse,
    CaseHeaderResponse,
    VersionCounts,
    VersionResponse,
    ItemCurrentResponse,
    RowMatchResponse,
    ItemsResponse,
    EvidenceResponse,
    ItemEvidenceResponse,
    QuestionResponse,
    QuestionsResponse,
)

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[RecordService, Depends(get_record_service)]


@router.get("/cases/{caseId}/versions", response_model=VersionsResponse)
async def list_versions(
    caseId: Id, service: Annotated[ApprovalService, Depends(get_approval_service)]
):
    rows = await service.list_versions_with_records(caseId)
    return VersionsResponse(
        versions=[
            record_response(
                VersionListItem,
                row["version"],
                "version_id",
                unresolved_count=row["unresolved_count"],
                carry_over=CarryOverResponse.model_validate(
                    row["carry_over"], from_attributes=True
                ),
                latest_state_event=record_response(
                    StateEventRecord, row["latest_state_event"], "state_event_id"
                )
                if row["latest_state_event"]
                else None,
                latest_bounce=record_response(
                    BounceRecord, row["latest_bounce"], "bounce_id", comments=[]
                )
                if row["latest_bounce"]
                else None,
                latest_sendoff=record_response(
                    SendoffDecisionRecord,
                    row["latest_sendoff_decision"],
                    "sendoff_decision_id",
                )
                if row["latest_sendoff_decision"]
                else None,
                bounced=row["bounced"],
                needs_recheck=row["needs_recheck"],
                elapsed_sec=row["elapsed_sec"],
            )
            for row in rows
        ]
    )


@router.get("/versions/{versionId}", response_model=VersionResponse)
async def get_version(versionId: Id, service: Service):
    data = await service.summary(versionId)
    header = data["case_header"]
    return VersionResponse(
        **{
            **data,
            "counts": VersionCounts(**data),
            "case_header": CaseHeaderResponse.model_validate(
                header, from_attributes=True
            )
            if header is not None
            else None,
        }
    )


@router.get("/versions/{versionId}/items", response_model=ItemsResponse)
async def list_items(versionId: Id, service: Service):
    rows = await service.list_items_with_edits(versionId)
    return ItemsResponse(
        items=[
            ItemCurrentResponse(
                **{
                    key: value
                    for key, value in row.values.items()
                    if key in ItemCurrentResponse.model_fields
                },
                item_id=row.values["id"],
                row_match=RowMatchResponse.model_validate(
                    row.row_match, from_attributes=True
                )
                if row.row_match is not None
                else None,
                history=[
                    record_response(ItemEditRecord, edit, "edit_id")
                    for edit in row.history
                ],
            )
            for row in rows
        ]
    )


@router.get(
    "/versions/{versionId}/items/{itemId}/evidence", response_model=ItemEvidenceResponse
)
async def list_evidence(versionId: Id, itemId: Id, service: Service):
    rows = await service.list_item_evidence(versionId, itemId)
    return ItemEvidenceResponse(
        item_id=itemId,
        evidences=[
            record_response(EvidenceResponse, row, "evidence_id") for row in rows
        ],
    )


@router.get("/versions/{versionId}/questions", response_model=QuestionsResponse)
async def list_questions(versionId: Id, service: Service):
    rows = await service.list_questions_with_latest(versionId)
    return QuestionsResponse(
        questions=[
            record_response(
                QuestionResponse,
                row["question"],
                "question_id",
                latest=record_response(JudgementRecord, row["latest"], "judgement_id")
                if row["latest"] is not None
                else None,
            )
            for row in rows
        ]
    )
