"""Download preserved workbook bytes and read export/evidence metadata."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Request, Response
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_export_service
from app.api.ui.schemas.exports import (
    ExportRecord,
    ExportsResponse,
    VersionEvidenceRecord,
    VersionEvidenceResponse,
)
from app.api.ui.schemas.records import record_response
from app.domain.draft_errors import DraftError
from app.services.export_service import ExportService

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[ExportService, Depends(get_export_service)]


@router.post(
    "/versions/{versionId}/exports",
    response_class=Response,
    responses={
        200: {
            "description": "保存済みの出力と同一のxlsxバイト列",
            "content": {
                XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}
            },
            "headers": {
                "Content-Disposition": {
                    "schema": {"type": "string"},
                    "description": "attachment; filename=ASCII安全なファイル名",
                },
                "X-Export-Id": {
                    "schema": {"type": "integer", "minimum": 1},
                    "description": "出力履歴のID",
                },
            },
        }
    },
)
async def create_export(versionId: Id, request: Request, service: Service):
    if await request.body():
        raise DraftError("E_REQUEST_INVALID", "出力リクエストに本文は指定できません")
    result = await service.export(versionId)
    return Response(
        content=result.content,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{result.record.file_name}"',
            "X-Export-Id": str(result.record.id),
        },
    )


@router.get("/versions/{versionId}/exports", response_model=ExportsResponse)
async def list_exports(versionId: Id, service: Service):
    return ExportsResponse(
        exports=[
            ExportRecord.model_validate(row, from_attributes=True)
            for row in await service.list_exports(versionId)
        ]
    )


@router.get("/versions/{versionId}/evidence", response_model=VersionEvidenceResponse)
async def list_version_evidence(versionId: Id, service: Service):
    return VersionEvidenceResponse(
        evidences=[
            record_response(VersionEvidenceRecord, row, "evidence_id")
            for row in await service.list_evidence(versionId)
        ]
    )
