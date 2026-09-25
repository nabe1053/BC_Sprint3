"""CaseRepository（Data Access層）。04-db.md 3.1 A層 `cases`。

中-D: `IntegrityError`（UNIQUE 違反）はここで `DuplicateCaseCodeError` に翻訳する。
Data Access 層は SQLAlchemy を扱ってよいが、Service 層に生の ORM 例外を
漏らさない（clean-architecture.md: 内側の詳細を外側に押し付けない）。

軽微-3: 翻訳対象は SQLSTATE 23505（unique_violation）に限る（無条件翻訳をしない）。
それ以外の IntegrityError（NOT NULL 違反等）は Data Access の詳細のままでは
なく、そのまま再送出する（Service 層に「本当は unique 違反ではないのに
DuplicateCaseCodeError になる」誤情報を渡さないため）。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cases import Case
from app.models.versions import Version
from app.models.approvals import SendoffDecision, VersionStateEvent
from app.models.drafts import Question
from app.models.records import QuestionJudgement
from app.services.exceptions import DuplicateCaseCodeError

_UNIQUE_VIOLATION_SQLSTATE = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    """psycopg3 の SQLSTATE（`orig.sqlstate`）で unique_violation かを判定する。

    制約名が取れる場合は case_code の UNIQUE 制約由来かも合わせて確認する
    （軽微-3: SQLSTATE または制約名で絞る。ORM 由来の文字列一致に頼らない）。
    """
    sqlstate = getattr(exc.orig, "sqlstate", None)
    if sqlstate != _UNIQUE_VIOLATION_SQLSTATE:
        return False
    diag = getattr(exc.orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None) if diag else None
    if constraint_name is not None:
        return "case_code" in constraint_name
    return True


class CaseRepository:
    """`cases` テーブルへの CRUD。ORM 操作をこの層に閉じ込める。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, case: Case) -> Case:
        self.session.add(case)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            if not _is_unique_violation(exc):
                raise
            raise DuplicateCaseCodeError(
                f"case_code '{case.case_code}' は既に使用されています",
                details={"caseCode": case.case_code},
            ) from exc
        await self.session.refresh(case)
        return case

    async def get_by_id(self, case_id: int) -> Case | None:
        return await self.session.get(Case, case_id)

    async def get_by_code(self, case_code: str) -> Case | None:
        stmt = select(Case).where(Case.case_code == case_code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self) -> list[Case]:
        stmt = select(Case).order_by(Case.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_versions(self, case_ids):
        if not case_ids:
            return {}
        latest_sendoff = (
            select(SendoffDecision.decision)
            .where(SendoffDecision.version_id == Version.id)
            .order_by(SendoffDecision.recorded_at.desc(), SendoffDecision.id.desc())
            .limit(1)
            .correlate(Version)
            .scalar_subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    Version.id,
                    Version.case_id,
                    Version.current_state,
                    latest_sendoff.label("latest_sendoff"),
                )
                .where(Version.case_id.in_(case_ids), Version.finalized_at.is_not(None))
                .distinct(Version.case_id)
                .order_by(Version.case_id, Version.version_no.desc())
            )
        ).all()
        return {row.case_id: row for row in rows}

    async def version_summaries(self, version_ids: list[int]) -> dict[int, dict]:
        """案件一覧（#1）の材料: 版ごとの確認事項（最新の判断つき）と最新の状態イベント（F-15）。

        版数に依らず 3 回の SELECT で引く。未解決の判定は Service（domain）で行う。
        """
        if not version_ids:
            return {}
        grouped = {
            version_id: {"questions": [], "latest_state_event": None}
            for version_id in version_ids
        }
        questions = list(
            (
                await self.session.execute(
                    select(Question)
                    .where(Question.version_id.in_(version_ids))
                    .order_by(Question.id)
                )
            ).scalars()
        )
        # 確認事項が 0 件でも SELECT 回数を変えない（案件・版の数に依らない回数を保つ）。
        latest = {}
        for judgement in (
            await self.session.execute(
                select(QuestionJudgement)
                .where(QuestionJudgement.question_id.in_([q.id for q in questions]))
                .order_by(QuestionJudgement.recorded_at, QuestionJudgement.id)
            )
        ).scalars():
            latest[judgement.question_id] = judgement
        for question in questions:
            grouped[question.version_id]["questions"].append(
                {"question": question, "latest": latest.get(question.id)}
            )
        for event in (
            await self.session.execute(
                select(VersionStateEvent)
                .where(VersionStateEvent.version_id.in_(version_ids))
                .order_by(VersionStateEvent.recorded_at, VersionStateEvent.id)
            )
        ).scalars():
            grouped[event.version_id]["latest_state_event"] = event
        return grouped
