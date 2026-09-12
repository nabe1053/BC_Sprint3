"""Agent-only artifact writes (#15–19, #21)."""
from fastapi import APIRouter, Depends, Path
from typing import Annotated
from app.api.dependencies_t202 import get_draft_service
from app.api.routes_t202 import DraftRoute, ERROR_RESPONSES
from app.api.schemas_drafts import (
    HeaderRequest,
    HeaderCreated,
    ItemsRequest,
    ItemsCreated,
    ItemCreated,
    EvidenceRequest,
    EvidenceCreated,
    QuestionRequest,
    QuestionCreated,
    InventoryBatchRequest,
    InventoryCreated,
    EntryCreated,
    FinalizedResponse,
)
from app.services.draft_service import DraftService

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
VersionId = Annotated[int, Path(gt=0)]
Service = Annotated[DraftService, Depends(get_draft_service)]


@router.post(
    "/versions/{versionId}/header", status_code=201, response_model=HeaderCreated
)
async def save_header(versionId: VersionId, body: HeaderRequest, service: Service):
    row = await service.save_header(versionId, body.model_dump())
    return HeaderCreated(header_id=row.id)


@router.post(
    "/versions/{versionId}/items", status_code=201, response_model=ItemsCreated
)
async def add_items(versionId: VersionId, body: ItemsRequest, service: Service):
    rows = await service.add_items(versionId, [r.model_dump() for r in body.rows])
    return ItemsCreated(
        items=[ItemCreated(item_id=r.id, row_code=r.row_code) for r in rows]
    )


@router.post(
    "/versions/{versionId}/evidence", status_code=201, response_model=EvidenceCreated
)
async def add_evidence(versionId: VersionId, body: EvidenceRequest, service: Service):
    rows = await service.add_evidences(versionId, [body.model_dump()])
    return EvidenceCreated(evidence_id=rows[0].id)


@router.post(
    "/versions/{versionId}/questions", status_code=201, response_model=QuestionCreated
)
async def add_question(versionId: VersionId, body: QuestionRequest, service: Service):
    rows = await service.add_questions(versionId, [body.model_dump()])
    return QuestionCreated(question_id=rows[0].id)


@router.post(
    "/versions/{versionId}/inventory", status_code=201, response_model=InventoryCreated
)
async def add_inventory(
    versionId: VersionId, body: InventoryBatchRequest, service: Service
):
    rows = await service.add_inventory(
        versionId, [r.model_dump() for r in body.entries]
    )
    return InventoryCreated(entries=[EntryCreated(entry_id=r.id) for r in rows])


@router.post("/versions/{versionId}/finalize", response_model=FinalizedResponse)
async def finalize(versionId: VersionId, service: Service):
    row = await service.finalize(versionId)
    return FinalizedResponse(
        version_id=row.id,
        current_state=row.current_state,
        is_complete=row.is_complete,
        finalized_at=row.finalized_at,
    )
