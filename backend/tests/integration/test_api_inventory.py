"""Real HTTP + DI + PostgreSQL inventory read and coverage lifecycle."""
import httpx
from fastapi import FastAPI

from app.api.errors import ApiError, api_error_handler
from app.api.ui.router import router
from app.core.database import get_db
from app.repositories.record_repository import RecordRepository
from app.services.record_service import RecordService
from tests.fixtures.inventory_data import seed_inventory


async def test_inventory_http_isolates_versions_and_reflects_coverage(db_session):
    first = await seed_inventory(db_session)
    other = await seed_inventory(db_session)
    pending = await seed_inventory(db_session, finalized=False)
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")

    async def test_session():
        yield db_session

    app.dependency_overrides[get_db] = test_session
    path = f"/api/v1/ui/versions/{first.seed.version.id}/inventory"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["summary"] == {
            "sourceEntryCount": 12,
            "sourceItemCount": 8,
            "outputRowCount": 11,
            "splitEntryIds": sorted(first.entries[i].id for i in (6, 7, 8)),
            "excludedEntryIds": sorted(first.entries[i].id for i in (9, 10, 11, 12)),
            "unmappedEntryIds": [],
            "orphanItemIds": [],
            "multiMappedItemIds": [],
            "inconsistentEntryIds": [],
            "coverage": None,
        }
        assert [row["entryId"] for row in body["entries"]] == [
            row.id
            for row in sorted(first.entries.values(), key=lambda row: (row.seq, row.id))
        ]
        assert {row["documentFileName"] for row in body["entries"]} == {
            first.document.file_name
        }
        assert {row["documentId"] for row in body["entries"]} == {first.document.id}
        assert {row["itemId"] for row in body["items"]} == {
            row.id for row in first.items.values()
        }
        assert not {row["itemId"] for row in body["items"]} & {
            row.id for row in other.items.values()
        }
        records = RecordService(RecordRepository(db_session))
        coverage = await records.confirm(
            first.seed.version.id, {"kind": "coverage", "recorded_by": "確認者"}
        )
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json()["summary"]["coverage"]["recordedBy"] == "確認者"
        assert response.json()["summary"]["coverage"]["confirmationId"] == coverage.id
        await records.undo_confirmation(
            first.seed.version.id, coverage.id, {"recorded_by": "取消者"}
        )
        assert (await client.get(path)).json()["summary"]["coverage"] is None
        for version_id in (pending.seed.version.id, 999999):
            response = await client.get(f"/api/v1/ui/versions/{version_id}/inventory")
            assert (
                response.status_code == 404 and response.json()["code"] == "E_NOT_FOUND"
            )
