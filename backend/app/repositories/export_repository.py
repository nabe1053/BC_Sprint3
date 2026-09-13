"""Read consistent workbook materials and append export metadata."""
from contextlib import asynccontextmanager
from types import SimpleNamespace
from sqlalchemy import select, func
from app.domain.export_types import ExportSnapshot, ItemRow
from app.domain.record_types import apply_edits, unresolved_question_ids
from app.models import (
    Export,
    Version,
    Case,
    CaseHeader,
    Document,
    Item,
    ItemEnd,
    Evidence,
    RuleSet,
    AgentRun,
    ItemEdit,
    Confirmation,
    BounceComment,
)
from app.repositories.draft_repository import DraftRepository, require
from app.repositories.record_repository import RecordRepository


class ExportRepository:
    def __init__(self, session):
        self.session = session

    _transaction = DraftRepository._transaction
    _one = DraftRepository._one
    _all = DraftRepository._all

    @asynccontextmanager
    async def lock_version(self, version_id):
        async with self._transaction():
            version = await self._one(
                select(Version)
                .where(Version.id == version_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            require(version is not None)
            require(
                version.finalized_at is not None,
                "E_VERSION_NOT_FINALIZED",
                "未確定の版は出力できません",
            )
            yield version

    async def snapshot(self, version_id):
        # A reused session may retain edits cancelled by another transaction.
        # Refresh all snapshot materials after acquiring the version lock.
        for record in list(self.session.identity_map.values()):
            if (
                isinstance(record, (ItemEdit, Confirmation, BounceComment))
                and record.version_id == version_id
            ):
                self.session.expire(record)
        records_repo = RecordRepository(self.session)
        version = await records_repo.version(version_id)
        case = await self._one(select(Case).where(Case.id == version.case_id))
        header = await self._one(
            select(CaseHeader).where(CaseHeader.version_id == version_id)
        )
        documents = await self._all(
            select(Document)
            .where(Document.case_id == version.case_id)
            .order_by(Document.received_at, Document.id)
        )
        rule = await self._one(select(RuleSet).where(RuleSet.id == version.rule_set_id))
        elapsed_sec = await self._one(
            select(AgentRun.elapsed_sec).where(AgentRun.version_id == version_id)
        )
        item_materials = await records_repo.list_items_with_edits(version_id)
        ends = await self._all(
            select(ItemEnd)
            .join(Item, Item.id == ItemEnd.item_id)
            .where(Item.version_id == version_id)
            .order_by(ItemEnd.id)
        )
        ends_by_item = {}
        for end in ends:
            ends_by_item.setdefault(end.item_id, []).append(end)
        items = [
            ItemRow(
                apply_edits(item, edits).values,
                ends_by_item.get(item.id, []),
                match,
                sum(edit.undone_at is None for edit in edits),
            )
            for item, edits, match in item_materials
        ]
        questions = await records_repo.list_questions_with_latest(version_id)
        records = await records_repo.list_records(version_id)
        return ExportSnapshot(
            case=case,
            version=version,
            header=header,
            documents=documents,
            items=items,
            evidences=await self.list_evidence(version_id),
            questions=questions,
            records=records,
            elapsed_sec=elapsed_sec,
            rule_version=rule.rule_version,
            conversion_enabled=rule.conversion_enabled,
            unresolved_count=len(unresolved_question_ids(questions)),
            matched_count=sum(item.row_match is not None for item in items),
            coverage_confirmed=any(
                row.kind == "coverage" and row.undone_at is None
                for row in records["confirmations"]
            ),
        )

    async def list_evidence(self, version_id):
        require(
            await self._one(select(Version.id).where(Version.id == version_id))
            is not None
        )
        rows = (
            await self.session.execute(
                select(Evidence, Document.file_name)
                .join(Document, Document.id == Evidence.document_id)
                .outerjoin(Item, Item.id == Evidence.item_id)
                .where(Evidence.version_id == version_id)
                .order_by(Item.seq.asc().nullsfirst(), Evidence.id)
            )
        ).all()
        return [
            SimpleNamespace(
                **{
                    column.key: getattr(evidence, column.key)
                    for column in Evidence.__table__.columns
                },
                file_name=file_name,
            )
            for evidence, file_name in rows
        ]

    async def count_exports(self, version_id):
        return await self._one(
            select(func.count())
            .select_from(Export)
            .where(Export.version_id == version_id)
        )

    async def save_export(self, values):
        row = Export(**values)
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_exports(self, version_id):
        require(
            await self._one(select(Version.id).where(Version.id == version_id))
            is not None
        )
        return await self._all(
            select(Export)
            .where(Export.version_id == version_id)
            .order_by(Export.exported_at, Export.id)
        )
