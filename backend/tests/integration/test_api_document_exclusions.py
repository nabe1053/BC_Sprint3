"""F-16 API: #5a 資料の除外・#5b 除外済みの一覧（UI 専用）・#4 から外れること。"""
import pytest

from app.core.config import settings

CASES = "/api/v1/ui/cases"


@pytest.fixture(autouse=True)
def _tmp_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_ROOT", str(tmp_path))


def _case_with_doc(client, code):
    case_id = client.post(
        CASES, json={"caseCode": code, "customerName": None, "title": None}
    ).json()["caseId"]
    doc = client.post(
        f"{CASES}/{case_id}/documents",
        files={"file": ("wrong.txt", "needle".encode(), "text/plain")},
    )
    assert doc.status_code == 201
    return case_id, doc.json()["documentId"]


def test_exclude_hides_document_from_list_and_lists_exclusion(client):
    case_id, doc_id = _case_with_doc(client, "EXCL-API-1")

    response = client.post(
        f"{CASES}/{case_id}/documents/{doc_id}/exclusion",
        json={"recordedBy": " 担当者 "},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["documentId"] == doc_id and body["recordedBy"] == "担当者"
    assert body["recordedAt"]
    listed = client.get(f"{CASES}/{case_id}/documents").json()["documents"]
    assert listed == []
    excluded = client.get(f"{CASES}/{case_id}/document-exclusions").json()
    assert [
        (e["documentId"], e["fileName"], e["recordedBy"])
        for e in excluded["exclusions"]
    ] == [(doc_id, "wrong.txt", "担当者")]


@pytest.mark.parametrize(
    "body, status, code",
    [
        ({"recordedBy": "  "}, 400, "E_RECORDER_REQUIRED"),
        ({}, 400, "E_RECORDER_REQUIRED"),
    ],
)
def test_exclude_requires_recorder(client, body, status, code):
    case_id, doc_id = _case_with_doc(client, "EXCL-API-2")
    response = client.post(f"{CASES}/{case_id}/documents/{doc_id}/exclusion", json=body)
    assert (response.status_code, response.json()["code"]) == (status, code)
    assert len(client.get(f"{CASES}/{case_id}/documents").json()["documents"]) == 1


def test_exclude_twice_and_wrong_case(client):
    case_id, doc_id = _case_with_doc(client, "EXCL-API-3")
    other_id, _ = _case_with_doc(client, "EXCL-API-3b")
    url = f"{CASES}/{case_id}/documents/{doc_id}/exclusion"
    assert client.post(url, json={"recordedBy": "担当"}).status_code == 201
    again = client.post(url, json={"recordedBy": "担当"})
    assert (again.status_code, again.json()["code"]) == (409, "E_ALREADY_EXCLUDED")
    wrong = client.post(
        f"{CASES}/{other_id}/documents/{doc_id}/exclusion", json={"recordedBy": "担当"}
    )
    assert (wrong.status_code, wrong.json()["code"]) == (404, "E_NOT_FOUND")


def test_exclusion_routes_are_ui_only(client):
    case_id, doc_id = _case_with_doc(client, "EXCL-API-4")
    response = client.post(
        f"/api/v1/agent/cases/{case_id}/documents/{doc_id}/exclusion",
        json={"recordedBy": "担当"},
    )
    assert response.status_code in (404, 405)
    assert client.get(
        f"/api/v1/agent/cases/{case_id}/document-exclusions"
    ).status_code in (404, 405)
