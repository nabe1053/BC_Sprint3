"""Approval lifecycle through real HTTP, DI and PostgreSQL."""
from datetime import UTC, datetime
import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import event
from app.api.errors import ApiError, api_error_handler
from app.api.ui.router import router
from app.core.database import get_db
from app.models import Question, Case, Version, SendoffDecision
from tests.fixtures.record_data import seed_record_version, record_actor


@pytest.fixture
async def approval_client(db_session):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")

    async def session():
        yield db_session

    app.dependency_overrides[get_db] = session
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


async def test_real_di_approval_lifecycle_and_derived_flags(
    db_session, approval_client
):
    seed = await seed_record_version(db_session)
    vid, item_id, case_id = seed.version.id, seed.item.id, seed.case.id
    db_session.add(
        Question(
            version_id=vid,
            item_id=item_id,
            question_code="Q1",
            target_field="grade",
            reason="check",
        )
    )
    await db_session.commit()
    client = approval_client
    path = f"/api/v1/ui/versions/{vid}"
    actor = {"recordedBy": "人"}
    for payload in (
        {"kind": "row_match", "itemId": item_id, **actor},
        {"kind": "coverage", **actor},
    ):
        assert (
            await client.post(path + "/confirmations", json=payload)
        ).status_code == 201
    state = await client.post(
        path + "/state-events", json={"toState": "staff_checked", **actor}
    )
    assert state.status_code == 201 and state.json()["unresolvedCount"] == 1
    comment = await client.post(
        path + "/bounce-comments", json={"itemId": item_id, "comment": "確認", **actor}
    )
    assert comment.status_code == 201 and comment.json()["bounceId"] is None
    bounce = await client.post(path + "/bounces", json=actor)
    assert (
        bounce.status_code == 201
        and bounce.json()["reason"] == f"{seed.item.row_code}: 確認"
    )
    assert (await client.get(path)).json()["currentState"] == "staff_checked"
    history = (await client.get(path + "/records")).json()
    assert {row["stateEventId"] for row in history["stateEvents"]} == {
        state.json()["stateEventId"]
    }
    assert [row["bounceId"] for row in history["bounces"]] == [
        bounce.json()["bounceId"]
    ]
    assert [row["bounceCommentId"] for row in history["bounces"][0]["comments"]] == [
        comment.json()["bounceCommentId"]
    ]
    assert history["bounces"][0]["comments"][0]["bounceId"] == bounce.json()["bounceId"]
    assert history["unlinkedComments"] == []
    versions_path = f"/api/v1/ui/cases/{case_id}/versions"
    row = (await client.get(versions_path)).json()["versions"][0]
    assert row["bounced"] is True and row["needsRecheck"] is False
    assert row["carryOver"] == {
        "editCount": 0,
        "rowMatchConfirmed": 1,
        "rowMatchTotal": 1,
        "coverageRecorded": True,
        "judgementCount": 0,
    }
    assert (
        await client.post(
            path + "/state-events", json={"toState": "review_checked", **actor}
        )
    ).status_code == 201
    assert (await client.get(versions_path)).json()["versions"][0]["bounced"] is False
    edited = await client.post(
        path + "/edits",
        json={
            "itemId": item_id,
            "field": "grade",
            "newValue": "L80",
            "reason": "訂正",
            **actor,
        },
    )
    assert edited.status_code == 201
    row = (await client.get(versions_path)).json()["versions"][0]
    assert (
        row["needsRecheck"] is True
        and row["currentState"] == "staff_checked"
        and row["bounced"] is False
    )
    assert (
        await client.post(
            path + "/sendoff-decisions",
            json={"decision": "approved", "reason": "可", **actor},
        )
    ).status_code == 201
    assert (await client.get(versions_path)).json()["versions"][0]["latestSendoff"][
        "decision"
    ] == "approved"
    assert (await client.get("/api/v1/ui/cases")).json()["cases"][0][
        "latestSendoff"
    ] == "approved"
    repeated = await client.post(
        path + "/state-events", json={"toState": "staff_checked", **actor}
    )
    assert repeated.status_code == 409 and repeated.json()["code"] == "E_STATE_ORDER"


async def test_real_http_errors_keep_scope_details_and_validation_order(
    db_session, approval_client
):
    seed = await seed_record_version(db_session)
    other = await seed_record_version(db_session, finalized=False)
    vid, item_id, row_code, pending_id, foreign_item = (
        seed.version.id,
        seed.item.id,
        seed.item.row_code,
        other.version.id,
        other.item.id,
    )
    client = approval_client
    path = f"/api/v1/ui/versions/{vid}"
    actor = {"recordedBy": "人"}
    result = await client.post(
        path + "/state-events", json={"toState": "staff_checked", **actor}
    )
    assert result.status_code == 409
    assert result.json()["details"] == {
        "unmatchedItemIds": [item_id],
        "unmatchedRowCodes": [row_code],
        "coverageRecorded": False,
    }
    for version, target in ((vid, foreign_item), (pending_id, foreign_item)):
        result = await client.post(
            f"/api/v1/ui/versions/{version}/bounce-comments",
            json={"itemId": target, "comment": "確認", **actor},
        )
        assert result.status_code == 404 and result.json()["code"] == "E_NOT_FOUND"
    result = await client.post(
        path + "/state-events", json={"toState": "draft", "recordedBy": " "}
    )
    assert result.status_code == 400 and result.json()["code"] == "E_RECORDER_REQUIRED"


async def test_case_latest_sendoff_uses_latest_finalized_version_and_constant_queries(
    db_session, approval_client
):
    seed = await seed_record_version(db_session)
    vid, case_id = seed.version.id, seed.case.id
    at = datetime.now(UTC)
    db_session.add_all(
        [
            SendoffDecision(
                version_id=vid, decision="hold", reason="first", **record_actor(at=at)
            ),
            SendoffDecision(
                version_id=vid,
                decision="approved",
                reason="second",
                **record_actor(at=at),
            ),
        ]
    )
    pending = Version(
        case_id=case_id,
        rule_set_id=seed.rule.id,
        version_no=2,
        current_state="draft",
        is_complete=False,
    )
    db_session.add(pending)
    await db_session.flush()
    db_session.add(
        SendoffDecision(
            version_id=pending.id,
            decision="hold",
            reason="pending ignored",
            **record_actor(),
        )
    )
    await db_session.commit()

    async def measured():
        queries = []

        def observe(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                queries.append(statement)

        event.listen(db_session.bind.sync_engine, "before_cursor_execute", observe)
        try:
            response = await approval_client.get("/api/v1/ui/cases")
        finally:
            event.remove(db_session.bind.sync_engine, "before_cursor_execute", observe)
        assert response.status_code == 200
        return response.json()["cases"], len(queries)

    first, count1 = await measured()
    assert (
        first[0]["latestSendoff"] == "approved"
        and first[0]["latestVersionId"] == vid
        and first[0]["progressStatus"] == "draft_review"
    )
    empty = Case(case_code="no-version")
    db_session.add(empty)
    newer = Version(
        case_id=case_id,
        rule_set_id=seed.rule.id,
        version_no=3,
        current_state="draft",
        is_complete=True,
        finalized_at=at,
    )
    db_session.add(newer)
    await db_session.commit()
    second, count2 = await measured()
    # 案件一覧・最新版（2）＋ F-15 の確認事項・判断・状態イベント（3）。案件数に依らず一定。
    assert count1 == count2 == 5
    assert {row["caseId"] for row in second} == {case_id, empty.id}
    assert all(row["latestSendoff"] is None for row in second)
    assert (
        next(row for row in second if row["caseId"] == case_id)["latestVersionId"]
        == newer.id
    )
