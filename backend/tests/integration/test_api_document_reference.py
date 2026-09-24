"""API #4・#6・#7・#10 資料参照系（05-api-ipo.md 1章 A・5章の要約・0.3 区分 UI/AGENT・UI）。

対象パス:
    #4  GET /api/v1/ui/cases/{caseId}/documents    と GET /api/v1/agent/cases/{caseId}/documents
    #6  GET /api/v1/ui/documents/{documentId}/content と GET /api/v1/agent/documents/{documentId}/content
    #7  GET /api/v1/ui/documents/{documentId}/email  と GET /api/v1/agent/documents/{documentId}/email
    #10 GET /api/v1/ui/documents/{documentId}/file（UI のみ・AGENT には登録しない）

DB のシード（case/document/document_pages/email_parts）は Repository を直接使って
実データを用意する（下位は実 DB。エラー分岐だけ意図的な入力で作る）。

期待するレスポンス契約（仮決め）:
    #4: {"caseId": ..., "caseName": ..., "documents": [{"documentId":..., "fileName":...,
         "kind":..., "readStatus":...}, ...]}
    #6: {"pages": [{"locator":..., "text":..., "readStatus": "success"|"unreadable"}]}
         全体として読取不能なときのみ 409 E_UNREADABLE。
    #7: {"parts": [{"partRole":..., "seq":..., "sentAt":..., "fromAddr":..., "subject":...,
         "body":..., "attachmentName":...}]}。.eml でない資料は 409 E_NOT_EMAIL。
    #10: バイナリ本体。storage_path が STORAGE_ROOT 外を指す場合は 404。
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.config import settings
from app.models.cases import Case
from app.models.documents import Document, DocumentIssue, DocumentPage, EmailPart
from app.repositories.case_repository import CaseRepository
from app.repositories.document_repository import DocumentRepository

CASES_PATH = "/api/v1/ui/cases"
AGENT_CASES_PATH = "/api/v1/agent/cases"
UI_DOCUMENTS_PATH = "/api/v1/ui/documents"
AGENT_DOCUMENTS_PATH = "/api/v1/agent/documents"


async def _make_case(
    db_session, case_code: str = "CASE-REF-001", title: str | None = "羽島沖ガス田"
) -> Case:
    repo = CaseRepository(db_session)
    return await repo.create(Case(case_code=case_code, customer_name=None, title=title))


def _new_document(case_id: int, **overrides) -> Document:
    defaults = dict(
        case_id=case_id,
        file_name="sample.pdf",
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
# #4 資料一覧
# ---------------------------------------------------------------------------


async def test_list_documents_ui_returns_case_id_and_name_and_documents(
    client, db_session
) -> None:
    """正常系: 資料一覧は案件ID・案件名・資料のreadStatusを併せて返す（05-api-ipo #4）。"""
    case = await _make_case(db_session)
    doc_repo = DocumentRepository(db_session)
    await doc_repo.create_with_details(
        _new_document(case.id, file_name="doc-a.pdf", read_status="success")
    )
    await doc_repo.create_with_details(
        _new_document(case.id, file_name="doc-b.pdf", read_status="partial")
    )

    response = client.get(f"{CASES_PATH}/{case.id}/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["caseId"] == case.id
    assert body["caseName"] == case.title
    file_names = {d["fileName"] for d in body["documents"]}
    assert file_names == {"doc-a.pdf", "doc-b.pdf"}
    read_statuses = {d["fileName"]: d["readStatus"] for d in body["documents"]}
    assert read_statuses["doc-b.pdf"] == "partial"


async def test_list_documents_returns_page_count_and_unreadable_locators(
    client, db_session
) -> None:
    """#4: ページ／シート数と受付時の読取不能範囲を返す（SCR-02「PDF・4ページ」「一部読取不能（p.2）」）。

    ページ数が判定できない資料（.eml・破損）は null のまま返す（0 で埋めない・CV-003）。
    """
    case = await _make_case(db_session, case_code="CASE-REF-PAGES")
    doc_repo = DocumentRepository(db_session)
    await doc_repo.create_with_details(
        _new_document(case.id, file_name="p2.pdf", read_status="partial", page_count=4),
        issues=[
            DocumentIssue(
                locator="p.2", issue_type="unreadable_page", detail="画像のみ"
            )
        ],
    )
    await doc_repo.create_with_details(
        _new_document(case.id, file_name="mail.eml", kind="eml", page_count=None)
    )

    response = client.get(f"{CASES_PATH}/{case.id}/documents")

    assert response.status_code == 200
    rows = {d["fileName"]: d for d in response.json()["documents"]}
    assert rows["p2.pdf"]["pageCount"] == 4
    assert rows["p2.pdf"]["unreadableLocators"] == ["p.2"]
    assert rows["mail.eml"]["pageCount"] is None
    assert rows["mail.eml"]["unreadableLocators"] == []


async def test_list_documents_ui_and_agent_return_same_body(client, db_session) -> None:
    """正常系: /ui/* と /agent/* が同じ応答を返す（0.3 UI/AGENT 両方登録）。"""
    case = await _make_case(db_session, case_code="CASE-REF-002")
    doc_repo = DocumentRepository(db_session)
    await doc_repo.create_with_details(_new_document(case.id, file_name="doc-a.pdf"))

    ui_response = client.get(f"{CASES_PATH}/{case.id}/documents")
    agent_response = client.get(f"{AGENT_CASES_PATH}/{case.id}/documents")

    assert ui_response.status_code == agent_response.status_code == 200
    assert ui_response.json() == agent_response.json()


def test_list_documents_missing_case_returns_404(client) -> None:
    """異常系: 存在しない案件IDは 404。"""
    response = client.get(f"{CASES_PATH}/999999/documents")

    assert response.status_code == 404
    assert response.json()["code"] == "E_NOT_FOUND"


# ---------------------------------------------------------------------------
# #6 本文取得
# ---------------------------------------------------------------------------


async def test_get_content_returns_page_level_read_status_without_dropping_readable_pages(
    client, db_session
) -> None:
    """正常系: 一部ページが読めない資料でも 200 で返し、当該ページを unreadable と示す
    （読めたページまで落とさない・N03・05-api-ipo #6）。"""
    case = await _make_case(db_session, case_code="CASE-REF-003")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, read_status="partial"),
        pages=[
            DocumentPage(locator="p.1", seq=1, text="読めた本文", cells=None),
            DocumentPage(locator="p.2", seq=2, text=None, cells=None),
        ],
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/content")

    assert response.status_code == 200
    pages = {p["locator"]: p for p in response.json()["pages"]}
    assert pages["p.1"]["readStatus"] == "success"
    assert pages["p.1"]["text"] == "読めた本文"
    assert pages["p.2"]["readStatus"] == "unreadable"


async def test_get_content_all_unreadable_returns_409(client, db_session) -> None:
    """異常系: 要求範囲が全体として読取不能なときのみ 409 E_UNREADABLE。"""
    case = await _make_case(db_session, case_code="CASE-REF-004")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, read_status="unreadable"),
        pages=[DocumentPage(locator="p.1", seq=1, text=None, cells=None)],
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/content")

    assert response.status_code == 409
    assert response.json()["code"] == "E_UNREADABLE"


async def test_get_content_from_seq_greater_than_to_seq_returns_422(
    client, db_session
) -> None:
    """異常系: fromSeq > toSeq は契約違反として 422（reviewer 指摘 軽-3。
    409 E_UNREADABLE に落とさない）。"""
    case = await _make_case(db_session, case_code="CASE-REF-010")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id),
        pages=[DocumentPage(locator="p.1", seq=1, text="本文", cells=None)],
    )

    response = client.get(
        f"{UI_DOCUMENTS_PATH}/{document.id}/content",
        params={"fromSeq": 5, "toSeq": 1},
    )

    assert response.status_code == 422


async def test_get_content_ui_and_agent_return_same_body(client, db_session) -> None:
    """正常系: /ui/* と /agent/* が同じ応答を返す。"""
    case = await _make_case(db_session, case_code="CASE-REF-005")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id),
        pages=[DocumentPage(locator="p.1", seq=1, text="本文", cells=None)],
    )

    ui_response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/content")
    agent_response = client.get(f"{AGENT_DOCUMENTS_PATH}/{document.id}/content")

    assert ui_response.status_code == agent_response.status_code == 200
    assert ui_response.json() == agent_response.json()


# ---------------------------------------------------------------------------
# #7 メール構造
# ---------------------------------------------------------------------------


async def test_get_email_returns_parts_structure(client, db_session) -> None:
    """正常系: .eml の構造（本文・引用部・添付一覧）が取得できる。"""
    case = await _make_case(db_session, case_code="CASE-REF-006")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, kind="eml", file_name="mail.eml"),
        email_parts=[
            EmailPart(
                part_role="latest_body",
                seq=1,
                sent_at=datetime.now(UTC),
                from_addr="a@example.com",
                subject="件名",
                body="本文",
                attachment_name=None,
            ),
            EmailPart(
                part_role="attachment",
                seq=2,
                sent_at=None,
                from_addr=None,
                subject=None,
                body=None,
                attachment_name="spec.pdf",
            ),
        ],
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/email")

    assert response.status_code == 200
    parts = response.json()["parts"]
    roles = {p["partRole"] for p in parts}
    assert roles == {"latest_body", "attachment"}


async def test_get_email_for_non_eml_document_returns_409(client, db_session) -> None:
    """異常系: .eml でない資料にメール構造を要求すると 409 E_NOT_EMAIL。"""
    case = await _make_case(db_session, case_code="CASE-REF-007")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(_new_document(case.id, kind="pdf"))

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/email")

    assert response.status_code == 409
    assert response.json()["code"] == "E_NOT_EMAIL"


# ---------------------------------------------------------------------------
# #10 原ファイル取得（UI のみ）
# ---------------------------------------------------------------------------


async def test_get_file_returns_saved_original_bytes(
    client, db_session, tmp_path, monkeypatch
) -> None:
    """正常系: 保存した原本のバイト列がそのまま返る。"""
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root))

    case = await _make_case(db_session, case_code="CASE-REF-008")
    case_dir = storage_root / str(case.id)
    case_dir.mkdir()
    file_path = case_dir / "abc.pdf"
    file_path.write_bytes(b"%PDF-1.4 dummy content")

    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, storage_path=str(file_path))
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/file")

    assert response.status_code == 200
    assert response.content == b"%PDF-1.4 dummy content"


async def test_get_file_outside_storage_root_returns_404(
    client, db_session, tmp_path, monkeypatch
) -> None:
    """異常系: storage_path が STORAGE_ROOT の外を指す資料は 404（パストラバーサル防止・決定1）。"""
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root))

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.pdf"
    outside_file.write_bytes(b"leaked content")

    case = await _make_case(db_session, case_code="CASE-REF-009")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, storage_path=str(outside_file))
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/file")

    assert response.status_code == 404


async def test_get_file_via_symlink_escaping_storage_root_returns_404(
    client, db_session, tmp_path, monkeypatch
) -> None:
    """異常系: 軽微2: STORAGE_ROOT 配下の symlink が外部の実ファイルを指す場合も
    404（`realpath` による解決が正しく機能していることを固定する。`abspath` に
    戻すと symlink はそのまま STORAGE_ROOT 配下のパス文字列として前方一致して
    しまい、このテストが無いと検知できない）。"""
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(storage_root))

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    outside_file = outside_dir / "secret.pdf"
    outside_file.write_bytes(b"leaked content")

    case_dir = storage_root / "1"
    case_dir.mkdir()
    symlink_path = case_dir / "linked.pdf"
    symlink_path.symlink_to(outside_file)

    case = await _make_case(db_session, case_code="CASE-REF-011")
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        _new_document(case.id, storage_path=str(symlink_path))
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/file")

    assert response.status_code == 404
