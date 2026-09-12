from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
import asyncio
import httpx
from fastapi import FastAPI
from app.api.agent.endpoints.drafts import router as drafts
from app.api.common.draft_validation import router as validation
from app.api.errors import ApiError, api_error_handler
from app.api.dependencies import get_draft_service
from app.models import AgentRunStep
from app.domain.run_types import RunResult
from app.services.draft_service import DraftService
from app.repositories.run_background import RunBackground
from app.agent.jobs import start_agent_job
from tests.fixtures.run_support import repo, service
from tests.fixtures.draft_data import item, header


async def test_real_api_job_finalize_and_trace_round_trip(session, seeded, tmp_path):
    from app.repositories.run_trace_store import RunTraceStore

    case, _, doc = seeded
    repository = repo(session)
    repository.trace = RunTraceStore(tmp_path)
    run = await service(repository).start(case.id)
    actual = DraftService(repository)
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(drafts, prefix="/api/v1/agent")
    app.include_router(validation, prefix="/api/v1/agent")

    async def provide():
        return actual

    app.dependency_overrides[get_draft_service] = provide
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        base = f"/api/v1/agent/versions/{run.version_id}"

        async def worker():
            assert (await repository.progress(run.id))["version_id"] is None
            session.add(
                AgentRunStep(
                    agent_run_id=run.id,
                    seq=2,
                    tool_name="read_document",
                    args_digest="synthetic",
                    document_id=doc.id,
                    locator="body:1",
                    result_status="ok",
                )
            )
            await session.commit()
            assert (
                await client.post(base + "/header", json=header())
            ).status_code == 201
            response = await client.post(base + "/items", json={"rows": [item()]})
            assert response.status_code == 201
            item_id = response.json()["items"][0]["itemId"]
            for field, value in (("kind", "CSG"), ("qty", "150 MT")):
                response = await client.post(
                    base + "/evidence",
                    json={
                        "itemId": item_id,
                        "field": field,
                        "rawValue": value,
                        "adoptedValue": value,
                        "documentId": doc.id,
                        "locator": "body:1",
                        "quote": value,
                    },
                )
                assert response.status_code == 201
            response = await client.post(
                base + "/inventory",
                json={
                    "entries": [
                        {
                            "documentId": doc.id,
                            "position": "body:1",
                            "seq": 1,
                            "excerpt": "synthetic",
                            "status": "mapped",
                            "itemIds": [item_id],
                        }
                    ]
                },
            )
            assert response.status_code == 201
            response = await client.get(base + "/validation")
            assert response.status_code == 200 and response.json()["violations"] == []
            response = await client.post(base + "/finalize")
            assert (
                response.status_code == 200
                and response.json()["currentState"] == "draft"
            )
            assert (
                await client.post(base + "/items", json={"rows": [item()]})
            ).status_code == 409
            return RunResult("completed", turns=1)

        await start_agent_job(
            run.id,
            work=worker,
            on_finish=lambda result: repository.finish(run.id, result),
            outer_timeout_s=2,
        )
    progress = await repository.progress(run.id)
    assert progress["outcome"] == "success" and progress["version_id"] == run.version_id
    assert len(await repository.steps(run.id)) == 3
    assert (tmp_path / f"{run.id}.jsonl").exists()


async def test_background_gateway_acquires_and_closes_own_session(monkeypatch):
    calls = []

    @asynccontextmanager
    async def sessions():
        calls.append("open")
        try:
            yield object()
        finally:
            calls.append("close")

    finish = AsyncMock()

    class Repository:
        def __init__(self, session, **kwargs):
            calls.append(session)

        async def finish(self, *args):
            await finish(*args)

    monkeypatch.setattr("app.repositories.run_background.RunRepository", Repository)
    result = RunResult("failed")
    await RunBackground(sessions, file_size=lambda d: 10, trace=None).finish(42, result)
    assert calls[0] == "open" and calls[-1] == "close" and len(calls) == 3
    finish.assert_awaited_once_with(42, result)


async def test_lifespan_recovers_before_accepting_jobs_and_stops_on_exit(monkeypatch):
    from app.api import dependencies as deps

    calls = []

    async def db():
        calls.append("open")
        try:
            yield object()
        finally:
            calls.append("close")

    class Repository:
        async def recover_interrupted(self):
            calls.append("recover")

    async def stop():
        calls.append("stop")

    monkeypatch.setattr(deps, "get_db", db)
    monkeypatch.setattr(deps, "make_run_repository", lambda s: Repository())
    monkeypatch.setattr(deps, "stop_jobs", stop)
    async with deps.run_lifespan(None):
        assert calls == ["open", "recover", "close"]
    assert calls[-1] == "stop"


async def test_outer_timeout_does_not_wait_for_uncooperative_cancellation():
    release = asyncio.Event()

    async def worker():
        try:
            await release.wait()
        except asyncio.CancelledError:
            await release.wait()
        return RunResult("completed")

    finish = AsyncMock()
    task = start_agent_job(100, work=worker, on_finish=finish, outer_timeout_s=0.01)
    try:
        await asyncio.wait_for(asyncio.shield(task), 0.1)
        assert finish.await_args.args[0].stop_reason == "outer_timeout"
    finally:
        release.set()
        await asyncio.wait_for(task, 1)
