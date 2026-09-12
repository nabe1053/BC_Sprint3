from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi import FastAPI
from app.api.ui.endpoints.agent_runs import router
from app.api.dependencies_t202 import get_run_service
from app.api.errors import ApiError, api_error_handler
from app.domain.draft_errors import DraftError


@pytest.fixture
def run_service():
    return N(
        start=AsyncMock(
            return_value=N(id=1, version_id=2, started_at=datetime.now(UTC))
        ),
        progress=AsyncMock(
            return_value=dict(
                run_id=1,
                outcome="running",
                stage="reading",
                stage_detail=None,
                turns=0,
                elapsed_sec=1,
                stop_reason=None,
                limits={
                    "maxTurns": 40,
                    "innerTimeoutS": 900,
                    "inactivityTimeoutS": 60,
                    "outerTimeoutS": 960,
                },
                version_id=None,
                is_complete=False,
            )
        ),
        steps=AsyncMock(return_value=[]),
    )


@pytest.fixture
async def run_client(run_service):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    from app.api.agent.router import router as agent_router

    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(router, prefix="/api/v1/ui")

    async def provide():
        return run_service

    app.dependency_overrides[get_run_service] = provide
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


async def test_start_202_and_polling_no_draft_content(run_client, run_service):
    r = await run_client.post(
        "/api/v1/ui/cases/1/agent-runs", json={"acknowledgedCarryOver": True}
    )
    assert r.status_code == 202 and r.json()["versionId"] == 2
    run_service.start.assert_awaited_once_with(
        1, rule_version=None, acknowledged_carry_over=True
    )
    r = await run_client.get("/api/v1/ui/agent-runs/1")
    assert r.status_code == 200 and r.json()["versionId"] is None
    assert r.json()["limits"]["outerTimeoutS"] == 960 and "items" not in r.json()
    r = await run_client.get("/api/v1/ui/agent-runs/1/steps")
    assert r.status_code == 200 and r.json() == {"steps": []}


@pytest.mark.parametrize(
    "code,status",
    [
        ("E_NO_READABLE_DOCUMENT", 400),
        ("E_CARRY_OVER_NOT_ACKNOWLEDGED", 400),
        ("E_RUN_IN_PROGRESS", 409),
        ("E_LIMIT_EXCEEDED", 413),
        ("E_EXTERNAL_SEND_NOT_APPROVED", 503),
        ("E_JOB_START_FAILED", 503),
    ],
)
async def test_start_error_contract(run_client, run_service, code, status):
    run_service.start.side_effect = DraftError(code, "synthetic")
    r = await run_client.post("/api/v1/ui/cases/1/agent-runs", json={})
    assert r.status_code == status and r.json()["code"] == code


async def test_trace_is_ui_only_and_unknown_run_404(run_client, run_service):
    run_service.steps.side_effect = DraftError("E_NOT_FOUND", "synthetic")
    r = await run_client.get("/api/v1/ui/agent-runs/999/steps")
    assert r.status_code == 404
    r = await run_client.post("/api/v1/agent/cases/1/agent-runs", json={})
    assert r.status_code == 404
