"""Export wire contracts through the actual application with a service double."""
from datetime import datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import httpx
import pytest
from app.domain.draft_errors import DraftError
from app.domain.export_types import ExportWithIntegrity, ExportResult
from tests.fixtures.export_data import AT

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CONTENT = b"PK\x03\x04synthetic-xlsx"
EXPORT_KEYS = {
    "exportId",
    "fileName",
    "storagePath",
    "contentHash",
    "exportedAt",
    "stateAtExport",
    "sendoffAtExport",
    "unresolvedAtExport",
    "isInitial",
    "integrity",
}
EVIDENCE_KEYS = {
    "evidenceId",
    "itemId",
    "fileName",
    "field",
    "rawValue",
    "adoptedValue",
    "documentId",
    "locator",
    "quote",
    "appliedCondition",
    "conversionNote",
    "changeReason",
    "priorValue",
}


@pytest.fixture
async def export_http():
    from app.main import app
    from app.api import dependencies

    history = ExportWithIntegrity(
        5,
        "S-01_v2_draft_20260913-140305.xlsx",
        "synthetic/5.xlsx",
        "abc",
        AT,
        "draft",
        "undecided",
        2,
        True,
        "intact",
    )
    record = N(id=5, file_name=history.file_name)
    evidence = N(
        id=3,
        item_id=None,
        file_name="synthetic.pdf",
        field="customer_name",
        raw_value="原値",
        adopted_value="原値",
        document_id=4,
        locator="p.1",
        quote="=HYPERLINK('x')",
        applied_condition=None,
        conversion_note="換算なし",
        change_reason=None,
        prior_value=None,
        version_id=7,
        private_secret="not-published",
    )
    service = N(
        export=AsyncMock(return_value=ExportResult(record, CONTENT)),
        list_exports=AsyncMock(return_value=[history]),
        list_evidence=AsyncMock(return_value=[evidence]),
    )
    previous = app.dependency_overrides.copy()
    # Missing dependency/route is observable as HTTP 404 in the initial RED run.
    dependency = getattr(dependencies, "get_export_service", object())
    app.dependency_overrides[dependency] = lambda: service
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield N(app=app, client=client, service=service, history=history)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


async def test_export_returns_service_bytes_and_download_headers(export_http):
    response = await export_http.client.post("/api/v1/ui/versions/7/exports")
    assert response.status_code == 200
    assert response.content == CONTENT
    assert response.headers["content-type"] == MIME
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="{export_http.history.file_name}"'
    )
    assert response.headers["x-export-id"] == "5"
    export_http.service.export.assert_awaited_once_with(7)


@pytest.mark.parametrize(
    "body", [b"{}", b'{"exportedAt":"2099-01-01","recordedBy":"synthetic-secret"}']
)
async def test_nonempty_export_body_is_rejected_without_calling_service(
    export_http, body
):
    response = await export_http.client.post(
        "/api/v1/ui/versions/7/exports", content=body
    )
    assert (
        response.status_code == 400 and response.json()["code"] == "E_REQUEST_INVALID"
    )
    assert "synthetic-secret" not in response.text
    export_http.service.export.assert_not_awaited()


async def test_history_exact_camel_keys_and_server_metadata(export_http):
    response = await export_http.client.get("/api/v1/ui/versions/7/exports")
    assert response.status_code == 200
    assert set(response.json()) == {"exports"}
    row = response.json()["exports"][0]
    assert set(row) == EXPORT_KEYS
    assert row["exportId"] == 5 and row["isInitial"] is True
    assert row["integrity"] == "intact" and row["unresolvedAtExport"] == 2
    assert row["storagePath"] == "synthetic/5.xlsx" and row["contentHash"] == "abc"
    assert datetime.fromisoformat(row["exportedAt"]) == AT
    export_http.service.list_exports.assert_awaited_once_with(7)


async def test_bulk_evidence_includes_case_level_and_filename_without_internal_fields(
    export_http
):
    response = await export_http.client.get("/api/v1/ui/versions/7/evidence")
    assert response.status_code == 200
    assert set(response.json()) == {"evidences"}
    row = response.json()["evidences"][0]
    assert set(row) == EVIDENCE_KEYS
    assert row["itemId"] is None and row["evidenceId"] == 3
    assert row["fileName"] == "synthetic.pdf" and row["quote"] == "=HYPERLINK('x')"
    assert "not-published" not in response.text
    export_http.service.list_evidence.assert_awaited_once_with(7)


@pytest.mark.parametrize(
    "path,method,key",
    [
        ("exports", "list_exports", "exports"),
        ("evidence", "list_evidence", "evidences"),
    ],
)
async def test_empty_reads_are_200_arrays(export_http, path, method, key):
    getattr(export_http.service, method).return_value = []
    response = await export_http.client.get(f"/api/v1/ui/versions/7/{path}")
    assert response.status_code == 200 and response.json() == {key: []}


@pytest.mark.parametrize(
    "http_method,path,method,code,status",
    [
        ("POST", "exports", "export", "E_VERSION_NOT_FINALIZED", 409),
        ("POST", "exports", "export", "E_NOT_FOUND", 404),
        ("GET", "exports", "list_exports", "E_NOT_FOUND", 404),
        ("GET", "evidence", "list_evidence", "E_NOT_FOUND", 404),
    ],
)
async def test_domain_errors_have_common_json(
    export_http, http_method, path, method, code, status
):
    getattr(export_http.service, method).side_effect = DraftError(
        code, "版を確認してください"
    )
    response = await export_http.client.request(
        http_method, f"/api/v1/ui/versions/7/{path}"
    )
    assert response.status_code == status
    assert response.json() == {
        "code": code,
        "message": "版を確認してください",
        "details": {},
    }
    assert response.headers["content-type"] == "application/json"
    assert "x-export-id" not in response.headers


@pytest.mark.parametrize(
    "http_method,path", [("POST", "exports"), ("GET", "exports"), ("GET", "evidence")]
)
@pytest.mark.parametrize("version_id", ["0", "invalid"])
async def test_invalid_path_never_calls_service(
    export_http, http_method, path, version_id
):
    response = await export_http.client.request(
        http_method, f"/api/v1/ui/versions/{version_id}/{path}"
    )
    assert (
        response.status_code == 422 and response.json()["code"] == "E_REQUEST_INVALID"
    )
    for name in ("export", "list_exports", "list_evidence"):
        getattr(export_http.service, name).assert_not_awaited()


async def test_download_headers_are_exposed_for_allowed_browser_origin(export_http):
    from starlette.middleware.cors import CORSMiddleware

    cors = next(m for m in export_http.app.user_middleware if m.cls is CORSMiddleware)
    origin = cors.kwargs["allow_origins"][0]
    response = await export_http.client.post(
        "/api/v1/ui/versions/7/exports", headers={"Origin": origin}
    )
    assert response.status_code == 200
    assert {"content-disposition", "x-export-id"} <= {
        h.strip().lower()
        for h in response.headers.get("access-control-expose-headers", "").split(",")
    }
    assert response.headers["access-control-allow-origin"] == origin


def test_openapi_export_binary_headers_and_read_models():
    from app.main import app

    schema = app.openapi()
    operation = schema["paths"]["/api/v1/ui/versions/{versionId}/exports"]["post"]
    assert "requestBody" not in operation
    response = operation["responses"]["200"]
    assert set(response["content"]) == {MIME}
    assert response["content"][MIME]["schema"] == {"type": "string", "format": "binary"}
    assert set(response["headers"]) == {"Content-Disposition", "X-Export-Id"}
    assert operation["responses"]["409"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/ErrorResponse")
    assert (
        set(schema["components"]["schemas"]["ExportRecord"]["required"]) == EXPORT_KEYS
    )
    assert (
        set(schema["components"]["schemas"]["VersionEvidenceRecord"]["required"])
        == EVIDENCE_KEYS
    )
