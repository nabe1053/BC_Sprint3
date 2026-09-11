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
    assert exc_info.value.details.get("case_code") == "CASE-DUP"


async def test_non_unique_integrity_error_is_not_translated(db_session) -> None:
    """軽微-3: NOT NULL 違反等、unique 違反でない IntegrityError は
    DuplicateCaseCodeError に翻訳せず、そのまま再送出する
    （SQLSTATE 23505 以外を無条件で翻訳しない）。"""
    repo = CaseRepository(db_session)

    with pytest.raises(IntegrityError) as exc_info:
        await repo.create(Case(case_code=None, customer_name=None, title=None))

    assert not isinstance(exc_info.value, DuplicateCaseCodeError)
