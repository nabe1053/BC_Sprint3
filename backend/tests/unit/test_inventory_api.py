"""UI inventory HTTP/DTO contracts with an isolated service."""
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.api.errors import ApiError, api_error_handler
from app.domain.draft_errors import DraftError
from app.domain.record_types import RowMatch
from app.services.inventory_reconciliation import reconcile
from tests.fixtures.inventory_data import s06

AT = datetime(2026, 9, 13, tzinfo=UTC)
PATH = "/api/v1/ui/versions/1/inventory"
ID_FIELDS = (
    "split_entry_ids",
    "excluded_entry_ids",
    "unmapped_entry_ids",
    "orphan_item_ids",
    "multi_mapped_item_ids",
    "inconsistent_entry_ids",
)


def result():
    data = reconcile(*s06(), version_id=1)
    return replace(
        data,
        entries=tuple(
            replace(row, document_file_name="<b>x</b>.pdf") for row in data.entries
        ),
    )


@pytest.fixture
async def inventory_http():
    from app.api.dependencies import get_inventory_service
    from app.api.ui.router import router
    from app.api.agent.router import router as agent_router

    service = N(reconcile=AsyncMock(return_value=result()))
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.dependency_overrides[get_inventory_service] = lambda: service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, service


def assert_camel_keys(value):
    if isinstance(value, dict):
        assert all("_" not in key for key in value)
        for nested in value.values():
            assert_camel_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_camel_keys(nested)


async def test_inventory_s06_http_contract_and_field_whitelists(inventory_http):
    client, service = inventory_http
    response = await client.get(PATH)
    assert response.status_code == 200
    service.reconcile.assert_awaited_once_with(1)
    body = response.json()
    assert set(body) == {"summary", "entries", "items"}
    assert body["summary"] == {
        "sourceEntryCount": 12,
        "sourceItemCount": 8,
        "outputRowCount": 11,
        "splitEntryIds": [6, 7, 8],
        "excludedEntryIds": [9, 10, 11, 12],
        "unmappedEntryIds": [],
        "orphanItemIds": [],
        "multiMappedItemIds": [],
        "inconsistentEntryIds": [],
        "coverage": None,
    }
    entry = body["entries"][0]
    assert set(entry) == {
        "entryId",
        "documentId",
        "documentFileName",
        "position",
        "sourceNo",
        "seq",
        "excerpt",
        "status",
        "statusDetail",
        "basis",
        "linkedItems",
        "linkCount",
        "judgement",
    }
    assert entry["documentFileName"] == "<b>x</b>.pdf"
    assert entry["linkedItems"] == [{"itemId": 101, "rowCode": "R101"}]
    item = body["items"][0]
    assert set(item) == {
        "itemId",
        "rowCode",
        "sourceNo",
        "seq",
        "groupCode",
        "candidateLabel",
        "sourceEntries",
        "hasSource",
    }
    assert item["sourceEntries"] == [
        {"entryId": 1, "documentId": 1, "position": "p.1", "sourceNo": "1"}
    ]
    assert_camel_keys(body)


@pytest.mark.parametrize("field", ID_FIELDS)
def test_inventory_id_sets_are_sorted_and_deduplicated(field):
    from app.api.ui.schemas.inventory import InventoryResponse

    data = result()
    summary = replace(data.summary, **{field: frozenset({8, 3, 5})})
    dto = InventoryResponse.model_validate(
        replace(data, summary=summary), from_attributes=True
    )
    assert getattr(dto.summary, field) == [3, 5, 8]
    summary = N(**{**vars(data.summary), field: [8, 3, 8, 5]})
    dto = InventoryResponse.model_validate(
        N(summary=summary, entries=data.entries, items=data.items), from_attributes=True
    )
    assert getattr(dto.summary, field) == [3, 5, 8]


async def test_coverage_is_nested_and_uses_only_record_metadata(inventory_http):
    client, service = inventory_http
    data = result()
    service.reconcile.return_value = replace(
        data, summary=replace(data.summary, coverage=RowMatch(42, "照合者", AT))
    )
    body = (await client.get(PATH)).json()
    assert "coverage" not in body
    assert body["summary"]["coverage"] == {
        "confirmationId": 42,
        "recordedBy": "照合者",
        "recordedAt": "2026-09-13T00:00:00Z",
    }
    assert (
        datetime.fromisoformat(body["summary"]["coverage"]["recordedAt"]).utcoffset()
        is not None
    )


@pytest.mark.parametrize(
    "judgement", ["mapped", "split", "excluded", "missing", "inconsistent"]
)
def test_inventory_judgement_vocabulary(judgement):
    from app.api.ui.schemas.inventory import InventoryEntryResponse

    row = replace(result().entries[0], judgement=judgement)
    assert (
        InventoryEntryResponse.model_validate(row, from_attributes=True).judgement
        == judgement
    )


@pytest.mark.parametrize(
    "change",
    [
        {"judgement": "unknown"},
        {"status": "missing"},
        {"position": None},
        {"excerpt": None},
        {"seq": 0},
        {"link_count": -1},
    ],
)
def test_inventory_entry_rejects_invalid_contract_values(change):
    from app.api.ui.schemas.inventory import InventoryEntryResponse

    with pytest.raises(ValidationError):
        InventoryEntryResponse.model_validate(
            replace(result().entries[0], **change), from_attributes=True
        )


async def test_private_attributes_never_escape_at_any_response_depth(inventory_http):
    client, service = inventory_http
    data = result()

    def private(value):
        return N(**vars(value), private="hidden", version_id=99)

    entry = private(data.entries[0])
    entry.linked_items = [private(entry.linked_items[0])]
    item = private(data.items[0])
    item.source_entries = [private(item.source_entries[0])]
    summary = private(data.summary)
    summary.coverage = private(RowMatch(42, "照合者", AT))
    service.reconcile.return_value = N(
        summary=summary, entries=[entry], items=[item], private="hidden", version_id=99
    )
    response = await client.get(PATH)
    assert response.status_code == 200
    assert (
        "hidden" not in response.text
        and "private" not in response.text
        and "versionId" not in response.text
    )
    assert_camel_keys(response.json())


async def test_inventory_not_found_uses_existing_error_contract(inventory_http):
    client, service = inventory_http
    service.reconcile.side_effect = DraftError(
        "E_NOT_FOUND", "版がありません", {"versionId": 1}
    )
    response = await client.get(PATH)
    assert response.status_code == 404
    assert response.json() == {
        "code": "E_NOT_FOUND",
        "message": "版がありません",
        "details": {"versionId": 1},
    }


@pytest.mark.parametrize("version_id", [0, -1])
async def test_invalid_version_id_is_rejected_before_service(
    inventory_http, version_id
):
    client, service = inventory_http
    response = await client.get(f"/api/v1/ui/versions/{version_id}/inventory")
    assert (
        response.status_code == 422 and response.json()["code"] == "E_REQUEST_INVALID"
    )
    service.reconcile.assert_not_awaited()


@pytest.mark.parametrize(
    "method,path", [("GET", "/api/v1/agent/versions/1/inventory"), ("POST", PATH)]
)
async def test_inventory_wrong_namespace_method_is_405_without_service(
    inventory_http, method, path
):
    client, service = inventory_http
    response = await client.request(method, path, json={})
    assert response.status_code == 405
    service.reconcile.assert_not_awaited()
