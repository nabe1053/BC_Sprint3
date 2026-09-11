"""依存注入。

認証は実装しない（CLAUDE.md 決定事項1）。Service は Repository を注入して
構築する（clean-architecture.md: endpoints → services → repositories）。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends

from app.core.database import get_db
from app.repositories.case_repository import CaseRepository
from app.repositories.document_repository import DocumentRepository
from app.services.case_service import CaseService
from app.services.document_intake_service import DocumentIntakeService
from app.services.document_query_service import DocumentQueryService


def get_case_service(session: AsyncSession = Depends(get_db)) -> CaseService:
    return CaseService(CaseRepository(session))


def get_document_intake_service(
    session: AsyncSession = Depends(get_db),
) -> DocumentIntakeService:
    return DocumentIntakeService(DocumentRepository(session))


def get_document_query_service(
    session: AsyncSession = Depends(get_db),
) -> DocumentQueryService:
    return DocumentQueryService(DocumentRepository(session), CaseRepository(session))


__all__ = [
    "get_db",
    "get_case_service",
    "get_document_intake_service",
    "get_document_query_service",
]
