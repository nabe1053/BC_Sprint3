"""#1・#2・#3 案件エンドポイント（UI 専用。05-api-ipo.md 1章 A・5章の要約）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from app.api.schemas_error import ErrorResponse
from app.api.ui.schemas.cases import (
    CaseCreateRequest,
    CaseListItem,
    CaseListResponse,
    CaseResponse,
)
from app.api.ui.schemas.approvals import StateEventRecord
from app.api.ui.schemas.records import record_response
from app.core.dependencies import get_case_service
from app.services.case_service import CaseService

router = APIRouter(prefix="/cases", tags=["cases"])


def _to_case_response(case) -> CaseResponse:
    return CaseResponse(
        case_id=case.id,
        case_code=case.case_code,
        customer_name=case.customer_name,
        title=case.title,
        created_at=case.created_at,
    )


@router.post(
    "",
    response_model=CaseResponse,
    status_code=201,
    responses={409: {"model": ErrorResponse, "description": "caseCode が重複している"}},
)
async def create_case(
    payload: CaseCreateRequest,
    service: CaseService = Depends(get_case_service),
) -> CaseResponse:
    """#2: 案件を作成する。"""
    case = await service.create_case(
        case_code=payload.case_code,
        customer_name=payload.customer_name,
        title=payload.title,
    )
    return _to_case_response(case)


@router.get("", response_model=CaseListResponse)
async def list_cases(
    service: CaseService = Depends(get_case_service),
) -> CaseListResponse:
    """#1: 案件一覧・進捗ステータス。"""
    entries = await service.list_cases()
    items = [
        CaseListItem(
            case_id=entry.case.id,
            case_code=entry.case.case_code,
            customer_name=entry.case.customer_name,
            title=entry.case.title,
            created_at=entry.case.created_at,
            progress_status=entry.progress_status,
            latest_version_id=entry.latest_version_id,
            latest_sendoff=entry.latest_sendoff,
            latest_state_event=record_response(
                StateEventRecord, entry.latest_state_event, "state_event_id"
            )
            if entry.latest_state_event is not None
            else None,
            question_total=entry.question_total,
            unresolved_count=entry.unresolved_count,
        )
        for entry in entries
    ]
    return CaseListResponse(cases=items)


@router.get(
    "/{caseId}",
    response_model=CaseResponse,
    responses={404: {"model": ErrorResponse, "description": "案件が存在しない"}},
)
async def get_case(
    case_id: int = Path(alias="caseId"),
    service: CaseService = Depends(get_case_service),
) -> CaseResponse:
    """#3: 案件詳細。"""
    case = await service.get_case(case_id)
    return _to_case_response(case)
