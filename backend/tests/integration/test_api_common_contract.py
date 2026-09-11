"""共通形式（05-api-ipo.md 0.2）の契約テスト。

- エラー応答が {code, message, details} の形であること
- 日時が ISO 8601（タイムゾーンつき）で返り、API が日時を補完しないこと
- `DomainError.details` のキーが camelCase であること（0.4。中-8: `case_code` の
  snake_case 漏れを reviewer が実応答で検出したため、機械的に再発防止する）
"""

from datetime import UTC, datetime

import pytest

from app.core.config import settings
from app.models.cases import Case
from app.models.documents import Document, DocumentPage
from app.repositories.case_repository import CaseRepository
from app.repositories.document_repository import DocumentRepository

CASES_PATH = "/api/v1/ui/cases"
UI_DOCUMENTS_PATH = "/api/v1/ui/documents"


@pytest.fixture(autouse=True)
def _use_tmp_storage_root(tmp_path, monkeypatch):
    """413/415 の保存経路が実 `backend/storage/` に書き込まないようにする
    （tests/integration/test_api_document_intake.py 中-7 と同じ方針）。"""
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))


def _assert_details_keys_are_camel_case(details: dict) -> None:
    for key in details:
        assert "_" not in key, f"details キー '{key}' が snake_case のままです"


def test_error_response_has_code_message_details_shape(client) -> None:
    """異常系: エラー応答は {code, message, details} の形（0.2）。"""
    response = client.get(f"{CASES_PATH}/999999")

    assert response.status_code == 404
    body = response.json()
    assert set(body.keys()) == {"code", "message", "details"}
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)
    assert isinstance(body["details"], dict)


def test_created_at_is_returned_as_timezone_aware_iso8601(client) -> None:
    """正常系: createdAt がタイムゾーンつき ISO 8601 で返る（0.2）。"""
    response = client.post(
        CASES_PATH,
        json={"caseCode": "CASE-CONTRACT-001", "customerName": None, "title": None},
    )

    assert response.status_code == 201
    created_at = response.json()["createdAt"]
    parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_not_found_error_details_keys_are_camel_case(client) -> None:
    """404 E_NOT_FOUND: details.caseId が camelCase。"""
    response = client.get(f"{CASES_PATH}/999999")

    assert response.status_code == 404
    _assert_details_keys_are_camel_case(response.json()["details"])


def test_duplicate_case_code_error_details_keys_are_camel_case(client) -> None:
    """409 E_DUPLICATE_CASE_CODE: details.caseCode が camelCase（中-8）。"""
    payload = {
        "caseCode": "CASE-CONTRACT-DUP-001",
        "customerName": None,
        "title": None,
    }
    client.post(CASES_PATH, json=payload)

    response = client.post(CASES_PATH, json=payload)

    assert response.status_code == 409
    _assert_details_keys_are_camel_case(response.json()["details"])


async def test_unreadable_error_details_keys_are_camel_case(client, db_session) -> None:
    """409 E_UNREADABLE: details.documentId が camelCase。"""
    case_repo = CaseRepository(db_session)
    case = await case_repo.create(
        Case(case_code="CASE-CONTRACT-UNREADABLE", customer_name=None, title=None)
    )
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        Document(
            case_id=case.id,
            file_name="broken.pdf",
            storage_path="/tmp/does-not-matter.pdf",
            kind="pdf",
            page_count=1,
            read_status="unreadable",
            content_hash="hash",
            received_at=datetime.now(UTC),
        ),
        pages=[DocumentPage(locator="p.1", seq=1, text=None, cells=None)],
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/content")

    assert response.status_code == 409
    _assert_details_keys_are_camel_case(response.json()["details"])


async def test_not_email_error_details_keys_are_camel_case(client, db_session) -> None:
    """409 E_NOT_EMAIL: details.documentId が camelCase。"""
    case_repo = CaseRepository(db_session)
    case = await case_repo.create(
        Case(case_code="CASE-CONTRACT-NOTEMAIL", customer_name=None, title=None)
    )
    doc_repo = DocumentRepository(db_session)
    document = await doc_repo.create_with_details(
        Document(
            case_id=case.id,
            file_name="sample.pdf",
            storage_path="/tmp/does-not-matter.pdf",
            kind="pdf",
            page_count=1,
            read_status="success",
            content_hash="hash",
            received_at=datetime.now(UTC),
        )
    )

    response = client.get(f"{UI_DOCUMENTS_PATH}/{document.id}/email")

    assert response.status_code == 409
    _assert_details_keys_are_camel_case(response.json()["details"])


def test_limit_exceeded_error_details_keys_are_camel_case(client, monkeypatch) -> None:
    """413 E_LIMIT_EXCEEDED: details.limit/max/actual は元から camelCase 相当
    （アンダースコア無し）だが、機械的に固定する。"""
    create_resp = client.post(
        CASES_PATH,
        json={
            "caseCode": "CASE-CONTRACT-413",
            "customerName": None,
            "title": None,
        },
    )
    case_id = create_resp.json()["caseId"]
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0)

    response = client.post(
        f"{CASES_PATH}/{case_id}/documents",
        files={"file": ("too-big.pdf", b"x" * 1024, "application/pdf")},
    )

    assert response.status_code == 413
    _assert_details_keys_are_camel_case(response.json()["details"])


def test_unsupported_format_error_details_keys_are_camel_case(client) -> None:
    """415 E_UNSUPPORTED_FORMAT: details.documentId が camelCase。"""
    create_resp = client.post(
        CASES_PATH,
        json={
            "caseCode": "CASE-CONTRACT-415",
            "customerName": None,
            "title": None,
        },
    )
    case_id = create_resp.json()["caseId"]

    response = client.post(
        f"{CASES_PATH}/{case_id}/documents",
        files={"file": ("proposal.pptx", b"dummy", "application/vnd.ms-powerpoint")},
    )

    assert response.status_code == 415
    _assert_details_keys_are_camel_case(response.json()["details"])
