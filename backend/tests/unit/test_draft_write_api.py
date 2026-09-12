from tests.fixtures.draft_data import item, header
from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.api.agent.endpoints.drafts import router as write_router
from app.api.common.draft_validation import router as validation_router
from app.api.dependencies import get_draft_service
from app.api.errors import ApiError, api_error_handler
from app.domain.draft_errors import DraftError
from app.services.draft_validation import ValidationResult, Violation


@pytest.fixture
def service():
    return N(
        save_header=AsyncMock(return_value=N(id=1)),
        add_items=AsyncMock(return_value=[N(id=2, row_code="1")]),
        add_evidences=AsyncMock(return_value=[N(id=3)]),
        add_questions=AsyncMock(return_value=[N(id=4, question_code="Q1")]),
        add_inventory=AsyncMock(return_value=[N(id=5)]),
        validate=AsyncMock(
            return_value=ValidationResult(
                [], {"items": 1, "questions": 0, "inventory": 1}
            )
        ),
        finalize=AsyncMock(
            return_value=N(
                id=1,
                current_state="draft",
                is_complete=True,
                finalized_at=datetime.now(UTC),
            )
        ),
    )


@pytest.fixture
async def client(service):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(write_router, prefix="/api/v1/agent")
    for prefix in ("/api/v1/agent", "/api/v1/ui"):
        app.include_router(validation_router, prefix=prefix)

    async def provide_service():
        return service

    app.dependency_overrides[get_draft_service] = provide_service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_valid_items_return_created_ids_and_empty_rejections(client, service):
    response = await client.post(
        "/api/v1/agent/versions/1/items", json={"rows": [item()]}
    )
    assert response.status_code == 201
    assert response.json() == {"items": [{"itemId": 2, "rowCode": "1"}], "rejected": []}
    service.add_items.assert_awaited_once()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"qtyUnit": None}, "E_QTY_UNIT_REQUIRED"),
        ({"qtyState": "tba", "qtyValue": "0"}, "E_QTY_STATE_INVALID"),
        ({"sourceNo": ""}, "E_SOURCE_REF_REQUIRED"),
        ({"candidateLabel": "A"}, "E_GROUP_REQUIRED"),
        ({"odState": "stated", "odValue": "1"}, "E_UNIT_REQUIRED"),
        ({"odState": "stated"}, "E_STATE_VALUE_CONFLICT"),
        ({"convertedValue": "100"}, "E_REQUEST_INVALID"),
        ({"qtyValue": "not-a-number"}, "E_REQUEST_INVALID"),
    ],
)
async def test_invalid_items_are_rejected_before_service(client, service, change, code):
    response = await client.post(
        "/api/v1/agent/versions/1/items", json={"rows": [item() | change]}
    )
    assert response.status_code == 400
    assert response.json()["code"] == code
    service.add_items.assert_not_called()


async def test_missing_important_state_and_snake_case_input(client):
    data = item()
    del data["odState"]
    r = await client.post("/api/v1/agent/versions/1/items", json={"rows": [data]})
    assert r.status_code == 400 and r.json()["code"] == "E_STATE_REQUIRED"
    data = item()
    data["qty_value"] = data.pop("qtyValue")
    r = await client.post("/api/v1/agent/versions/1/items", json={"rows": [data]})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "path,payload,key",
    [
        ("header", header(), "headerId"),
        (
            "evidence",
            {
                "field": "qty",
                "rawValue": "150 MT",
                "adoptedValue": "150 MT",
                "documentId": 1,
                "locator": "body:1",
                "quote": "150 MT",
            },
            "evidenceId",
        ),
        (
            "questions",
            {"questionCode": "Q1", "targetField": "qty", "reason": "confirm"},
            "questionId",
        ),
        (
            "inventory",
            {
                "entries": [
                    {
                        "documentId": 1,
                        "position": "body:1",
                        "seq": 1,
                        "excerpt": "total",
                        "status": "excluded",
                        "basis": "total",
                    }
                ]
            },
            "entries",
        ),
    ],
)
async def test_other_writes(client, path, payload, key):
    r = await client.post("/api/v1/agent/versions/1/" + path, json=payload)
    assert r.status_code == 201 and key in r.json()


@pytest.mark.parametrize(
    "code,status",
    [
        ("E_VERSION_FINALIZED", 409),
        ("E_EVIDENCE_DUPLICATE", 409),
        ("E_NOT_FOUND", 404),
        ("E_TARGET_INVALID", 400),
    ],
)
async def test_domain_errors_use_common_contract(client, service, code, status):
    service.save_header.side_effect = DraftError(code, "example", {"versionId": 1})
    r = await client.post("/api/v1/agent/versions/1/header", json=header())
    assert r.status_code == status
    assert r.json() == {"code": code, "message": "example", "details": {"versionId": 1}}


async def test_validation_is_readonly_on_both_namespaces(client, service):
    service.validate.return_value = ValidationResult(
        [Violation("missing_evidence", "欠落", 2)],
        {"items": 1, "questions": 0, "inventory": 1},
    )
    for namespace in ("agent", "ui"):
        r = await client.get(f"/api/v1/{namespace}/versions/1/validation")
        assert r.status_code == 200
        assert r.json()["violations"][0]["itemId"] == 2
    service.finalize.assert_not_called()


async def test_finalize_returns_draft_and_ui_cannot_write(client):
    r = await client.post("/api/v1/agent/versions/1/finalize")
    assert r.status_code == 200 and r.json()["currentState"] == "draft"
    r = await client.post("/api/v1/ui/versions/1/items", json={"rows": [item()]})
    assert r.status_code == 404


@pytest.mark.parametrize("field", ["documentId", "locator", "quote"])
async def test_missing_evidence_source_returns_source_ref_code(client, field):
    payload = {
        "field": "qty",
        "rawValue": "150 MT",
        "adoptedValue": "150 MT",
        "documentId": 1,
        "locator": "body:1",
        "quote": "150 MT",
    }
    payload.pop(field)
    response = await client.post("/api/v1/agent/versions/1/evidence", json=payload)
    assert (
        response.status_code == 400
        and response.json()["code"] == "E_SOURCE_REF_REQUIRED"
    )
