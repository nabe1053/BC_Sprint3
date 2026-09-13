"""CaseService（Business Logic層）の単体テスト。Repository は mock する。

期待インタフェース:
    app.services.case_service.CaseService(case_repository)
        async def create_case(case_code: str, customer_name: str | None,
                               title: str | None) -> Case
    Repository には以下の非同期メソッドがある想定（CaseRepositoryProtocol）:
        get_by_code(case_code: str) -> Case | None
        create(case: Case) -> Case

    app.services.exceptions:
        DuplicateCaseCodeError  # code == "E_DUPLICATE_CASE_CODE"（05-api-ipo.md 6章）

中-D: UNIQUE 違反（IntegrityError）の `DuplicateCaseCodeError` への翻訳は
Repository 側の責務（`CaseRepository.create()`）に移した。Service は
SQLAlchemy を import せず、Repository が翻訳済みの `DuplicateCaseCodeError` を
そのまま伝播するだけでよい。
"""

from unittest.mock import AsyncMock

import pytest

from app.services.case_service import CaseService
from app.services.exceptions import DuplicateCaseCodeError


def _make_service(existing_case=None) -> tuple[CaseService, AsyncMock]:
    repo = AsyncMock()
    repo.get_by_code.return_value = existing_case
    repo.create.side_effect = lambda case: case
    return CaseService(repo), repo


async def test_create_case_succeeds_with_valid_code() -> None:
    """正常系: case_code があれば案件を作成し repository.create を呼ぶ。"""
    service, repo = _make_service(existing_case=None)

    await service.create_case(
        case_code="CASE-001", customer_name="双葉物産", title="羽島沖ガス田開発"
    )

    repo.create.assert_awaited_once()


@pytest.mark.parametrize("blank_code", ["", "   "])
async def test_create_case_rejects_empty_case_code(blank_code: str) -> None:
    """異常系: case_code が空文字（空白のみ含む）なら拒否し、repository を呼ばない。"""
    service, repo = _make_service()

    with pytest.raises(ValueError):
        await service.create_case(case_code=blank_code, customer_name=None, title=None)

    repo.create.assert_not_awaited()


async def test_create_case_rejects_duplicate_case_code() -> None:
    """異常系: 既に存在する case_code は E_DUPLICATE_CASE_CODE のドメイン例外になる。"""
    existing = object()  # 既存 Case の代替（Repository がモックのため実体は不要）
    service, repo = _make_service(existing_case=existing)

    with pytest.raises(DuplicateCaseCodeError) as exc_info:
        await service.create_case(case_code="CASE-001", customer_name=None, title=None)

    assert exc_info.value.code == "E_DUPLICATE_CASE_CODE"
    repo.create.assert_not_awaited()


async def test_create_case_propagates_duplicate_from_repository_on_race() -> None:
    """異常系: get_by_code をすり抜けた UNIQUE 違反（並行投入の競合）は
    Repository 側で E_DUPLICATE_CASE_CODE に翻訳済みのものがそのまま伝播する
    （中-D: 翻訳の責務は Repository に移した。Service は SQLAlchemy を知らない）。"""
    service, repo = _make_service(existing_case=None)
    repo.create.side_effect = DuplicateCaseCodeError(
        "case_code 'CASE-001' は既に使用されています",
        details={"caseCode": "CASE-001"},
    )

    with pytest.raises(DuplicateCaseCodeError) as exc_info:
        await service.create_case(case_code="CASE-001", customer_name=None, title=None)

    assert exc_info.value.code == "E_DUPLICATE_CASE_CODE"
    # 中-8: details のキーは camelCase（05-api-ipo.md 0.4）。
    assert exc_info.value.details.get("caseCode") == "CASE-001"


@pytest.mark.parametrize(
    "state,expected",
    [
        (None, "intake"),
        ("draft", "draft_review"),
        ("staff_checked", "staff_checked"),
        ("review_checked", "review_checked"),
    ],
)
async def test_case_progress_uses_latest_finalized_version(state, expected):
    from types import SimpleNamespace as N

    case = N(id=3)
    repository = N(
        list=AsyncMock(return_value=[case]),
        latest_versions=AsyncMock(
            return_value={}
            if state is None
            else {3: N(id=7, current_state=state, latest_sendoff=None)}
        ),
    )
    result = await CaseService(repository).list_cases()
    assert result == [(case, expected, None if state is None else 7, None)]
