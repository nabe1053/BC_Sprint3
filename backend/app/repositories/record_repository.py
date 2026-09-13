"""Finalized-version human records, serialized with the version row lock."""
from contextlib import asynccontextmanager

from sqlalchemy import select, update

from app.domain.draft_errors import DraftError
from app.domain.record_types import CarryOver, unresolved_question_ids
from app.models import (
    AgentRun,
    VersionStateEvent,
    Bounce,
    BounceComment,
    SendoffDecision,
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
                version = await self.version(version_id, lock=True)
                yield version
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

    async def item_rows(self, version_id):
        rows = (
            await self.session.execute(
                select(Item.id, Item.row_code).where(Item.version_id == version_id)
            )
        ).all()
        return dict(rows)

    async def matched_item_ids(self, version_id):
        return set(
            (
                await self.session.execute(
                    select(Confirmation.item_id).where(
                        Confirmation.version_id == version_id,
                        Confirmation.kind == "row_match",
                        Confirmation.undone_at.is_(None),
                    )
                )
            ).scalars()
        )

    async def coverage_confirmed(self, version_id):
        return await self.active_confirmation(version_id, "coverage", None) is not None

    async def save_state_event(
        self,
        version,
        *,
        from_state,
        to_state,
        recorded_by,
        recorded_at,
        unresolved_count,
    ):
        require(
            version.current_state == from_state,
            "E_STATE_ORDER",
            "状態が変更されています",
        )
        event = VersionStateEvent(
            version_id=version.id,
            from_state=from_state,
            to_state=to_state,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            unresolved_count=unresolved_count,
        )
        self.session.add(event)
        version.current_state = to_state
        await self.session.flush()
        return event

    async def save_bounce_comment(self, version_id, data):
        row = BounceComment(version_id=version_id, **data)
        self.session.add(row)
        await self.session.flush()
        return row

    async def unlinked_bounce_comments(self, version_id):
        return list(
            (
                await self.session.execute(
                    select(BounceComment)
                    .where(
                        BounceComment.version_id == version_id,
                        BounceComment.bounce_id.is_(None),
                    )
                    .order_by(BounceComment.recorded_at, BounceComment.id)
                )
            ).scalars()
        )

    async def save_bounce(self, version_id, data, comments):
        require(all(comment.version_id == version_id for comment in comments))
        row = Bounce(version_id=version_id, **data)
        self.session.add(row)
        await self.session.flush()
        await self.session.execute(
            update(BounceComment)
            .where(
                BounceComment.version_id == version_id,
                BounceComment.id.in_([comment.id for comment in comments]),
                BounceComment.bounce_id.is_(None),
            )
            .values(bounce_id=row.id)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.flush()
        return row

    async def save_sendoff(self, version_id, data):
        row = SendoffDecision(version_id=version_id, **data)
        self.session.add(row)
        await self.session.flush()
        return row

    async def _record_materials(self, version_ids):
        """One query per record kind, independent of the number of versions."""
        grouped = {version_id: {} for version_id in version_ids}
        for key, model in (
            ("edits", ItemEdit),
            ("confirmations", Confirmation),
            ("state_events", VersionStateEvent),
            ("bounces", Bounce),
            ("comments", BounceComment),
            ("sendoff_decisions", SendoffDecision),
        ):
            rows = (
                await self.session.execute(
                    select(model)
                    .where(model.version_id.in_(version_ids))
                    .order_by(model.recorded_at, model.id)
                )
            ).scalars()
            for version_id in grouped:
                grouped[version_id][key] = []
            for row in rows:
                grouped[row.version_id][key].append(row)
        questions = list(
            (
                await self.session.execute(
                    select(Question)
                    .where(Question.version_id.in_(version_ids))
                    .order_by(Question.id)
                )
            ).scalars()
        )
        by_question = {question.id: question for question in questions}
        judgements = list(
            (
                await self.session.execute(
                    select(QuestionJudgement)
                    .where(QuestionJudgement.question_id.in_(by_question))
                    .order_by(QuestionJudgement.recorded_at, QuestionJudgement.id)
                )
            ).scalars()
        )
        items = list(
            (
                await self.session.execute(
                    select(Item)
                    .where(Item.version_id.in_(version_ids))
                    .order_by(Item.seq, Item.id)
                )
            ).scalars()
        )
        for version_id in grouped:
            grouped[version_id].update(questions=[], judgements=[], items=[])
        for question in questions:
            grouped[question.version_id]["questions"].append(question)
        for judgement in judgements:
            grouped[by_question[judgement.question_id].version_id]["judgements"].append(
                judgement
            )
        for item in items:
            grouped[item.version_id]["items"].append(item)
        return grouped

    async def list_records(self, version_id):
        await self.version(version_id)
        data = (await self._record_materials([version_id]))[version_id]
        comments = {}
        for comment in data["comments"]:
            comments.setdefault(comment.bounce_id, []).append(comment)
        return {
            **{
                key: data[key]
                for key in (
                    "edits",
                    "confirmations",
                    "judgements",
                    "state_events",
                    "sendoff_decisions",
                )
            },
            "bounces": [
                {"bounce": bounce, "comments": comments.get(bounce.id, [])}
                for bounce in data["bounces"]
            ],
            "unlinked_comments": comments.get(None, []),
        }

    async def list_versions_with_records(self, case_id):
        versions = await self.list_versions(case_id)
        if not versions:
            return []
        version_ids = [version.id for version in versions]
        materials = await self._record_materials(version_ids)
        # N06 の生成所要。版数に依らない 1 回の SELECT でまとめて引く（1実行1版）。
        elapsed = dict(
            (
                await self.session.execute(
                    select(AgentRun.version_id, AgentRun.elapsed_sec)
                    .where(AgentRun.version_id.in_(version_ids))
                    # 1実行1版だが一意制約は無い。重複時は最新（id 最大）を採る。
                    .order_by(AgentRun.id)
                )
            ).all()
        )
        result = []
        for version in versions:
            data = materials[version.id]
            confirmations = [
                row for row in data["confirmations"] if row.undone_at is None
            ]
            latest = {row.question_id: row for row in data["judgements"]}
            questions = [
                {"question": question, "latest": latest.get(question.id)}
                for question in data["questions"]
            ]
            result.append(
                {
                    "version": version,
                    "carry_over": CarryOver(
                        edit_count=sum(row.undone_at is None for row in data["edits"]),
                        row_match_confirmed=sum(
                            row.kind == "row_match" for row in confirmations
                        ),
                        row_match_total=len(data["items"]),
                        coverage_recorded=any(
                            row.kind == "coverage" for row in confirmations
                        ),
                        judgement_count=len(latest),
                    ),
                    "unresolved_count": len(unresolved_question_ids(questions)),
                    "elapsed_sec": elapsed.get(version.id),
                    "latest_state_event": data["state_events"][-1]
                    if data["state_events"]
                    else None,
                    "latest_review_checked_at": next(
                        (
                            row.recorded_at
                            for row in reversed(data["state_events"])
                            if row.to_state == "review_checked"
                        ),
                        None,
                    ),
                    "latest_bounce": data["bounces"][-1] if data["bounces"] else None,
                    "latest_sendoff_decision": data["sendoff_decisions"][-1]
                    if data["sendoff_decisions"]
                    else None,
                }
            )
        return result
