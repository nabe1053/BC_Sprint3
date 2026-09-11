"""DocumentRepository（Data Access層）の統合テスト。テスト用 DB（octg_test）を使う。

期待インタフェース:
    app.repositories.document_repository.DocumentRepository(session)
        async def create_with_details(
            document: Document,
            pages: list[DocumentPage] | None = None,
            email_parts: list[EmailPart] | None = None,
            issues: list[DocumentIssue] | None = None,
        ) -> Document
        async def list_by_case(case_id: int) -> list[Document]
        async def count_by_case(case_id: int) -> int
        async def get_page_by_locator(document_id: int, locator: str) -> DocumentPage | None
        async def add_issue(issue: DocumentIssue) -> DocumentIssue
"""

from datetime import UTC, datetime

from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.repositories.case_repository import CaseRepository
from app.repositories.document_repository import DocumentRepository


async def _make_case(db_session) -> Case:
    case_repo = CaseRepository(db_session)
    return await case_repo.create(
        Case(case_code="CASE-DOC-001", customer_name=None, title=None)
    )


def _new_document(case_id: int, **overrides) -> Document:
    defaults = dict(
        case_id=case_id,
        file_name="sample-03.pdf",
        storage_path="/refs/sample-03.pdf",
        kind="pdf",
        page_count=2,
        read_status="success",
        content_hash="hash-abc",
        received_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Document(**defaults)


async def test_create_with_details_saves_document_pages_and_email_parts(
    db_session,
) -> None:
    """document + document_pages + email_parts をまとめて保存できる。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)
    document = _new_document(case.id, kind="eml", content_hash="hash-eml")

    saved = await repo.create_with_details(
        document,
        pages=[DocumentPage(locator="p.1", seq=1, text="dummy page text", cells=None)],
        email_parts=[
            EmailPart(
                part_role="latest_body",
                seq=1,
                sent_at=datetime.now(UTC),
                from_addr="a@example.com",
                subject="件名",
                body="本文",
                attachment_name=None,
            )
        ],
    )

    assert saved.id is not None
    page = await repo.get_page_by_locator(saved.id, "p.1")
    assert page is not None
    assert page.text == "dummy page text"


async def test_list_by_case_and_count_by_case(db_session) -> None:
    """案件ごとの一覧・件数が正しく取れる。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)
    await repo.create_with_details(_new_document(case.id, file_name="doc-a.pdf"))
    await repo.create_with_details(_new_document(case.id, file_name="doc-b.pdf"))

    documents = await repo.list_by_case(case.id)
    count = await repo.count_by_case(case.id)

    assert len(documents) == 2
    assert count == 2


async def test_get_page_by_locator(db_session) -> None:
    """locator を指定してページを取得できる。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)
    document = await repo.create_with_details(
        _new_document(case.id),
        pages=[
            DocumentPage(locator="p.1", seq=1, text="page one", cells=None),
            DocumentPage(locator="p.2", seq=2, text="page two", cells=None),
        ],
    )

    page2 = await repo.get_page_by_locator(document.id, "p.2")

    assert page2 is not None
    assert page2.text == "page two"


async def test_add_document_issue(db_session) -> None:
    """document_issues に読取不能範囲を追加できる（report_unreadable 相当）。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)
    document = await repo.create_with_details(_new_document(case.id))

    issue = await repo.add_issue(
        DocumentIssue(
            document_id=document.id,
            agent_run_id=None,
            locator="p.1",
            issue_type="unreadable_page",
            detail="画像のみで文字が取得できない",
        )
    )

    assert issue.id is not None


async def test_partial_read_status_is_kept_distinct_from_success(db_session) -> None:
    """read_status=partial は success と区別して保持される。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)

    document = await repo.create_with_details(
        _new_document(case.id, read_status="partial", file_name="partial-doc.pdf")
    )

    documents = await repo.list_by_case(case.id)
    saved = next(d for d in documents if d.id == document.id)
    assert saved.read_status == "partial"
    assert saved.read_status != "success"


async def test_duplicate_content_hash_keeps_both_documents(db_session) -> None:
    """同一 content_hash の資料を2件投入しても両方が一覧に残る（X03）。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)

    await repo.create_with_details(
        _new_document(case.id, file_name="first.pdf", content_hash="same-hash")
    )
    await repo.create_with_details(
        _new_document(case.id, file_name="second.pdf", content_hash="same-hash")
    )

    documents = await repo.list_by_case(case.id)
    same_hash_docs = [d for d in documents if d.content_hash == "same-hash"]
    assert len(same_hash_docs) == 2


async def test_unsupported_kind_document_is_recorded(db_session) -> None:
    """未対応形式（.pptx 等）でも投入の事実を資料一覧に残せる（FUNC-01 X01）。

    documents.kind の CHECK に 'unsupported' が無いと、この保存は実 DB で失敗する
    （リビジョン 540727e02dcb で追加）。ページは作らない。
    """
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)

    document = await repo.create_with_details(
        _new_document(
            case.id,
            file_name="proposal.pptx",
            kind="unsupported",
            read_status="unsupported",
        )
    )

    documents = await repo.list_by_case(case.id)
    saved = next(d for d in documents if d.id == document.id)
    assert saved.kind == "unsupported"
    assert saved.read_status == "unsupported"
    assert await repo.get_page_by_locator(document.id, "p.1") is None


async def test_search_pages_escapes_ilike_wildcards(db_session) -> None:
    """reviewer 指摘 軽-2: 検索語に含まれる `%` `_` はワイルドカードとして
    展開されず、リテラル文字として扱われる。"""
    case = await _make_case(db_session)
    repo = DocumentRepository(db_session)
    document = await repo.create_with_details(
        _new_document(case.id, file_name="discount.pdf"),
        pages=[
            DocumentPage(locator="p.1", seq=1, text="10%_OFF クーポン", cells=None),
            DocumentPage(locator="p.2", seq=2, text="10XOFF クーポン", cells=None),
        ],
    )

    results = await repo.search_pages(case.id, "10%_OFF", limit=10)

    matched_locators = {page.locator for doc, page in results if doc.id == document.id}
    assert matched_locators == {"p.1"}
