"""#5 資料投入・#10 原ファイル取得エンドポイント（UI 専用）。

reviewer 指摘 重-1: endpoint はストリーム読取だけを行う。サイズ上限の判定
（算術）は `DocumentIntakeService.assert_within_size_limit()` に委譲し、
保存パス生成（uuid4）・ファイル書き込みは Service 経由で
`DocumentStorageGateway`（Data Access層）が行う（endpoints には業務ロジック・
生ファイル I/O を書かない）。

サイズ上限超過（決定2）はチャンク読取の途中で打ち切り、Service（保存）を
呼ばずに 413 を返す（超過分を全部メモリに載せない・ディスクにも書かない）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Path, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas_error import ErrorResponse
from app.api.ui.schemas.documents import DocumentIntakeResponse
from app.core.dependencies import (
    get_case_service,
    get_document_intake_service,
    get_document_query_service,
)
from app.services.case_service import CaseService
from app.services.document_intake_service import DocumentIntakeService
from app.services.document_query_service import DocumentQueryService

router = APIRouter(tags=["documents-intake"])

_CHUNK_SIZE = 1024 * 1024


@router.post(
    "/cases/{caseId}/documents",
    response_model=DocumentIntakeResponse,
    status_code=201,
    responses={
        404: {"model": ErrorResponse, "description": "案件が存在しない"},
        413: {"model": ErrorResponse, "description": "サイズ・件数等の上限超過"},
        415: {"model": ErrorResponse, "description": "未対応の資料形式"},
    },
)
async def intake_document(
    case_id: int = Path(alias="caseId"),
    file: UploadFile = File(...),
    case_service: CaseService = Depends(get_case_service),
    intake_service: DocumentIntakeService = Depends(get_document_intake_service),
) -> DocumentIntakeResponse:
    """#5: 資料投入。

    案件存在確認 → チャンク読取（上限超過は 413・Service を呼ばず記録を残さない）
    → Service（上限判定・保存先決定・抽出・read_status 決定・保存）。
    """
    await case_service.get_case(case_id)  # 存在しなければ E_NOT_FOUND（404）

    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        # 決定2: 全部メモリに載せる前に打ち切る。上限バイト数の算術は
        # Service 側の述語に委譲する（endpoints に業務ロジックを書かない）。
        intake_service.assert_within_size_limit(total_size)
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    document = await intake_service.intake_document(
        case_id=case_id,
        file_name=file.filename or "unknown",
        file_bytes=file_bytes,
    )

    return DocumentIntakeResponse(
        document_id=document.id,
        read_status=document.read_status,
    )


@router.get(
    "/documents/{documentId}/file",
    response_class=FileResponse,
    responses={
        200: {"content": {"application/octet-stream": {}}},
        404: {"model": ErrorResponse, "description": "資料が存在しない"},
    },
)
async def get_file(
    document_id: int = Path(alias="documentId"),
    service: DocumentQueryService = Depends(get_document_query_service),
) -> FileResponse:
    """#10: 原ファイル（読取専用）。STORAGE_ROOT 配下でなければ 404。"""
    path = await service.get_file_path(document_id)
    return FileResponse(path)
