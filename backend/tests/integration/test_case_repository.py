"""CaseRepository（Data Access層）の統合テスト。テスト用 DB（octg_test）を使う。

期待インタフェース:
    app.repositories.case_repository.CaseRepository(session)
        async def create(case: Case) -> Case
        async def get_by_id(case_id: int) -> Case | None
        async def get_by_code(case_code: str) -> Case | None
        async def list() -> list[Case]

中-D: `create()` は UNIQUE 違反（IntegrityError）を素通しせず、
`DuplicateCaseCodeError`（E_DUPLICATE_CASE_CODE）に翻訳して送出する
（Service 層が SQLAlchemy を知らずに済むようにするため）。
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.cases import Case
from app.repositories.case_repository import CaseRepository
from app.services.exceptions import DuplicateCaseCodeError


async def test_create_and_get_by_id(db_session) -> None:
    """作成した案件を id で取得できる。"""
    repo = CaseRepository(db_session)

    created = await repo.create(
        Case(case_code="CASE-001", customer_name="双葉物産", title="羽島沖ガス田開発")
    )

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.case_code == "CASE-001"


async def test_get_by_code(db_session) -> None:
    """case_code で案件を取得できる。"""
    repo = CaseRepository(db_session)
    await repo.create(Case(case_code="CASE-002", customer_name=None, title=None))

    fetched = await repo.get_by_code("CASE-002")
    assert fetched is not None
    assert fetched.case_code == "CASE-002"


async def test_get_by_code_returns_none_when_not_found(db_session) -> None:
    """存在しない case_code は None を返す。"""
    repo = CaseRepository(db_session)

    assert await repo.get_by_code("NO-SUCH-CODE") is None


async def test_list_returns_all_cases(db_session) -> None:
    """作成した案件がすべて一覧に含まれる。"""
    repo = CaseRepository(db_session)
    await repo.create(Case(case_code="CASE-010", customer_name=None, title=None))
    await repo.create(Case(case_code="CASE-011", customer_name=None, title=None))

    cases = await repo.list()

    codes = {c.case_code for c in cases}
    assert {"CASE-010", "CASE-011"}.issubset(codes)


async def test_case_code_is_unique(db_session) -> None:
    """case_code は UNIQUE 制約があり、重複作成は DuplicateCaseCodeError になる
    （中-D: 生の IntegrityError を Service 層に漏らさない）。"""
    repo = CaseRepository(db_session)
    await repo.create(Case(case_code="CASE-DUP", customer_name=None, title=None))

    with pytest.raises(DuplicateCaseCodeError) as exc_info:
        await repo.create(Case(case_code="CASE-DUP", customer_name=None, title=None))

    assert exc_info.value.code == "E_DUPLICATE_CASE_CODE"
    # 中-8: details のキーは camelCase（05-api-ipo.md 0.4）。
    assert exc_info.value.details.get("caseCode") == "CASE-DUP"


async def test_non_unique_integrity_error_is_not_translated(db_session) -> None:
    """軽微-3: NOT NULL 違反等、unique 違反でない IntegrityError は
    DuplicateCaseCodeError に翻訳せず、そのまま再送出する
    （SQLSTATE 23505 以外を無条件で翻訳しない）。"""
    repo = CaseRepository(db_session)

    with pytest.raises(IntegrityError) as exc_info:
        await repo.create(Case(case_code=None, customer_name=None, title=None))

    assert not isinstance(exc_info.value, DuplicateCaseCodeError)


async def test_version_summaries_returns_questions_with_latest_judgement_and_state_event(
    db_session,
) -> None:
    """F-15: 案件一覧の材料。版ごとに確認事項（最新の判断つき）と最新の状態イベントを返す。"""
    from datetime import UTC, datetime, timedelta

    from app.models import Question, QuestionJudgement
    from tests.fixtures.record_data import seed_record_version

    seed = await seed_record_version(db_session, state="staff_checked")
    other = await seed_record_version(db_session)
    q1 = Question(
        version_id=seed.version.id,
        item_id=seed.item.id,
        question_code="Q1",
        target_field="grade",
        reason="材質",
    )
    q2 = Question(
        version_id=seed.version.id,
        item_id=None,
        question_code="Q2",
        target_field="due",
        reason="納期",
    )
    db_session.add_all([q1, q2])
    await db_session.flush()
    at = datetime.now(UTC)
    db_session.add_all(
        [
            QuestionJudgement(
                question_id=q1.id,
                status="judged",
                resolution="unresolved",
                recorded_by="担当",
                recorded_at=at,
            ),
            QuestionJudgement(
                question_id=q1.id,
                status="judged",
                resolution="resolved",
                recorded_by="担当",
                recorded_at=at + timedelta(minutes=1),
            ),
        ]
    )
    await db_session.commit()

    summaries = await CaseRepository(db_session).version_summaries(
        [seed.version.id, other.version.id]
    )

    mine = summaries[seed.version.id]
    assert [row["question"].question_code for row in mine["questions"]] == ["Q1", "Q2"]
    assert mine["questions"][0]["latest"].resolution == "resolved"
    assert mine["questions"][1]["latest"] is None
    assert mine["latest_state_event"].to_state == "staff_checked"
    assert mine["latest_state_event"].recorded_by == "fixture"
    assert summaries[other.version.id] == {"questions": [], "latest_state_event": None}
    assert await CaseRepository(db_session).version_summaries([]) == {}
