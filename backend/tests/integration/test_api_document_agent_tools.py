"""API #8・#9 エージェント専用（05-api-ipo.md 1章 A・5章の要約・0.3 区分 AGENT）。

対象パス:
    #8 GET  /api/v1/agent/cases/{caseId}/search
    #9 POST /api/v1/agent/documents/{documentId}/issues

これらは AGENT 区分であり、/ui/* には存在しないこと自体も E 節
（tests/integration/test_api_path_separation_live.py）で検査する。ここでは
入出力契約（エラーの意味論）を検証する。

期待するレスポンス契約（仮決め）:
    #8 200: {"results": [{"documentId":..., "locator":..., "excerpt":...}, ...]}
       400: E_QUERY_REQUIRED（検索語が空）
    #9 201: {"issueId": <int>}
       400: E_DETAIL_REQUIRED（detail が空）
       404: E_NOT_FOUND（資料が存在しない）
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.cases import Case
from app.models.documents import Document, DocumentPage
from app.repositories.case_repository import CaseRepository
from app.repositories.document_repository import DocumentRepository

AGENT_CASES_PATH = "/api/v1/agent/cases"
AGENT_DOCUMENTS_PATH = "/api/v1/agent/documents"


async def _make_case(db_session, case_code: str = "CASE-AGENT-001") -> Case:
    repo = CaseRepository(db_session)
    return await repo.create(Case(case_code=case_code, customer_name=None, title=None))


def _new_document(case_id: int, **overrides) -> Document:
    defaults = dict(
        case_id=case_id,
        file_name="spec.pdf",
        storage_path="/tmp/does-not-matter.pdf",
        kind="pdf",
        page_count=1,
        read_status="success",
        content_hash="hash",
        received_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Document(**defaults)


# ---------------------------------------------------------------------------
# #8 検索
# ---------------------------------------------------------------------------


async def test_search_finds_matching_locator_and_excerpt(client, db_session) -> None:
    """正常系: 案件内の資料本文から検索語に一致する箇所（資料ID・位置・抜粋）を返す。"""
    case = await _make_case(db_session)
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id),
        pages=[
            DocumentPage(
                locator="p.1",
                seq=1,
                text="納地は本文3.2項による。詳細は別紙。",
                cells=None,
            )
        ],
    )

    response = client.get(
        f"{AGENT_CASES_PATH}/{case.id}/search", params={"q": "本文3.2項", "limit": 5}
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert any(
        r["documentId"] == document.id and r["locator"] == "p.1" for r in results
    )


async def test_search_with_empty_query_returns_400(client, db_session) -> None:
    """異常系: 検索語が空は 400 E_QUERY_REQUIRED。"""
    case = await _make_case(db_session)

    response = client.get(f"{AGENT_CASES_PATH}/{case.id}/search", params={"q": ""})

    assert response.status_code == 400
    assert response.json()["code"] == "E_QUERY_REQUIRED"


def test_search_missing_case_returns_404(client) -> None:
    """異常系: 存在しない案件IDは 404。"""
    response = client.get(f"{AGENT_CASES_PATH}/999999/search", params={"q": "x"})

    assert response.status_code == 404
    assert response.json()["code"] == "E_NOT_FOUND"


# ---------------------------------------------------------------------------
# #9 読取不能・未走査範囲の記録
# ---------------------------------------------------------------------------


async def test_report_issue_creates_document_issue_row(client, db_session) -> None:
    """正常系: 読取不能範囲を記録すると document_issues に1行残る。"""
    case = await _make_case(db_session, case_code="CASE-AGENT-002")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(_new_document(case.id))

    response = client.post(
        f"{AGENT_DOCUMENTS_PATH}/{document.id}/issues",
        json={
            "locator": "p.3",
            "issueType": "unreadable_page",
            "detail": "画像のみで文字が無い",
        },
    )

    assert response.status_code == 201
    assert isinstance(response.json()["issueId"], int)


async def test_report_issue_with_empty_detail_returns_400(client, db_session) -> None:
    """異常系: detail が空は 400 E_DETAIL_REQUIRED（表示できない記録を残さない・N03）。"""
    case = await _make_case(db_session, case_code="CASE-AGENT-003")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(_new_document(case.id))

    response = client.post(
        f"{AGENT_DOCUMENTS_PATH}/{document.id}/issues",
        json={"locator": "p.3", "issueType": "unreadable_page", "detail": ""},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "E_DETAIL_REQUIRED"


async def test_report_issue_with_invalid_issue_type_returns_422(
    client, db_session
) -> None:
    """異常系: issueType が 04-db.md の CHECK 制約の語彙に無い値は 422
    （reviewer 指摘 重-3: DB の CHECK 違反（500・IntegrityError）に到達させない）。"""
    case = await _make_case(db_session, case_code="CASE-AGENT-004")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(_new_document(case.id))

    response = client.post(
        f"{AGENT_DOCUMENTS_PATH}/{document.id}/issues",
        json={
            "locator": "p.3",
            "issueType": "not_a_real_issue_type",
            "detail": "不正な issueType",
        },
    )

    assert response.status_code == 422


def test_report_issue_missing_document_returns_404(client) -> None:
    """異常系: 存在しない資料IDへの記録は 404。"""
    response = client.post(
        f"{AGENT_DOCUMENTS_PATH}/999999/issues",
        json={"locator": None, "issueType": "not_scanned", "detail": "未走査"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "E_NOT_FOUND"
