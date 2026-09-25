"""DocumentRepository（Data Access層）。

04-db.md 3.1 A層 `documents` / `document_pages` / `email_parts` / `document_issues`。
"""

from __future__ import annotations

import re

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.draft_errors import DraftError
from app.models.agent_runs import AgentRun
from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.models.records import DocumentExclusion

# 「読取不能の対象範囲」として受付一覧に出す issue 種別。reference_missing は付随情報の
# 欠落であり、読めなかった範囲ではない（04-db.md §3.3 T-201 補足）。
_UNREADABLE_ISSUE_TYPES = ("unreadable_page", "encrypted", "unsupported")


def _locator_order(locator: str) -> list:
    """`p.10` が `p.2` より前に来ないよう、数字部分を数値として並べる。"""
    return [
        int(part) if part.isdigit() else part for part in re.split(r"(\d+)", locator)
    ]


def active_document():
    """除外されていない資料（F-16・04-db `document_exclusions`）の条件。"""
    return ~exists().where(DocumentExclusion.document_id == Document.id)


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
        """除外済み（F-16）を除いた案件の資料。"""
        stmt = (
            select(Document)
            .where(Document.case_id == case_id, active_document())
            .order_by(Document.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_intake_unreadable_locators(
        self, document_ids: list[int]
    ) -> dict[int, list[str]]:
        """受付時（agent_run_id IS NULL）に記録した読取不能範囲を資料ごとに返す。

        範囲の無い資料全体の issue は含めない（資料全体の不能は read_status が表す）。
        """
        if not document_ids:
            return {}
        stmt = select(DocumentIssue.document_id, DocumentIssue.locator).where(
            DocumentIssue.document_id.in_(document_ids),
            DocumentIssue.agent_run_id.is_(None),
            DocumentIssue.locator.is_not(None),
            DocumentIssue.issue_type.in_(_UNREADABLE_ISSUE_TYPES),
        )
        found: dict[int, set[str]] = {}
        for document_id, locator in (await self.session.execute(stmt)).all():
            found.setdefault(document_id, set()).add(locator)
        return {
            document_id: sorted(locators, key=_locator_order)
            for document_id, locators in found.items()
        }

    async def count_by_case(self, case_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.case_id == case_id, active_document())
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
                active_document(),
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

    async def is_excluded(self, document_id: int) -> bool:
        stmt = select(exists().where(DocumentExclusion.document_id == document_id))
        return bool((await self.session.execute(stmt)).scalar())

    async def list_exclusions(
        self, case_id: int
    ) -> list[tuple[Document, DocumentExclusion]]:
        """除外済みの資料と除外記録（#5b）。"""
        stmt = (
            select(Document, DocumentExclusion)
            .join(DocumentExclusion, DocumentExclusion.document_id == Document.id)
            .where(Document.case_id == case_id)
            .order_by(DocumentExclusion.recorded_at, DocumentExclusion.id)
        )
        return [tuple(row) for row in (await self.session.execute(stmt)).all()]

    async def exclude(
        self, case_id: int, document_id: int, recorded_by: str, recorded_at
    ) -> DocumentExclusion:
        """資料を除外する（#5a）。案の作成（#12）と同じ案件の行ロックの中で、
        実行中の run が無いことを確かめてから追記する（起動との競合で除外済みを読ませない）。"""
        case = (
            await self.session.execute(
                select(Case).where(Case.id == case_id).with_for_update()
            )
        ).scalar_one_or_none()
        document = await self.session.get(Document, document_id)
        if case is None or document is None or document.case_id != case_id:
            await self.session.rollback()
            raise DraftError("E_NOT_FOUND", "資料が存在しません")
        running = (
            await self.session.execute(
                select(AgentRun.id).where(
                    AgentRun.case_id == case_id, AgentRun.outcome == "running"
                )
            )
        ).first()
        if running:
            await self.session.rollback()
            raise DraftError("E_RUN_IN_PROGRESS", "この案件は実行中です")
        if await self.is_excluded(document_id):
            await self.session.rollback()
            raise DraftError("E_ALREADY_EXCLUDED", "この資料は除外済みです")
        record = DocumentExclusion(
            document_id=document_id, recorded_by=recorded_by, recorded_at=recorded_at
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
