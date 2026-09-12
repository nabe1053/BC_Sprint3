"""UI-only human record writes (#29–33); policy stays in RecordService."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_record_service
from app.services.record_service import RecordService
from app.api.ui.schemas.records import (
    ItemEditRequest,
    UndoRequest,
    ConfirmationRequest,
    JudgementRequest,
    ItemEditRecord,
    EditsResponse,
    EditUndone,
    ConfirmationRecord,
    ConfirmationUndone,
    JudgementRecord,
    record_response,
)

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[RecordService, Depends(get_record_service)]


@router.post(
    "/versions/{versionId}/edits", status_code=201, response_model=EditsResponse
)
async def edit_item(versionId: Id, body: ItemEditRequest, service: Service):
    rows = await service.edit(versionId, body.model_dump())
    return EditsResponse(
        edits=[record_response(ItemEditRecord, row, "edit_id") for row in rows]
    )


@router.post("/versions/{versionId}/edits/{editId}/undo", response_model=EditUndone)
async def undo_edit(versionId: Id, editId: Id, body: UndoRequest, service: Service):
    row = await service.undo_edit(versionId, editId, body.model_dump())
    return record_response(EditUndone, row, "edit_id")


@router.post(
    "/versions/{versionId}/confirmations",
    status_code=201,
    response_model=ConfirmationRecord,
)
async def confirm(versionId: Id, body: ConfirmationRequest, service: Service):
    row = await service.confirm(versionId, body.model_dump())
    return record_response(ConfirmationRecord, row, "confirmation_id")


@router.post(
    "/versions/{versionId}/confirmations/{confirmationId}/undo",
    response_model=ConfirmationUndone,
)
async def undo_confirmation(
    versionId: Id, confirmationId: Id, body: UndoRequest, service: Service
):
    row = await service.undo_confirmation(versionId, confirmationId, body.model_dump())
    return record_response(ConfirmationUndone, row, "confirmation_id")


@router.post(
    "/versions/{versionId}/questions/{questionId}/judgements",
    status_code=201,
    response_model=JudgementRecord,
)
async def judge(
    versionId: Id, questionId: Id, body: JudgementRequest, service: Service
):
    row = await service.judge(versionId, questionId, body.model_dump())
    return record_response(JudgementRecord, row, "judgement_id")
