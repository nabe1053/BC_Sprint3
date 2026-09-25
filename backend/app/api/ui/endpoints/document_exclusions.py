"""#5a 資料の除外・#5b 除外済みの一覧（UI 専用・F-16）。人の記録なので /agent/* に置かない。"""
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.ui.schemas.documents import (
    DocumentExclusionRecord,
    DocumentExclusionRequest,
    DocumentExclusionsResponse,
    ExcludedDocument,
)
from app.core.dependencies import get_document_exclusion_service
from app.services.document_exclusion_service import DocumentExclusionService

router = APIRouter(
    route_class=DraftRoute, responses=ERROR_RESPONSES, tags=["documents-intake"]
)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[DocumentExclusionService, Depends(get_document_exclusion_service)]


@router.post(
    "/cases/{caseId}/documents/{documentId}/exclusion",
    status_code=201,
    response_model=DocumentExclusionRecord,
)
async def exclude_document(
    caseId: Id, documentId: Id, body: DocumentExclusionRequest, service: Service
):
    row = await service.exclude(caseId, documentId, body.model_dump())
    return DocumentExclusionRecord(
        document_id=row.document_id,
        recorded_by=row.recorded_by,
        recorded_at=row.recorded_at,
    )


@router.get(
    "/cases/{caseId}/document-exclusions", response_model=DocumentExclusionsResponse
)
async def list_document_exclusions(caseId: Id, service: Service):
    rows = await service.list_exclusions(caseId)
    return DocumentExclusionsResponse(
        exclusions=[
            ExcludedDocument(
                document_id=document.id,
                file_name=document.file_name,
                recorded_by=exclusion.recorded_by,
                recorded_at=exclusion.recorded_at,
            )
            for document, exclusion in rows
        ]
    )
