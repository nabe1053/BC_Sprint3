"""Real HTTP/DB human record lifecycle and finalized-version navigation."""
import httpx
from datetime import UTC, datetime

from fastapi import FastAPI

from app.api.errors import ApiError, api_error_handler
from app.services.record_service import RecordService
from app.repositories.record_repository import RecordRepository
from tests.fixtures.record_data import seed_record_version


async def test_edit_read_undo_preserves_source_history_and_summary(db_session):
    from app.api.dependencies import get_record_service
    from app.api.ui.router import router
    from app.models import CaseHeader
    from app.domain.draft_types import HeaderInput

    seed = await seed_record_version(db_session)
    header = HeaderInput(
        inquiry_no_state="not_stated",
        customer_name="synthetic",
        customer_name_state="stated",
        due_state="not_stated",
        place_state="not_stated",
        incoterms_state="not_stated",
        quote_deadline_tz_state="missing",
    )
    db_session.add(CaseHeader(version_id=seed.version.id, **header.model_dump()))
    await db_session.commit()
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_record_service] = lambda: RecordService(
        RecordRepository(db_session)
    )
    path = f"/api/v1/ui/versions/{seed.version.id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            path + "/edits",
            json={
                "itemId": seed.item.id,
                "field": "grade",
                "newValue": "L80",
                "reason": "照合",
                "recordedBy": "担当者",
            },
        )
        assert response.status_code == 201
        edit = response.json()["edits"][0]
        assert datetime.fromisoformat(edit["recordedAt"]).utcoffset() is not None
        response = await client.get(path + "/items")
        assert response.status_code == 200
        row = response.json()["items"][0]
        assert (
            row["grade"] == "L80"
            and row["gradeRaw"] == "K55"
            and len(row["history"]) == 1
        )
        response = await client.post(
            path + f"/edits/{edit['editId']}/undo", json={"recordedBy": "取消者"}
        )
        assert response.status_code == 200 and response.json()["undoneBy"] == "取消者"
        response = await client.get(path + "/items")
        row = response.json()["items"][0]
        assert row["grade"] == "K55" and len(row["history"]) == 1
        assert row["history"][0]["undoneBy"] == "取消者"
        response = await client.get(path)
        assert response.status_code == 200
        body = response.json()
        assert body["counts"]["editCount"] == body["counts"]["editedItemCount"] == 0
        assert (
            body["caseId"] == seed.case.id
            and body["versionNo"] == 1
            and body["currentState"] == "draft"
        )
        assert body["caseHeader"]["customerName"] == "synthetic"
        assert body["finalizedAt"] and body["isComplete"]


async def test_latest_case_version_and_version_list_ignore_unfinalized(db_session):
    from app.models import Version
    from app.repositories.case_repository import CaseRepository
    from app.services.case_service import CaseService

    seed = await seed_record_version(db_session)
    second = Version(
        case_id=seed.case.id,
        rule_set_id=seed.rule.id,
        version_no=2,
        current_state="staff_checked",
        finalized_at=datetime.now(UTC),
        is_complete=True,
    )
    pending = Version(
        case_id=seed.case.id,
        rule_set_id=seed.rule.id,
        version_no=3,
        current_state="draft",
        finalized_at=None,
        is_complete=False,
    )
    db_session.add_all([second, pending])
    await db_session.commit()
    cases = await CaseService(CaseRepository(db_session)).list_cases()
    assert [(case.id, status, latest_id) for case, status, latest_id in cases] == [
        (seed.case.id, "staff_checked", second.id)
    ]
    versions = await RecordService(RecordRepository(db_session)).list_versions(
        seed.case.id
    )
    assert [version.id for version in versions] == [second.id, seed.version.id]


async def test_row_match_confirmation_appears_and_undo_removes_it(db_session):
    from app.api.dependencies import get_record_service
    from app.api.ui.router import router

    seed = await seed_record_version(db_session)
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_record_service] = lambda: RecordService(
        RecordRepository(db_session)
    )
    path = f"/api/v1/ui/versions/{seed.version.id}"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        initial = await client.get(path + "/items")
        assert (
            initial.status_code == 200
            and initial.json()["items"][0]["rowMatch"] is None
        )
        coverage = await client.post(
            path + "/confirmations",
            json={"kind": "coverage", "recordedBy": "網羅性担当"},
        )
        assert coverage.status_code == 201
        assert (await client.get(path + "/items")).json()["items"][0][
            "rowMatch"
        ] is None
        response = await client.post(
            path + "/confirmations",
            json={
                "kind": "row_match",
                "itemId": seed.item.id,
                "recordedBy": "照合担当",
            },
        )
        assert response.status_code == 201
        confirmation = response.json()
        match = (await client.get(path + "/items")).json()["items"][0]["rowMatch"]
        assert match == {
            key: confirmation[key]
            for key in ("confirmationId", "recordedBy", "recordedAt")
        }
        response = await client.post(
            path + f"/confirmations/{confirmation['confirmationId']}/undo",
            json={"recordedBy": "取消担当"},
        )
        assert response.status_code == 200
        assert (await client.get(path + "/items")).json()["items"][0][
            "rowMatch"
        ] is None
