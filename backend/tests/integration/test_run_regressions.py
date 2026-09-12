"""RV-015 regressions, using only synthetic data and isolated dependencies."""
import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from app.agent import definition, jobs
from app.domain.draft_errors import DraftError
from app.domain.run_types import RunResult
from app.repositories.run_repository import RunRepository
from app.services.exceptions import DomainError
from tests.fixtures.run_support import service


async def test_definition_defaults_reach_reserved_run(session, seeded, monkeypatch):
    monkeypatch.setattr(definition, "MAX_TURNS", 7)
    monkeypatch.setattr(definition, "DUMMY_MODEL_ID", "synthetic-model")
    from app.api.dependencies import get_run_service

    # Exercise the composition factory without starting jobs or opening another DB.
    monkeypatch.setattr(
        "app.api.dependencies.RunDispatcher", lambda *a, **kw: lambda r: None
    )
    monkeypatch.setattr(
        "app.api.dependencies.make_run_repository",
        lambda s: RunRepository(s, file_size=lambda d: 1),
    )
    session.bind = None
    s = await get_run_service(session)
    run = await s.start(seeded[0].id)
    assert run.model == "synthetic-model"
    assert run.limits["maxTurns"] == 7


async def test_progress_never_writes_locks_or_exports(session, seeded, monkeypatch):
    trace = Mock()
    r = RunRepository(session, file_size=lambda d: 1, trace=trace)
    run = await service(r).start(seeded[0].id)
    trace.reset_mock()
    execute = session.execute

    async def read_only(statement):
        assert getattr(statement, "_for_update_arg", None) is None
        assert statement.is_select
        return await execute(statement)

    monkeypatch.setattr(session, "execute", read_only)
    monkeypatch.setattr(
        session, "commit", AsyncMock(side_effect=AssertionError("GET commit"))
    )
    monkeypatch.setattr(
        r, "recover_expired", AsyncMock(side_effect=AssertionError("GET recovery"))
    )
    assert (await service(r).progress(run.id))["outcome"] == "running"
    trace.sync.assert_not_called()


async def test_running_trace_failure_does_not_terminate_worker(session, seeded):
    r = RunRepository(session, file_size=lambda d: 1)
    run = await service(r).start(seeded[0].id)
    r.trace = Mock(sync=Mock(side_effect=OSError("synthetic")))
    await r._export_or_fail(run.id)
    assert run.outcome == "running" and run.ended_at is None
    assert run.stage_detail == "trace_write_failed"
    assert (await r.steps(run.id))[-1].tool_name == "job_trace_failure"


async def test_missing_original_allows_previously_extracted_content(session, seeded):
    r = RunRepository(session, file_size=lambda d: None)
    assert (await service(r).start(seeded[0].id)).outcome == "running"


def test_draft_error_uses_shared_domain_hierarchy():
    assert isinstance(DraftError("E_RUN_NOT_ACTIVE", "synthetic"), DomainError)


async def test_worker_diagnostics_are_safe_and_persistence_retries_back_off(
    caplog, monkeypatch
):
    delays = []

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(jobs.asyncio, "sleep", sleep)

    async def work():
        raise ValueError("synthetic-secret-body")

    finish = AsyncMock(
        side_effect=[
            OSError("synthetic-secret-body"),
            OSError("synthetic-secret-body"),
            None,
        ]
    )
    await jobs.start_agent_job(901, work=work, on_finish=finish, outer_timeout_s=1)
    assert "ValueError" in caplog.text and "OSError" in caplog.text
    assert "synthetic-secret-body" not in caplog.text
    assert len(delays) == 2 and 0 < delays[0] < delays[1]


async def test_cancel_cleanup_gets_bounded_grace_before_terminal_callback():
    cleaned = asyncio.Event()

    async def work():
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0.005)
            cleaned.set()

    async def finish(result):
        assert result == RunResult("outer_timeout")
        assert cleaned.is_set()

    await jobs.start_agent_job(902, work=work, on_finish=finish, outer_timeout_s=0.01)


def test_validation_code_comes_from_type_not_message_or_field():
    from fastapi.exceptions import RequestValidationError
    from types import SimpleNamespace
    from app.api.common.route_errors import invalid_request

    exc = RequestValidationError(
        [
            {
                "type": "E_BASIS_REQUIRED",
                "msg": "changed message",
                "loc": ("body", "renamed"),
            }
        ]
    )
    result = invalid_request(
        exc, SimpleNamespace(url=SimpleNamespace(path="/inventory"))
    )
    assert result.code == "E_BASIS_REQUIRED"


def test_schema_errors_carry_business_codes():
    from pydantic import ValidationError
    from app.api.common.schemas.drafts import ItemRequest
    from tests.fixtures.draft_data import item

    data = item()
    data.pop("odState")
    with pytest.raises(ValidationError) as exc:
        ItemRequest.model_validate(data)
    assert exc.value.errors()[0]["type"] == "E_STATE_REQUIRED"


def test_input_size_uses_shared_storage_validation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from app.repositories.document_storage import DocumentStorageGateway
    from app.repositories.run_input_files import RunInputFiles

    path = tmp_path / "1" / "synthetic.txt"
    path.parent.mkdir()
    path.write_text("safe")
    resolver = Mock(return_value=None)
    monkeypatch.setattr(DocumentStorageGateway, "resolve_readable_path", resolver)
    assert (
        RunInputFiles(str(tmp_path)).size(
            SimpleNamespace(case_id=1, storage_path=str(path))
        )
        is None
    )
    resolver.assert_called_once_with(str(path))


async def test_current_rule_alias_selects_marked_current(session, seeded):
    r = RunRepository(session, file_size=lambda d: 1)
    run = await service(r).start(seeded[0].id, rule_version="current")
    assert run.rule_set_id == seeded[1].id


def test_nested_end_business_error_keeps_typed_code():
    from pydantic import ValidationError
    from app.api.common.schemas.drafts import ItemRequest
    from tests.fixtures.draft_data import item

    with pytest.raises(ValidationError) as exc:
        ItemRequest.model_validate(
            item() | {"ends": [{"side": "end_a", "odValue": "1"}]}
        )
    assert exc.value.errors()[0]["type"] == "E_UNIT_REQUIRED"


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("managed", 4),
        ("relative", 4),
        ("sibling", None),
        ("escape", None),
        ("missing", None),
    ],
)
def test_input_size_respects_case_and_symlink_scope(
    tmp_path, monkeypatch, kind, expected
):
    from types import SimpleNamespace
    from app.repositories.run_input_files import RunInputFiles

    root = tmp_path / "storage"
    (root / "1").mkdir(parents=True)
    (root / "2").mkdir()
    path = root / ("2" if kind == "sibling" else "1") / "file.txt"
    if kind == "escape":
        outside = tmp_path / "outside.txt"
        outside.write_text("safe")
        path.symlink_to(outside)
    elif kind != "missing":
        path.write_text("safe")
    monkeypatch.chdir(tmp_path)
    stored = str(path.relative_to(tmp_path)) if kind == "relative" else str(path)
    assert (
        RunInputFiles("storage").size(SimpleNamespace(case_id=1, storage_path=stored))
        == expected
    )


async def test_noncooperative_terminal_callback_cannot_remove_time_bound(monkeypatch):
    release = asyncio.Event()
    calls = []
    monkeypatch.setattr(jobs, "FINISH_TIMEOUT_S", 0.005)

    async def work():
        return RunResult("failed")

    async def finish(result):
        calls.append(asyncio.current_task())
        try:
            await release.wait()
        except asyncio.CancelledError:
            await release.wait()

    task = jobs.start_agent_job(903, work=work, on_finish=finish, outer_timeout_s=1)
    try:
        with pytest.raises(RuntimeError, match="Terminal state could not be persisted"):
            await asyncio.wait_for(asyncio.shield(task), 0.8)
        assert len(calls) == 3
    finally:
        release.set()
        await asyncio.gather(*calls)


def test_run_endpoints_are_in_ui_only_route_contract():
    from tests.fixtures.route_contract import UI_ONLY_SEGMENTS

    # The generic path tests are collected once from unit/test_api_path_separation.py.
    assert "agent-runs" in UI_ONLY_SEGMENTS
