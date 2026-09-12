"""Finalized-version human records, serialized with the version row lock."""
from contextlib import asynccontextmanager

from sqlalchemy import select

from app.domain.draft_errors import DraftError
from app.models import (
    Case,
    CaseHeader,
    Confirmation,
    Evidence,
    Item,
    ItemEdit,
    Question,
    QuestionJudgement,
    Version,
)
from app.repositories.draft_repository import DraftRepository, require


class RecordRepository:
    def __init__(self, session):
        self.session = session

    _transaction = DraftRepository._transaction

    async def version(self, version_id, *, lock=False):
        statement = select(Version).where(Version.id == version_id)
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        version = (await self.session.execute(statement)).scalar_one_or_none()
        require(version is not None and version.finalized_at is not None)
        return version

    @asynccontextmanager
    async def record(self, version_id):
        try:
            async with self._transaction():
                await self.version(version_id, lock=True)
                yield
        except DraftError as exc:
            original = getattr(exc.__cause__, "orig", None)
            state = getattr(original, "sqlstate", None)
            constraint = getattr(
                getattr(original, "diag", None), "constraint_name", None
            )
            if state == "23505" and constraint in {
                "uq_confirmations_row_match_active",
                "uq_confirmations_coverage_active",
            }:
                raise DraftError(
                    "E_ALREADY_CONFIRMED", "未取消の確認が存在します"
                ) from exc
            if state == "23503":
                raise DraftError(
                    "E_NOT_FOUND", "対象が存在しないか版が一致しません"
                ) from exc
            raise

    async def item(self, version_id, item_id, code="E_NOT_FOUND"):
        item = await self.session.get(Item, item_id)
        require(item is not None and item.version_id == version_id, code)
        return item

    async def edits(self, version_id, item_id):
        return list(
            (
                await self.session.execute(
                    select(ItemEdit)
                    .where(
                        ItemEdit.version_id == version_id,
                        ItemEdit.item_id == item_id,
                    )
                    .order_by(ItemEdit.recorded_at, ItemEdit.id)
                )
            ).scalars()
        )

    async def save_edits(self, version_id, rows):
        records = [ItemEdit(version_id=version_id, **row) for row in rows]
        self.session.add_all(records)
        await self.session.flush()
        return records

    async def get_edit(self, version_id, edit_id):
        row = await self.session.get(ItemEdit, edit_id, populate_existing=True)
        require(row is not None and row.version_id == version_id)
        return row

    async def undo(self, row, at, by):
        row.undone_at, row.undone_by = at, by
        await self.session.flush()
        return row

    async def active_confirmation(self, version_id, kind, item_id):
        return (
            await self.session.execute(
                select(Confirmation).where(
                    Confirmation.version_id == version_id,
                    Confirmation.kind == kind,
                    Confirmation.item_id == item_id,
                    Confirmation.undone_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    async def save_confirmation(self, version_id, data):
        record = Confirmation(version_id=version_id, **data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_confirmation(self, version_id, confirmation_id):
        row = await self.session.get(
            Confirmation, confirmation_id, populate_existing=True
        )
        require(row is not None and row.version_id == version_id)
        return row

    async def question(self, version_id, question_id):
        row = await self.session.get(Question, question_id)
        require(row is not None and row.version_id == version_id)
        return row

    async def save_judgement(self, question_id, data):
        row = QuestionJudgement(question_id=question_id, **data)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_items_with_edits(self, version_id):
        await self.version(version_id)
        items = list(
            (
                await self.session.execute(
                    select(Item)
                    .where(Item.version_id == version_id)
                    .order_by(Item.seq, Item.id)
                )
            ).scalars()
        )
        edits = list(
            (
                await self.session.execute(
                    select(ItemEdit)
                    .where(ItemEdit.version_id == version_id)
                    .order_by(ItemEdit.recorded_at, ItemEdit.id)
                )
            ).scalars()
        )
        by_item = {}
        for edit in edits:
            by_item.setdefault(edit.item_id, []).append(edit)
        from app.domain.record_types import RowMatch

        confirmations = (
            await self.session.execute(
                select(Confirmation).where(
                    Confirmation.version_id == version_id,
                    Confirmation.kind == "row_match",
                    Confirmation.undone_at.is_(None),
                )
            )
        ).scalars()
        matches = {
            row.item_id: RowMatch(row.id, row.recorded_by, row.recorded_at)
            for row in confirmations
        }
        return [
            (item, by_item.get(item.id, []), matches.get(item.id)) for item in items
        ]

    async def list_questions_with_latest(self, version_id):
        await self.version(version_id)
        questions = list(
            (
                await self.session.execute(
                    select(Question)
                    .where(Question.version_id == version_id)
                    .order_by(Question.id)
                )
            ).scalars()
        )
        judgements = list(
            (
                await self.session.execute(
                    select(QuestionJudgement)
                    .join(Question, Question.id == QuestionJudgement.question_id)
                    .where(Question.version_id == version_id)
                    .order_by(
                        QuestionJudgement.recorded_at.desc(),
                        QuestionJudgement.id.desc(),
                    )
                )
            ).scalars()
        )
        latest = {}
        for judgement in judgements:
            latest.setdefault(judgement.question_id, judgement)
        return [
            {"question": question, "latest": latest.get(question.id)}
            for question in questions
        ]

    async def list_item_evidence(self, version_id, item_id):
        await self.version(version_id)
        await self.item(version_id, item_id)
        return list(
            (
                await self.session.execute(
                    select(Evidence)
                    .where(
                        Evidence.version_id == version_id, Evidence.item_id == item_id
                    )
                    .order_by(Evidence.id)
                )
            ).scalars()
        )

    async def summary(self, version_id):
        version = await self.version(version_id)
        header = (
            await self.session.execute(
                select(CaseHeader).where(CaseHeader.version_id == version_id)
            )
        ).scalar_one_or_none()
        items = await self.list_items_with_edits(version_id)
        questions = await self.list_questions_with_latest(version_id)
        confirmations = list(
            (
                await self.session.execute(
                    select(Confirmation).where(
                        Confirmation.version_id == version_id,
                        Confirmation.undone_at.is_(None),
                    )
                )
            ).scalars()
        )
        return {
            "items": items,
            "questions": questions,
            "confirmations": confirmations,
            "version": version,
            "case_header": header,
        }

    async def list_versions(self, case_id):
        require(await self.session.get(Case, case_id) is not None)
        return list(
            (
                await self.session.execute(
                    select(Version)
                    .where(
                        Version.case_id == case_id, Version.finalized_at.is_not(None)
                    )
                    .order_by(Version.version_no.desc(), Version.id.desc())
                )
            ).scalars()
        )
