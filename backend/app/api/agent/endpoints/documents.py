"""#8・#9 エージェント専用エンドポイント（05-api-ipo.md 5章 #8・#9）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from app.api.agent.schemas.documents import (
    IssueCreateRequest,
    IssueCreateResponse,
    SearchResponse,
    SearchResultItem,
)
from app.api.schemas_error import ErrorResponse
from app.core.dependencies import get_document_query_service
from app.services.document_query_service import DocumentQueryService

router = APIRouter(tags=["agent-documents"])


@router.get(
    "/cases/{caseId}/search",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "検索語が空"},
        404: {"model": ErrorResponse, "description": "案件が存在しない"},
    },
)
async def search(
    case_id: int = Path(alias="caseId"),
    q: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=100),
    service: DocumentQueryService = Depends(get_document_query_service),
) -> SearchResponse:
    """#8: 案件内の資料本文を全文検索する。検索語が空なら E_QUERY_REQUIRED。"""
    results = await service.search(case_id, q, limit)
    return SearchResponse(
        results=[
            SearchResultItem(
                document_id=document.id, locator=page.locator, excerpt=excerpt
            )
            for document, page, excerpt in results
        ]
    )


@router.post(
    "/documents/{documentId}/issues",
    response_model=IssueCreateResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "detail が空"},
        404: {"model": ErrorResponse, "description": "資料が存在しない"},
    },
)
async def report_issue(
    document_id: int = Path(alias="documentId"),
    payload: IssueCreateRequest = ...,
    service: DocumentQueryService = Depends(get_document_query_service),
) -> IssueCreateResponse:
    """#9: 読取不能・未走査範囲の記録。detail が空なら E_DETAIL_REQUIRED。"""
    issue = await service.report_issue(
        document_id=document_id,
        locator=payload.locator,
        issue_type=payload.issue_type,
        detail=payload.detail,
    )
    return IssueCreateResponse(issue_id=issue.id)
