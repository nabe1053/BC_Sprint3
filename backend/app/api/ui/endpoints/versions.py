"""UI-only finalized version reads (#22 minimum and #23–26)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_record_service
from app.services.record_service import RecordService
from app.api.ui.schemas.records import ItemEditRecord, JudgementRecord, record_response
from app.api.ui.schemas.versions import (
    VersionListItem,
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
async def list_versions(caseId: Id, service: Service):
    rows = await service.list_versions(caseId)
    return VersionsResponse(
        versions=[record_response(VersionListItem, row, "version_id") for row in rows]
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
