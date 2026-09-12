"""Artifact persistence; every write locks the version and commits atomically."""
from contextlib import asynccontextmanager

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.domain.draft_errors import DraftError
from app.domain.draft_snapshot import DraftSnapshot
from app.models.agent_runs import AgentRun, AgentRunStep
from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.models.drafts import (
    CaseHeader,
    Evidence,
    InventoryEntry,
    InventoryLink,
    Item,
    ItemEnd,
    Question,
)
from app.models.rule_sets import RuleSet
from app.models.versions import Version


def require(
    condition, code="E_NOT_FOUND", message="対象が存在しないか、案件・版が一致しません"
):
    if not condition:
        raise DraftError(code, message)


class DraftRepository:
    def __init__(self, session):
        self.session = session

    @asynccontextmanager
    async def _transaction(self):
        try:
            yield
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if getattr(exc.orig, "sqlstate", None) not in {
                "23505",
                "23503",
                "23514",
                "23502",
            }:
                raise
            raise DraftError(
                "E_VALIDATION_FAILED", "成果物の保存制約に違反しています"
            ) from exc
        except BaseException:
            await self.session.rollback()
            raise

    async def _one(self, statement):
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def _all(self, statement):
        return list((await self.session.execute(statement)).scalars().all())

    @asynccontextmanager
    async def edit(self, version_id):
        """Serialize writes/finalization using the version row, then refresh state.

        SQLite isolation tests check refresh/rejection only: its dialect omits
        FOR UPDATE. PostgreSQL two-session lock serialization remains unverified
        until the user authorizes DB validation (RV-016 P2-3).
        """
        async with self._transaction():
            version = await self._one(
                select(Version)
                .where(Version.id == version_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            require(version is not None)
            require(
                version.finalized_at is None,
                "E_VERSION_FINALIZED",
                "確定済みの版は変更できません",
            )
            run = await self._one(
                select(AgentRun)
                .where(AgentRun.version_id == version_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            require(
                run is None or run.outcome == "running",
                "E_RUN_NOT_ACTIVE",
                "終了した実行の版には書き込めません",
            )
            yield version

    async def create_version(self, case_id, rule_set_id, prev_version_id=None):
        async with self._transaction():
            case = await self._one(
                select(Case).where(Case.id == case_id).with_for_update()
            )
            require(case is not None)
            rules = await self.session.get(RuleSet, rule_set_id)
            require(rules is not None)
            if prev_version_id is not None:
                previous = await self.session.get(Version, prev_version_id)
                require(previous is not None and previous.case_id == case_id)
            number = (
                await self.session.execute(
                    select(func.max(Version.version_no)).where(
                        Version.case_id == case_id
                    )
                )
            ).scalar_one()
            version = Version(
                case_id=case_id,
                version_no=(number or 0) + 1,
                rule_set_id=rule_set_id,
                prev_version_id=prev_version_id,
                current_state="draft",
                is_complete=False,
            )
            self.session.add(version)
            await self.session.flush()
        return version

    async def _item_in_version(self, item_id, version_id, code="E_NOT_FOUND"):
        if item_id is not None:
            item = await self.session.get(Item, item_id)
            require(item is not None and item.version_id == version_id, code)

    async def _document_in_case(self, document_id, case_id):
        doc = await self.session.get(Document, document_id)
        require(doc is not None and doc.case_id == case_id)

    async def save_header(self, version_id, data):
        async with self.edit(version_id):
            existing = await self._one(
                select(CaseHeader).where(CaseHeader.version_id == version_id)
            )
            require(
                existing is None,
                "E_VALIDATION_FAILED",
                "案件情報は既に登録されています",
            )
            header = CaseHeader(version_id=version_id, **data.model_dump())
            self.session.add(header)
            await self.session.flush()
        return header

    async def add_items(self, version_id, rows):
        async with self.edit(version_id):
            codes = [row.row_code for row in rows]
            require(
                len(set(codes)) == len(codes),
                "E_VALIDATION_FAILED",
                "行IDが重複しています",
            )
            existing = await self._all(
                select(Item).where(
                    Item.version_id == version_id, Item.row_code.in_(codes)
                )
            )
            require(not existing, "E_VALIDATION_FAILED", "行IDは既に登録されています")
            saved = []
            for row in rows:
                entity = Item(version_id=version_id, **row.model_dump(exclude={"ends"}))
                self.session.add(entity)
                await self.session.flush()
                self.session.add_all(
                    [ItemEnd(item_id=entity.id, **end.model_dump()) for end in row.ends]
                )
                saved.append(entity)
            await self.session.flush()
        return saved

    async def add_evidences(self, version_id, rows):
        async with self.edit(version_id) as version:
            saved = []
            existing = await self._all(
                select(Evidence).where(Evidence.version_id == version_id)
            )
            keys = {(row.item_id, row.field) for row in existing}
            for row in rows:
                await self._item_in_version(row.item_id, version_id)
                await self._document_in_case(row.document_id, version.case_id)
                key = (row.item_id, row.field)
                require(
                    key not in keys,
                    "E_EVIDENCE_DUPLICATE",
                    "同じ項目の根拠は既に登録されています",
                )
                keys.add(key)
                saved.append(Evidence(version_id=version_id, **row.model_dump()))
            self.session.add_all(saved)
            await self.session.flush()
        return saved

    async def add_questions(self, version_id, rows):
        async with self.edit(version_id):
            saved = []
            existing = await self._all(
                select(Question).where(Question.version_id == version_id)
            )
            codes = {row.question_code for row in existing}
            for row in rows:
                await self._item_in_version(row.item_id, version_id, "E_TARGET_INVALID")
                require(
                    row.question_code not in codes,
                    "E_VALIDATION_FAILED",
                    "確認IDが重複しています",
                )
                codes.add(row.question_code)
                saved.append(Question(version_id=version_id, **row.model_dump()))
            self.session.add_all(saved)
            await self.session.flush()
        return saved

    async def add_inventory(self, version_id, rows):
        async with self.edit(version_id) as version:
            saved = []
            for row in rows:
                await self._document_in_case(row.document_id, version.case_id)
                for item_id in row.item_ids:
                    await self._item_in_version(item_id, version_id)
                entry = InventoryEntry(
                    version_id=version_id, **row.model_dump(exclude={"item_ids"})
                )
                self.session.add(entry)
                await self.session.flush()
                self.session.add_all(
                    [InventoryLink(entry_id=entry.id, item_id=i) for i in row.item_ids]
                )
                saved.append(entry)
            await self.session.flush()
        return saved

    async def snapshot(self, version_id):
        version = await self.session.get(Version, version_id)
        require(version is not None)
        snapshot = DraftSnapshot()
        snapshot.items = await self._all(
            select(Item)
            .where(Item.version_id == version_id)
            .order_by(Item.seq, Item.id)
        )
        snapshot.ends = await self._all(
            select(ItemEnd)
            .join(Item, ItemEnd.item_id == Item.id)
            .where(Item.version_id == version_id)
        )
        snapshot.header = await self._one(
            select(CaseHeader).where(CaseHeader.version_id == version_id)
        )
        snapshot.evidences = await self._all(
            select(Evidence).where(Evidence.version_id == version_id)
        )
        snapshot.questions = await self._all(
            select(Question).where(Question.version_id == version_id)
        )
        snapshot.inventory = await self._all(
            select(InventoryEntry).where(InventoryEntry.version_id == version_id)
        )
        document_ids = select(Document.id).where(Document.case_id == version.case_id)
        pages = await self._all(
            select(DocumentPage).where(DocumentPage.document_id.in_(document_ids))
        )
        parts = await self._all(
            select(EmailPart).where(EmailPart.document_id.in_(document_ids))
        )
        snapshot.readable_ranges = {
            (page.document_id, page.locator)
            for page in pages
            if (page.text and page.text.strip()) or page.cells
        }
        snapshot.readable_ranges.update(
            (part.document_id, f"email:{part.part_role}:{part.seq}")
            for part in parts
            if (part.body and part.body.strip())
            or (part.part_role == "attachment" and part.attachment_name)
        )
        run = await self._one(select(AgentRun).where(AgentRun.version_id == version_id))
        snapshot.run_id = run.id if run else None
        if run:
            steps = await self._all(
                select(AgentRunStep).where(
                    AgentRunStep.agent_run_id == run.id,
                    AgentRunStep.result_status == "ok",
                    AgentRunStep.tool_name.in_(["read_document", "read_email"]),
                )
            )
            for step in steps:
                if step.tool_name == "read_email":
                    if step.locator == "email:*":
                        snapshot.scanned_ranges.update(
                            (doc, loc)
                            for doc, loc in snapshot.readable_ranges
                            if doc == step.document_id and loc.startswith("email:")
                        )
                    elif step.locator and step.locator.startswith("email:"):
                        snapshot.scanned_ranges.add((step.document_id, step.locator))
                elif step.locator and not step.locator.startswith("email:"):
                    snapshot.scanned_ranges.add((step.document_id, step.locator))
        issues = await self._all(
            select(DocumentIssue).where(DocumentIssue.document_id.in_(document_ids))
        )
        relevant = [
            issue
            for issue in issues
            if issue.agent_run_id is None
            or (run is not None and issue.agent_run_id == run.id)
        ]
        snapshot.has_issues = bool(relevant)
        for issue in relevant:
            # Missing ancillary metadata does not prove a page was read or explicitly left unread.
            if (
                issue.issue_type
                in {"unreadable_page", "encrypted", "unsupported", "not_scanned"}
                and issue.locator
            ):
                snapshot.excused_ranges.add((issue.document_id, issue.locator))
        return snapshot

    async def complete(self, version, validation, is_complete, finalized_at):
        """Called by DraftService within edit(); the version lock is held through validation."""
        run = await self._one(select(AgentRun).where(AgentRun.version_id == version.id))
        require(
            run is not None, "E_VALIDATION_FAILED", "版に対応する実行記録がありません"
        )
        require(
            run.case_id == version.case_id and run.rule_set_id == version.rule_set_id,
            "E_VALIDATION_FAILED",
            "実行と版の案件・規則版が一致しません",
        )
        run.validation_result = validation
        version.finalized_at = finalized_at
        version.current_state = "draft"
        version.is_complete = is_complete
        await self.session.flush()
        return version
