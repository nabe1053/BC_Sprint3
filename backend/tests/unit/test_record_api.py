"""HTTP contracts for finalized-version reads and human records; services mocked."""
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI

from app.api.errors import ApiError, api_error_handler
from app.domain.draft_errors import DraftError
from app.domain.draft_types import ItemInput
from app.domain.record_types import CurrentItem
from tests.fixtures.draft_data import item_data

AT = datetime(2026, 9, 13, tzinfo=UTC)
EDIT = {
    "itemId": 6,
    "field": "grade",
    "newValue": "L80",
    "newState": "stated",
    "reason": "訂正",
    "recordedBy": "担当者",
}


@pytest.fixture
async def record_http():
    from app.api.dependencies import get_record_service
    from app.api.ui.router import router
    from app.api.agent.router import router as agent_router
    from app.core.dependencies import get_case_service

    row = N(
        id=10,
        item_id=6,
        field="grade",
        old_value="K55",
        old_state="stated",
        new_value="L80",
        new_state="stated",
        reason="訂正",
        recorded_by="担当者",
        recorded_at=AT,
        undone_at=AT,
        undone_by="取消者",
    )
    values = ItemInput.model_validate(item_data()).model_dump(exclude={"ends"})
    values.update(
        id=6,
        grade="L80",
        grade_raw="K55",
        od_value=Decimal("4.500"),
        od_unit="in",
        od_raw='4-1/2"',
        od_state="stated",
        version_id=1,
        created_at=AT,
        private_column="private",
    )
    version = N(
        id=1,
        version_no=1,
        current_state="draft",
        finalized_at=AT,
        is_complete=True,
        created_at=AT,
    )
    judgement = N(
        id=20,
        question_id=30,
        status="judged",
        resolution="unresolved",
        note=None,
        recorded_by="担当者",
        recorded_at=AT,
    )
    question = N(
        id=30,
        question_code="Q1",
        item_id=6,
        target_field="grade",
        reason="確認",
        candidates=None,
        category="alternative",
    )
    service = N(
        edit=AsyncMock(
            return_value=[row, N(**{**vars(row), "id": 11, "field": "qty_unit"})]
        ),
        undo_edit=AsyncMock(return_value=row),
        confirm=AsyncMock(
            return_value=N(
                id=12, kind="row_match", item_id=6, recorded_by="担当者", recorded_at=AT
            )
        ),
        undo_confirmation=AsyncMock(
            return_value=N(id=12, undone_at=AT, undone_by="取消者")
        ),
        judge=AsyncMock(return_value=judgement),
        list_items_with_edits=AsyncMock(return_value=[CurrentItem(values, [row])]),
        list_questions_with_latest=AsyncMock(
            return_value=[
                {"question": question, "latest": judgement},
                {"question": N(**{**vars(question), "id": 31}), "latest": None},
            ]
        ),
        list_item_evidence=AsyncMock(
            return_value=[
                N(
                    id=13,
                    field="grade",
                    raw_value="K55",
                    adopted_value="K55",
                    document_id=4,
                    locator="body:1",
                    quote="K55",
                    applied_condition=None,
                    conversion_note=None,
                    change_reason=None,
                    prior_value=None,
                )
            ]
        ),
        list_versions=AsyncMock(return_value=[version]),
        summary=AsyncMock(
            return_value={
                "version_id": 1,
                "case_id": 2,
                "version_no": 1,
                "current_state": "draft",
                "is_complete": True,
                "finalized_at": AT,
                "case_header": None,
                "coverage_confirmed": False,
                **{
                    key: 0
                    for key in (
                        "item_count",
                        "question_item_count",
                        "tba_item_count",
                        "choice_group_count",
                        "matched_count",
                        "edit_count",
                        "edited_item_count",
                        "unresolved_count",
                    )
                },
            }
        ),
    )
    cases = N(
        list_cases=AsyncMock(
            return_value=[
                (
                    N(
                        id=2,
                        case_code="C",
                        customer_name=None,
                        title=None,
                        created_at=AT,
                    ),
                    "draft_review",
                    1,
                )
            ]
        )
    )
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.dependency_overrides[get_record_service] = lambda: service
    app.dependency_overrides[get_case_service] = lambda: cases
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client, service


async def test_edit_201_quantity_pair_and_server_timestamp(record_http):
    client, service = record_http
    payload = {
        **EDIT,
        "field": "qty_value",
        "newValue": "200",
        "newState": "numeric",
        "qtyUnit": "本",
    }
    response = await client.post("/api/v1/ui/versions/1/edits", json=payload)
    assert response.status_code == 201
    assert len(response.json()["edits"]) == 2
    assert (
        datetime.fromisoformat(response.json()["edits"][0]["recordedAt"]).utcoffset()
        is not None
    )
    args = service.edit.await_args.args
    assert args[0] == 1 and args[1]["qty_unit"] == "本"
    assert "recorded_at" not in args[1]


async def test_current_items_preserve_raw_history_and_decimal_strings(record_http):
    client, _ = record_http
    response = await client.get("/api/v1/ui/versions/1/items")
    assert response.status_code == 200
    row = response.json()["items"][0]
    assert row["itemId"] == 6 and row["grade"] == "L80" and row["gradeRaw"] == "K55"
    assert row["odRaw"] == '4-1/2"' and row["odValue"] == "4.500"
    assert row["history"][0]["undoneBy"] == "取消者"
    assert not {"versionId", "createdAt", "privateColumn", "ends"} & row.keys()


async def test_questions_keep_judged_unresolved_and_null_latest(record_http):
    client, _ = record_http
    response = await client.get("/api/v1/ui/versions/1/questions")
    assert response.status_code == 200
    questions = response.json()["questions"]
    assert (
        questions[0]["latest"]["status"] == "judged"
        and questions[0]["latest"]["resolution"] == "unresolved"
    )
    assert questions[1]["latest"] is None


@pytest.mark.parametrize(
    "path,payload,key,status",
    [
        ("edits/10/undo", {"recordedBy": "取消者"}, "editId", 200),
        (
            "confirmations",
            {"kind": "row_match", "itemId": 6, "recordedBy": "担当者"},
            "confirmationId",
            201,
        ),
        ("confirmations/12/undo", {"recordedBy": "取消者"}, "confirmationId", 200),
        (
            "questions/30/judgements",
            {
                "status": "judged",
                "resolution": "unresolved",
                "recordedBy": "担当者",
                "note": "",
            },
            "judgementId",
            201,
        ),
    ],
)
async def test_other_record_routes_and_blank_judgement_note(
    record_http, path, payload, key, status
):
    client, service = record_http
    response = await client.post("/api/v1/ui/versions/1/" + path, json=payload)
    assert response.status_code == status and key in response.json()
    if path.endswith("/undo"):
        assert response.json()["undoneBy"] == "取消者"
    if path.endswith("judgements"):
        assert service.judge.await_args.args[2]["note"] is None


@pytest.mark.parametrize(
    "change,status,code",
    [
        ({"reason": ""}, 400, "E_REASON_REQUIRED"),
        ({"recordedBy": None}, 400, "E_RECORDER_REQUIRED"),
        ({"newValue": None, "newState": None}, 400, "E_STATE_VALUE_CONFLICT"),
        (
            {"field": "qty_value", "newValue": "200", "newState": "numeric"},
            400,
            "E_QTY_UNIT_REQUIRED",
        ),
        ({"field": "grade_raw"}, 422, "E_FIELD_NOT_EDITABLE"),
        ({"recordedAt": "2026-09-13T00:00:00Z"}, 400, "E_REQUEST_INVALID"),
        ({"recorded_by": "person"}, 422, "E_REQUEST_INVALID"),
    ],
)
async def test_input_business_and_structural_error_contracts(
    record_http, change, status, code
):
    client, service = record_http
    payload = {**EDIT, **change}
    if change.get("recordedBy", "present") is None:
        del payload["recordedBy"]
    response = await client.post("/api/v1/ui/versions/1/edits", json=payload)
    assert response.status_code == status and response.json()["code"] == code
    assert set(response.json()) == {"code", "message", "details"}
    service.edit.assert_not_awaited()


async def test_row_confirmation_requires_target(record_http):
    client, service = record_http
    response = await client.post(
        "/api/v1/ui/versions/1/confirmations",
        json={"kind": "row_match", "recordedBy": "person"},
    )
    assert response.status_code == 400 and response.json()["code"] == "E_TARGET_INVALID"
    service.confirm.assert_not_awaited()


@pytest.mark.parametrize(
    "code,status",
    [
        ("E_NOT_FOUND", 404),
        ("E_ALREADY_UNDONE", 409),
        ("E_ALREADY_CONFIRMED", 409),
        ("E_TARGET_INVALID", 400),
    ],
)
async def test_service_error_status_and_camel_details(record_http, code, status):
    client, service = record_http
    service.edit.side_effect = DraftError(code, "synthetic", {"itemId": 6})
    response = await client.post("/api/v1/ui/versions/1/edits", json=EDIT)
    assert response.status_code == status and response.json()["code"] == code
    assert response.json()["details"] == {"itemId": 6}


async def test_version_summary_list_evidence_and_case_navigation(record_http):
    client, service = record_http
    response = await client.get("/api/v1/ui/cases/2/versions")
    assert (
        response.status_code == 200 and response.json()["versions"][0]["versionId"] == 1
    )
    service.list_versions.assert_awaited_once_with(2)
    response = await client.get("/api/v1/ui/versions/1")
    assert response.status_code == 200 and response.json()["caseHeader"] is None
    assert response.json()["counts"]["editedItemCount"] == 0
    response = await client.get("/api/v1/ui/versions/1/items/6/evidence")
    assert response.status_code == 200 and response.json()["itemId"] == 6
    assert response.json()["evidences"][0]["documentId"] == 4
    response = await client.get("/api/v1/ui/cases")
    assert response.status_code == 200
    assert response.json()["cases"][0]["latestVersionId"] == 1
    assert response.json()["cases"][0]["progressStatus"] == "draft_review"


async def test_agent_namespace_cannot_write_human_records(record_http):
    client, service = record_http
    response = await client.post("/api/v1/agent/versions/1/edits", json=EDIT)
    assert response.status_code == 404
    service.edit.assert_not_awaited()


@pytest.mark.parametrize("matched", [False, True])
async def test_items_expose_only_active_row_match_metadata(record_http, matched):
    client, service = record_http
    current = service.list_items_with_edits.return_value[0]
    service.list_items_with_edits.return_value = [
        N(
            values=current.values,
            history=current.history,
            row_match=N(
                confirmation_id=12,
                recorded_by="確認担当",
                recorded_at=AT,
                private="hidden",
            )
            if matched
            else None,
        )
    ]
    response = await client.get("/api/v1/ui/versions/1/items")
    assert response.status_code == 200
    match = response.json()["items"][0]["rowMatch"]
    if matched:
        assert set(match) == {"confirmationId", "recordedBy", "recordedAt"}
        assert match["confirmationId"] == 12 and match["recordedBy"] == "確認担当"
        assert datetime.fromisoformat(match["recordedAt"]) == AT
    else:
        assert match is None
