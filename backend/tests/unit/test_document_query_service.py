"""DocumentQueryService（Business Logic層）の単体テスト。Repository は mock する。

reviewer 指摘 中-1: ページ単位 readStatus の導出は Presentation ではなく
本 Service の責務。`get_content()` は `(page, read_status)` のタプル一覧を返す。
reviewer 指摘 軽-4: 空 dict `{}` は「読めた単位」に数えない（CV-001）。
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.models.documents import Document, DocumentPage
from app.services.document_query_service import DocumentQueryService
from app.services.exceptions import UnreadableError


def _make_service() -> tuple[DocumentQueryService, AsyncMock, AsyncMock]:
    document_repo = AsyncMock()
    case_repo = AsyncMock()
    return DocumentQueryService(document_repo, case_repo), document_repo, case_repo


def _document(**overrides) -> Document:
    defaults = dict(
        id=1,
        case_id=1,
        file_name="a.pdf",
        storage_path="/x/a.pdf",
        kind="pdf",
        page_count=1,
        read_status="success",
        content_hash="h",
        received_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Document(**defaults)


async def test_get_content_reports_success_for_page_with_text() -> None:
    service, document_repo, _ = _make_service()
    document_repo.get_by_id.return_value = _document()
    document_repo.list_pages.return_value = [
        DocumentPage(locator="p.1", seq=1, text="本文", cells=None)
    ]

    pages = await service.get_content(document_id=1)

    assert len(pages) == 1
    page, read_status = pages[0]
    assert page.locator == "p.1"
    assert read_status == "success"


async def test_get_content_reports_unreadable_for_page_without_text_or_cells() -> None:
    """一部ページのみ読めない場合はエラーにせず、当該ページを unreadable と示す
    （読めたページまで落とさない・N03）。"""
    service, document_repo, _ = _make_service()
    document_repo.get_by_id.return_value = _document(read_status="partial")
    document_repo.list_pages.return_value = [
        DocumentPage(locator="p.1", seq=1, text="読めた本文", cells=None),
        DocumentPage(locator="p.2", seq=2, text=None, cells=None),
    ]

    pages = await service.get_content(document_id=1)

    by_locator = {page.locator: status for page, status in pages}
    assert by_locator["p.1"] == "success"
    assert by_locator["p.2"] == "unreadable"


async def test_get_content_treats_empty_cells_dict_as_unreadable() -> None:
    """軽-4: 空 dict `{}` は「読めた単位」に数えない（CV-001）。
    ただし他ページが読めているので全体としては 200（要求範囲が全体不能ではない）。"""
    service, document_repo, _ = _make_service()
    document_repo.get_by_id.return_value = _document(kind="xlsx", read_status="partial")
    document_repo.list_pages.return_value = [
        DocumentPage(locator="Sheet0", seq=1, text=None, cells={"A1": "x"}),
        DocumentPage(locator="Sheet1", seq=2, text=None, cells={}),
    ]

    pages = await service.get_content(document_id=1)

    by_locator = {page.locator: status for page, status in pages}
    assert by_locator["Sheet0"] == "success"
    assert by_locator["Sheet1"] == "unreadable"


async def test_get_content_reports_success_for_non_empty_cells_dict() -> None:
    service, document_repo, _ = _make_service()
    document_repo.get_by_id.return_value = _document(kind="xlsx")
    document_repo.list_pages.return_value = [
        DocumentPage(locator="Sheet1", seq=1, text=None, cells={"A1": "x"})
    ]

    pages = await service.get_content(document_id=1)

    assert pages[0][1] == "success"


async def test_get_content_raises_unreadable_when_all_pages_are_unreadable() -> None:
    service, document_repo, _ = _make_service()
    document_repo.get_by_id.return_value = _document(read_status="unreadable")
    document_repo.list_pages.return_value = [
        DocumentPage(locator="p.1", seq=1, text=None, cells=None),
        DocumentPage(locator="p.2", seq=2, text=None, cells={}),
    ]

    with pytest.raises(UnreadableError):
        await service.get_content(document_id=1)


async def test_list_documents_for_case_attaches_intake_unreadable_locators() -> None:
    """#4: 資料ごとに受付時の読取不能範囲を添える（一部読取不能の対象範囲を画面に出す）。"""
    service, document_repo, case_repo = _make_service()
    case_repo.get_by_id.return_value = object()
    partial = _document(id=1, read_status="partial", page_count=4)
    clean = _document(id=2)
    document_repo.list_by_case.return_value = [partial, clean]
    document_repo.list_intake_unreadable_locators.return_value = {1: ["p.2"]}

    _, listings = await service.list_documents_for_case(case_id=1)

    assert [(doc.id, locators) for doc, locators in listings] == [
        (1, ["p.2"]),
        (2, []),
    ]
    document_repo.list_intake_unreadable_locators.assert_awaited_once_with([1, 2])
