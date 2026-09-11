"""#4・#6・#7 参照系エンドポイント（UI/AGENT 共通ハンドラ）。

05-api-ipo.md 0.3「参照系は `/ui/*` と `/agent/*` の両方に同一ハンドラを登録する」。
この router を `app/api/ui/router.py` と `app/api/agent/router.py` の両方から
`include_router()` することで、1つの実装を両パスに公開する
（`tests/integration/test_api_path_separation_t102.py` が両方の存在を検査する）。

reviewer 指摘 中-1: ページ単位 `readStatus` の導出（業務判断）は
`DocumentQueryService` 側に移した（本ファイルには残さない）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.api.schemas_common import (
    ContentResponse,
    DocumentsListResponse,
    DocumentSummary,
    EmailPartResponse,
    EmailResponse,
    PageContent,
)
from app.api.schemas_error import ErrorResponse
from app.core.dependencies import get_document_query_service
from app.services.document_query_service import DocumentQueryService

router = APIRouter(tags=["documents-reference"])


@router.get(
    "/cases/{caseId}/documents",
    response_model=DocumentsListResponse,
    responses={404: {"model": ErrorResponse, "description": "案件が存在しない"}},
)
async def list_documents(
    case_id: int = Path(alias="caseId"),
    service: DocumentQueryService = Depends(get_document_query_service),
) -> DocumentsListResponse:
    """#4: 案件配下の資料一覧・読取状態。"""
    case, documents = await service.list_documents_for_case(case_id)
    return DocumentsListResponse(
        case_id=case.id,
        case_name=case.title,
        documents=[
            DocumentSummary(
                document_id=d.id,
                file_name=d.file_name,
                kind=d.kind,
                read_status=d.read_status,
            )
            for d in documents
        ],
    )


@router.get(
    "/documents/{documentId}/content",
    response_model=ContentResponse,
    responses={
        404: {"model": ErrorResponse, "description": "資料が存在しない"},
        409: {"model": ErrorResponse, "description": "要求範囲が全体として読取不能"},
    },
)
async def get_content(
    document_id: int = Path(alias="documentId"),
    from_seq: int | None = Query(default=None, alias="fromSeq", ge=1),
    to_seq: int | None = Query(default=None, alias="toSeq", ge=1),
    service: DocumentQueryService = Depends(get_document_query_service),
) -> ContentResponse:
    """#6: 本文取得（`fromSeq`/`toSeq` 範囲指定・1始まり・両端を含む）。"""
    # 軽-3: fromSeq > toSeq は契約違反として 422（409 E_UNREADABLE に落とさない。
    # 05-api-ipo.md 6章に該当コードが無いため、新設せず標準の入力検証として扱う）。
    if from_seq is not None and to_seq is not None and from_seq > to_seq:
        raise HTTPException(
            status_code=422, detail="fromSeq は toSeq 以下でなければなりません"
        )

    pages = await service.get_content(document_id, from_seq, to_seq)
    return ContentResponse(
        pages=[
            PageContent(
                locator=page.locator,
                text=page.text,
                cells=page.cells,
                read_status=read_status,
            )
            for page, read_status in pages
        ]
    )


@router.get(
    "/documents/{documentId}/email",
    response_model=EmailResponse,
    responses={
        404: {"model": ErrorResponse, "description": "資料が存在しない"},
        409: {"model": ErrorResponse, "description": ".eml 資料ではない"},
    },
)
async def get_email(
    document_id: int = Path(alias="documentId"),
    service: DocumentQueryService = Depends(get_document_query_service),
) -> EmailResponse:
    """#7: .eml の構造（本文・引用部・添付一覧）。"""
    parts = await service.get_email(document_id)
    return EmailResponse(
        parts=[
            EmailPartResponse(
                part_role=p.part_role,
                seq=p.seq,
                sent_at=p.sent_at,
                from_addr=p.from_addr,
                subject=p.subject,
                body=p.body,
                attachment_name=p.attachment_name,
            )
            for p in parts
        ]
    )
