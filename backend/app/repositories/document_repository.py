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

    async def get_by_id(self, document_id: int) -> Document | None:
        return await self.session.get(Document, document_id)

    async def list_pages(
        self,
        document_id: int,
        from_seq: int | None = None,
        to_seq: int | None = None,
    ) -> list[DocumentPage]:
        """資料のページを seq 範囲で取得する（05-api-ipo.md 0.4 `fromSeq`/`toSeq`。
        1始まり・両端を含む・省略時は資料全体）。"""
        stmt = select(DocumentPage).where(DocumentPage.document_id == document_id)
        if from_seq is not None:
            stmt = stmt.where(DocumentPage.seq >= from_seq)
        if to_seq is not None:
            stmt = stmt.where(DocumentPage.seq <= to_seq)
        stmt = stmt.order_by(DocumentPage.seq)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_email_parts(self, document_id: int) -> list[EmailPart]:
        stmt = (
            select(EmailPart)
            .where(EmailPart.document_id == document_id)
            .order_by(EmailPart.seq)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_pages(
        self, case_id: int, query: str, limit: int
    ) -> list[tuple[Document, DocumentPage]]:
        """案件内の資料本文から検索語に一致するページを返す（05-api-ipo.md #8）。

        reviewer 指摘 軽-2: `query` に `%` `_` （ILIKE のワイルドカード）が
        含まれていてもリテラルとして扱う（エスケープする）。
        """
        escaped_query = (
            query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        stmt = (
            select(Document, DocumentPage)
            .join(DocumentPage, DocumentPage.document_id == Document.id)
            .where(
                Document.case_id == case_id,
                DocumentPage.text.ilike(f"%{escaped_query}%", escape="\\"),
            )
            .order_by(DocumentPage.document_id, DocumentPage.seq)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [tuple(row) for row in result.all()]

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
