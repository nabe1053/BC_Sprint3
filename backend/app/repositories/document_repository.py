"""DocumentRepository（Data Access層）。

04-db.md 3.1 A層 `documents` / `document_pages` / `email_parts` / `document_issues`。
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart


class DocumentRepository:
    """資料本体と付随レコード（ページ・メールパート・issue）への CRUD。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_with_details(
        self,
        document: Document,
        pages: list[DocumentPage] | None = None,
        email_parts: list[EmailPart] | None = None,
        issues: list[DocumentIssue] | None = None,
    ) -> Document:
        """document と付随レコードをまとめて保存する（1トランザクション）。"""
        self.session.add(document)
        await self.session.flush()

        for page in pages or []:
            page.document_id = document.id
            self.session.add(page)
        for part in email_parts or []:
            part.document_id = document.id
            self.session.add(part)
        for issue in issues or []:
            issue.document_id = document.id
            self.session.add(issue)

        await self.session.commit()
        await self.session.refresh(document)
        return document

    async def list_by_case(self, case_id: int) -> list[Document]:
        stmt = select(Document).where(Document.case_id == case_id).order_by(Document.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_case(self, case_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.case_id == case_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_page_by_locator(
        self, document_id: int, locator: str
    ) -> DocumentPage | None:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id, DocumentPage.locator == locator
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_issue(self, issue: DocumentIssue) -> DocumentIssue:
        self.session.add(issue)
        await self.session.commit()
        await self.session.refresh(issue)
        return issue
