"""Actual HTTP approval contracts with the Service boundary mocked."""
from types import SimpleNamespace as N
from datetime import datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from app.api.errors import DOMAIN_ERROR_STATUS_BY_CODE, ApiError, api_error_handler
from app.domain.draft_errors import DraftError
from tests.fixtures.approval_data import AT, approval_material

ERRORS = [
    ("E_STAFF_CHECK_INCOMPLETE", 409),
    ("E_COVERAGE_NOT_RECORDED", 409),
    ("E_STATE_ORDER", 409),
    ("E_STATE_ROLLBACK_FORBIDDEN", 422),
    ("E_NO_BOUNCE_COMMENT", 409),
    ("E_SENDOFF_REASON_REQUIRED", 400),
    ("E_COMMENT_REQUIRED", 400),
]


@pytest.mark.parametrize("code,status", ERRORS)
def test_approval_error_status_registry(code, status):
    assert DOMAIN_ERROR_STATUS_BY_CODE[code] == status


@pytest.fixture
async def approval_http():
    from app.api.dependencies import get_approval_service, get_record_service
    from app.core.dependencies import get_case_service
    from app.api.ui.router import router
    from app.api.agent.router import router as agent_router

    rows = approval_material()
    service = N(
        transition=AsyncMock(return_value=rows.state),
        comment=AsyncMock(return_value=N(**{**vars(rows.comment), "bounce_id": None})),
        bounce=AsyncMock(return_value=rows.bounce),
        decide_sendoff=AsyncMock(return_value=rows.sendoff),
        list_records=AsyncMock(return_value=rows.records),
        list_versions_with_records=AsyncMock(return_value=[rows.material]),
    )
    old = N(list_versions=AsyncMock())
    cases = N(list_cases=AsyncMock(return_value=[]))
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.dependency_overrides[get_approval_service] = lambda: service
    app.dependency_overrides[get_record_service] = lambda: old
    app.dependency_overrides[get_case_service] = lambda: cases
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield N(client=client, service=service, rows=rows, old=old, cases=cases)


@pytest.mark.parametrize(
    "path,payload,status,code",
    [
        (
            "state-events",
            {"toState": "draft", "recordedBy": "人"},
            422,
            "E_STATE_ROLLBACK_FORBIDDEN",
        ),
        ("state-events", {"recordedBy": "人"}, 422, "E_STATE_ROLLBACK_FORBIDDEN"),
        (
            "state-events",
            {"toState": "draft", "recordedBy": " "},
            400,
            "E_RECORDER_REQUIRED",
        ),
        (
            "bounce-comments",
            {"itemId": 9, "comment": "", "recordedBy": "人"},
            400,
            "E_COMMENT_REQUIRED",
        ),
        (
            "sendoff-decisions",
            {"decision": "hold", "reason": "", "recordedBy": "人"},
            400,
            "E_SENDOFF_REASON_REQUIRED",
        ),
        (
            "sendoff-decisions",
            {"decision": "approved", "reason": " ", "recordedBy": "人"},
            400,
            "E_SENDOFF_REASON_REQUIRED",
        ),
        (
            "state-events",
            {"to_state": "staff_checked", "recorded_by": "人"},
            422,
            "E_REQUEST_INVALID",
        ),
        (
            "state-events",
            {
                "toState": "staff_checked",
                "recordedBy": "人",
                "recordedAt": "2026-09-14T00:00:00Z",
            },
            400,
            "E_REQUEST_INVALID",
        ),
        (
            "bounces",
            {"recordedBy": "人", "reason": "input reason"},
            400,
            "E_REQUEST_INVALID",
        ),
    ],
)
async def test_invalid_input_never_calls_service(
    approval_http, path, payload, status, code
):
    response = await approval_http.client.post(
        "/api/v1/ui/versions/7/" + path, json=payload
    )
    assert response.status_code == status and response.json()["code"] == code
    for method in ("transition", "comment", "bounce", "decide_sendoff"):
        getattr(approval_http.service, method).assert_not_awaited()


@pytest.mark.parametrize(
    "path,method,payload,keys",
    [
        (
            "state-events",
            "transition",
            {"toState": "staff_checked", "recordedBy": "人"},
            {
                "stateEventId",
                "fromState",
                "toState",
                "recordedBy",
                "recordedAt",
                "unresolvedCount",
            },
        ),
        (
            "bounce-comments",
            "comment",
            {"itemId": 9, "comment": "確認", "recordedBy": "人"},
            {
                "bounceCommentId",
                "itemId",
                "bounceId",
                "comment",
                "recordedBy",
                "recordedAt",
            },
        ),
        (
            "bounces",
            "bounce",
            {"recordedBy": "人"},
            {"bounceId", "reason", "recordedBy", "recordedAt"},
        ),
        (
            "sendoff-decisions",
            "decide_sendoff",
            {"decision": "approved", "reason": "可", "recordedBy": "人"},
            {"sendoffDecisionId", "decision", "reason", "recordedBy", "recordedAt"},
        ),
    ],
)
async def test_success_has_exact_keys_and_no_client_timestamp(
    approval_http, path, method, payload, keys
):
    response = await approval_http.client.post(
        "/api/v1/ui/versions/7/" + path, json=payload
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == keys
    assert datetime.fromisoformat(body["recordedAt"]) == AT
    args = getattr(approval_http.service, method).await_args.args
    assert args[0] == 7 and "recorded_at" not in args[1]
    if method == "bounce":
        assert args[1] == {"recorded_by": "人"}
    if method == "comment":
        assert body["bounceId"] is None


@pytest.mark.parametrize("reason", [None, ""])
async def test_undecided_accepts_absent_or_empty_reason(approval_http, reason):
    payload = {"decision": "undecided", "recordedBy": "人"}
    if reason is not None:
        payload["reason"] = reason
    response = await approval_http.client.post(
        "/api/v1/ui/versions/7/sendoff-decisions", json=payload
    )
    assert response.status_code == 201
    assert approval_http.service.decide_sendoff.await_args.args[1] == {
        "decision": "undecided",
        "recorded_by": "人",
        "reason": None,
    }


@pytest.mark.parametrize("code,status", ERRORS)
async def test_domain_errors_preserve_details(approval_http, code, status):
    details = {
        "unmatchedItemIds": [1, 9],
        "unmatchedRowCodes": ["R1", "R9"],
        "coverageRecorded": False,
    }
    approval_http.service.transition.side_effect = DraftError(code, "fixed", details)
    response = await approval_http.client.post(
        "/api/v1/ui/versions/7/state-events",
        json={"toState": "staff_checked", "recordedBy": "人"},
    )
    assert response.status_code == status
    assert response.json() == {"code": code, "message": "fixed", "details": details}


def assert_camel(value):
    if isinstance(value, dict):
        assert all("_" not in key for key in value)
        for child in value.values():
            assert_camel(child)
    elif isinstance(value, list):
        for child in value:
            assert_camel(child)


async def test_history_exact_collections_cancellations_and_nested_comments(
    approval_http
):
    response = await approval_http.client.get("/api/v1/ui/versions/7/records")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "edits",
        "confirmations",
        "judgements",
        "stateEvents",
        "bounces",
        "unlinkedComments",
        "sendoffDecisions",
    }
    assert set(data["confirmations"][0]) == {
        "confirmationId",
        "kind",
        "itemId",
        "recordedBy",
        "recordedAt",
        "undoneAt",
        "undoneBy",
    }
    expected_keys = {
        "edits": {
            "editId",
            "itemId",
            "field",
            "oldValue",
            "oldState",
            "newValue",
            "newState",
            "reason",
            "recordedBy",
            "recordedAt",
            "undoneAt",
            "undoneBy",
        },
        "judgements": {
            "judgementId",
            "questionId",
            "status",
            "resolution",
            "note",
            "recordedBy",
            "recordedAt",
        },
        "stateEvents": {
            "stateEventId",
            "fromState",
            "toState",
            "recordedBy",
            "recordedAt",
            "unresolvedCount",
        },
        "bounces": {"bounceId", "reason", "recordedBy", "recordedAt", "comments"},
        "unlinkedComments": {
            "bounceCommentId",
            "itemId",
            "bounceId",
            "comment",
            "recordedBy",
            "recordedAt",
        },
        "sendoffDecisions": {
            "sendoffDecisionId",
            "decision",
            "reason",
            "recordedBy",
            "recordedAt",
        },
    }
    for key, expected in expected_keys.items():
        assert set(data[key][0]) == expected
    assert set(data["bounces"][0]["comments"][0]) == expected_keys["unlinkedComments"]
    assert data["confirmations"][0]["undoneBy"] == "取消者"
    assert (
        data["bounces"][0]["comments"][0]["bounceId"]
        == data["bounces"][0]["bounceId"]
        == 31
    )
    assert data["unlinkedComments"][0]["bounceId"] is None
    assert data["bounces"][0]["comments"][0]["comment"] == "確認 <script>"
    assert_camel(data)
    assert "private" not in response.text and "versionId" not in response.text
    approval_http.service.list_records.assert_awaited_once_with(7)


async def test_empty_records_returns_all_seven_arrays(approval_http):
    approval_http.service.list_records.return_value = {
        key: [] for key in approval_http.rows.records
    }
    response = await approval_http.client.get("/api/v1/ui/versions/7/records")
    assert response.status_code == 200
    assert response.json() == {
        key: []
        for key in [
            "edits",
            "confirmations",
            "judgements",
            "stateEvents",
            "bounces",
            "unlinkedComments",
            "sendoffDecisions",
        ]
    }


@pytest.mark.parametrize("populated", [False, True])
async def test_version_list_uses_approval_service_and_required_fields(
    approval_http, populated
):
    material = approval_http.rows.material
    if not populated:
        for key in ("latest_state_event", "latest_bounce", "latest_sendoff_decision"):
            material[key] = None
        material.update(bounced=False, needs_recheck=False, elapsed_sec=None)
    response = await approval_http.client.get("/api/v1/ui/cases/3/versions")
    assert response.status_code == 200
    row = response.json()["versions"][0]
    assert set(row) == {
        "versionId",
        "versionNo",
        "currentState",
        "finalizedAt",
        "isComplete",
        "createdAt",
        "unresolvedCount",
        "carryOver",
        "latestStateEvent",
        "latestBounce",
        "latestSendoff",
        "bounced",
        "needsRecheck",
        "elapsedSec",
    }
    # N06: 生成所要は版ごとに表示する。Decimal は丸めずに文字列、未記録は null。
    assert row["elapsedSec"] == ("631.5" if populated else None)
    assert row["carryOver"] == {
        "editCount": 1,
        "rowMatchConfirmed": 1,
        "rowMatchTotal": 1,
        "coverageRecorded": True,
        "judgementCount": 1,
    }
    assert row["bounced"] is populated and row["needsRecheck"] is populated
    for key in ("latestStateEvent", "latestBounce", "latestSendoff"):
        assert (row[key] is not None) is populated
    if populated:
        assert row["latestBounce"]["comments"] == []
    approval_http.service.list_versions_with_records.assert_awaited_once_with(3)
    approval_http.old.list_versions.assert_not_awaited()
    assert_camel(row)


async def test_agent_write_is_absent_and_nonpositive_version_is_rejected(approval_http):
    for prefix, version, status in [("agent", 7, 404), ("ui", 0, 422), ("ui", -1, 422)]:
        response = await approval_http.client.post(
            f"/api/v1/{prefix}/versions/{version}/state-events",
            json={"toState": "staff_checked", "recordedBy": "人"},
        )
        assert response.status_code == status
    approval_http.service.transition.assert_not_awaited()


@pytest.mark.parametrize("decision", [None, "approved"])
async def test_case_list_includes_latest_sendoff(approval_http, decision):
    case = N(id=3, case_code="C", customer_name=None, title=None, created_at=AT)
    approval_http.cases.list_cases.return_value = [(case, "staff_checked", 7, decision)]
    response = await approval_http.client.get("/api/v1/ui/cases")
    assert response.status_code == 200
    assert response.json()["cases"][0] == {
        "caseId": 3,
        "caseCode": "C",
        "customerName": None,
        "title": None,
        "createdAt": AT.isoformat().replace("+00:00", "Z"),
        "progressStatus": "staff_checked",
        "latestVersionId": 7,
        "latestSendoff": decision,
    }


def test_openapi_version_extension_and_case_sendoff_are_required_nullable_contracts():
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    required = {
        "unresolvedCount",
        "carryOver",
        "latestStateEvent",
        "latestBounce",
        "latestSendoff",
        "bounced",
        "needsRecheck",
    }
    assert required <= set(schemas["VersionListItem"]["required"])
    assert "latestSendoff" in schemas["CaseListItem"]["required"]
    for key in ("latestStateEvent", "latestBounce", "latestSendoff"):
        assert {"type": "null"} in schemas["VersionListItem"]["properties"][key][
            "anyOf"
        ]
    assert {"type": "null"} in schemas["CaseListItem"]["properties"]["latestSendoff"][
        "anyOf"
    ]
    assert set(schemas["CarryOverResponse"]["required"]) == {
        "editCount",
        "rowMatchConfirmed",
        "rowMatchTotal",
        "coverageRecorded",
        "judgementCount",
    }
