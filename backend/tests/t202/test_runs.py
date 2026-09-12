from datetime import UTC, datetime
from unittest.mock import AsyncMock
import asyncio
import pytest
from sqlalchemy import select, func
from app.models import RuleSet, Version, AgentRun
from app.domain.draft_errors import DraftError
from app.domain.run_types import InputLimits, RunResult
from app.agent.definition import default_run_limits
from app.repositories.run_repository import RunRepository
from app.services.run_service import RunService
from app.agent.jobs import start_agent_job


def repo(session):
    return RunRepository(session, file_size=lambda doc: 10)


def service(repository, scheduler=None, external=False):
    return RunService(
        repository,
        limits=default_run_limits(),
        input_limits=InputLimits(),
        scheduler=scheduler or (lambda run: None),
        external=external,
    )


async def test_start_reserves_same_rule_run_and_version_without_copy(session, seeded):
    case, rule, _ = seeded
    scheduled = []
    run = await service(repo(session), scheduled.append).start(case.id)
    assert run.outcome == "running" and scheduled == [run]
    assert run.rule_set_id == rule.id and run.model == "mock-fixed-v2"
    assert run.impl_version and run.limits["maxTurns"] == 40
    version = await session.get(Version, run.version_id)
    assert (
        version.rule_set_id == rule.id
        and not version.is_complete
        and version.finalized_at is None
    )
    with pytest.raises(DraftError, match="") as e:
        await service(repo(session)).start(case.id)
    assert e.value.code == "E_RUN_IN_PROGRESS"
    assert (
        await session.execute(select(func.count()).select_from(Version))
    ).scalar_one() == 1


async def test_specific_rule_is_used_and_missing_rule_is_404(session, seeded):
    case, _, _ = seeded
    run = await service(repo(session)).start(case.id, rule_version="newer-not-current")
    assert (
        await session.get(RuleSet, run.rule_set_id)
    ).rule_version == "newer-not-current"
    await repo(session).finish(run.id, RunResult("failed"))
    with pytest.raises(DraftError) as e:
        await service(repo(session)).start(case.id, rule_version="missing")
    assert e.value.code == "E_NOT_FOUND"


async def test_no_content_and_external_mode_do_not_create_versions(session, seeded):
    case, _, doc = seeded
    doc.read_status = "unreadable"
    await session.commit()
    with pytest.raises(DraftError) as e:
        await service(repo(session)).start(case.id)
    assert e.value.code == "E_NO_READABLE_DOCUMENT"
    with pytest.raises(DraftError) as e:
        await service(repo(session), external=True).start(case.id)
    assert e.value.code == "E_EXTERNAL_SEND_NOT_APPROVED"
    assert (
        await session.execute(select(func.count()).select_from(Version))
    ).scalar_one() == 0


@pytest.mark.parametrize("actual,allowed", [(20, True), (21, False)])
async def test_input_file_limit_boundary(session, seeded, actual, allowed):
    case, _, _ = seeded
    repository = RunRepository(session, file_size=lambda doc: actual)
    s = RunService(
        repository,
        limits=default_run_limits(),
        input_limits=InputLimits(max_file_bytes=20),
        scheduler=lambda r: None,
    )
    if allowed:
        await s.start(case.id)
    else:
        with pytest.raises(DraftError) as e:
            await s.start(case.id)
        assert e.value.code == "E_LIMIT_EXCEEDED"
        assert e.value.details["actual"] == 21 and e.value.details["limit"] == 20


async def test_unfinalized_worker_completion_is_failed_and_hidden(session, seeded):
    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    await r.finish(run.id, RunResult("completed"))
    view = await r.progress(run.id)
    assert view["outcome"] == "failed" and view["version_id"] is None
    assert view["is_complete"] is False and view["stop_reason"] == "failed"
    assert view["stage"] == "done" and view["elapsed_sec"] >= 0


async def test_success_only_exposes_finalized_version_and_partial_flag(session, seeded):
    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    version = await session.get(Version, run.version_id)
    version.finalized_at = datetime.now(UTC)
    version.is_complete = False
    await session.commit()
    await r.finish(run.id, RunResult("completed", turns=2))
    view = await r.progress(run.id)
    assert view["version_id"] == version.id and view["outcome"] == "success"
    assert view["is_complete"] is False and view["turns"] == 2
    assert len(await r.steps(run.id)) == 2


async def test_schedule_failure_is_terminal(session, seeded):
    def fail(_):
        raise RuntimeError("synthetic")

    case, _, _ = seeded
    r = repo(session)
    with pytest.raises(DraftError) as e:
        await service(r, fail).start(case.id)
    assert e.value.code == "E_JOB_START_FAILED"
    run = (await session.execute(select(AgentRun))).scalar_one()
    assert run.outcome == "failed"


async def test_restart_recovery_marks_orphans_failed(session, seeded):
    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    await r.recover_interrupted()
    view = await r.progress(run.id)
    assert view["outcome"] == "failed" and view["stage_detail"] == "process_interrupted"


@pytest.mark.parametrize(
    "behavior,reason",
    [("success", "completed"), ("error", "failed"), ("hang", "outer_timeout")],
)
async def test_job_dispatcher_has_outer_timeout_and_terminal_callback(behavior, reason):
    async def work():
        if behavior == "error":
            raise RuntimeError("do not persist raw error")
        if behavior == "hang":
            await asyncio.Event().wait()
        return RunResult("completed")

    finish = AsyncMock()
    task = start_agent_job(42, work=work, on_finish=finish, outer_timeout_s=0.01)
    await asyncio.wait_for(task, 1)
    assert finish.await_args.args[0].stop_reason == reason


async def test_question_target_error_has_business_code(session, seeded):
    from app.repositories.draft_repository import DraftRepository
    from app.domain.draft_types import QuestionInput

    case, _, _ = seeded
    run = await service(repo(session)).start(case.id)
    with pytest.raises(DraftError) as e:
        await DraftRepository(session).add_questions(
            run.version_id,
            [
                QuestionInput(
                    question_code="Q",
                    item_id=999,
                    target_field="qty",
                    reason="synthetic",
                )
            ],
        )
    assert e.value.code == "E_TARGET_INVALID"


@pytest.mark.parametrize(
    "table,create,insert,blocks",
    [
        ("item_edits", "version_id INTEGER, undone_at TEXT", "1,NULL", True),
        ("item_edits", "version_id INTEGER, undone_at TEXT", "1,'2026-01-01'", False),
        (
            "confirmations",
            "version_id INTEGER, undone_at TEXT, kind TEXT",
            "1,NULL,'coverage'",
            True,
        ),
        ("question_judgements", "question_id INTEGER", "1", True),
    ],
)
async def test_carryover_checks_real_schema_and_does_not_copy(
    session, seeded, table, create, insert, blocks
):
    from sqlalchemy import text
    from app.models.drafts import Question

    case, _, _ = seeded
    r = repo(session)
    first = await service(r).start(case.id)
    session.add(
        Question(
            id=1,
            version_id=first.version_id,
            question_code="Q",
            target_field="qty",
            reason="test",
        )
    )
    await session.commit()
    await r.finish(first.id, RunResult("failed"))
    await session.execute(text(f"CREATE TABLE {table} ({create})"))
    await session.execute(text(f"INSERT INTO {table} VALUES ({insert})"))
    await session.commit()
    if blocks:
        with pytest.raises(DraftError) as e:
            await service(r).start(case.id)
        assert e.value.code == "E_CARRY_OVER_NOT_ACKNOWLEDGED"
    second = await service(r).start(case.id, acknowledged_carry_over=True)
    version = await session.get(Version, second.version_id)
    assert version.prev_version_id == first.version_id and version.version_no == 2
    assert (
        await session.execute(
            select(func.count())
            .select_from(Question)
            .where(Question.version_id == version.id)
        )
    ).scalar_one() == 0


async def test_trace_failure_cannot_roll_back_terminal_state(session, seeded):
    class BrokenTrace:
        def sync(self, *args):
            raise OSError("synthetic")

    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    r.trace = BrokenTrace()
    await r.finish(run.id, RunResult("failed"))
    assert (await r.progress(run.id))["outcome"] == "failed"


async def test_trace_file_has_safe_metadata_and_matches_db_steps(
    session, seeded, tmp_path
):
    import json
    from app.repositories.run_trace_store import RunTraceStore

    case, _, _ = seeded
    r = RunRepository(session, file_size=lambda d: 10, trace=RunTraceStore(tmp_path))
    run = await service(r).start(case.id)
    await r.finish(run.id, RunResult("failed"))
    lines = [
        json.loads(line)
        for line in (tmp_path / f"{run.id}.jsonl").read_text().splitlines()
    ]
    assert [e["seq"] for e in lines] == [s.seq for s in await r.steps(run.id)]
    assert lines[-1]["stopReason"] == "failed"
    assert all("Synthetic" not in str(e) for e in lines)


async def test_job_cancel_records_terminal_result():
    work_started = asyncio.Event()

    async def work():
        work_started.set()
        await asyncio.Event().wait()

    finish = AsyncMock()
    task = start_agent_job(99, work=work, on_finish=finish, outer_timeout_s=60)
    await work_started.wait()
    task.cancel()
    await task
    assert finish.await_args.args[0].stop_reason == "failed"


async def test_terminal_run_rejects_late_worker_writes(session, seeded):
    from app.domain.draft_types import HeaderInput
    from test_write_api import header

    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    await r.finish(run.id, RunResult("outer_timeout"))
    with pytest.raises(DraftError) as e:
        await r.save_header(run.version_id, HeaderInput.model_validate(header()))
    assert e.value.code == "E_RUN_NOT_ACTIVE"


async def test_overdue_run_recovers_on_next_start_without_restart(session, seeded):
    from datetime import timedelta

    case, _, _ = seeded
    r = repo(session)
    run = await service(r).start(case.id)
    run.started_at = datetime.now(UTC) - timedelta(seconds=1000)
    await session.commit()
    old_id = run.id
    await service(r).start(case.id)
    view = await service(r).progress(old_id)
    assert view["outcome"] == "stopped" and view["stop_reason"] == "outer_timeout"


async def test_finish_retries_transient_failure():
    finish = AsyncMock(side_effect=[OSError("synthetic"), None])

    async def work():
        return RunResult("failed")

    await start_agent_job(123, work=work, on_finish=finish, outer_timeout_s=1)
    assert finish.await_count == 2


async def test_committed_trace_is_idempotent_when_finish_commit_retries(
    session, seeded, tmp_path, monkeypatch
):
    import json
    from app.repositories.run_trace_store import RunTraceStore

    case, _, _ = seeded
    repository = RunRepository(
        session, file_size=lambda d: 10, trace=RunTraceStore(tmp_path)
    )
    run = await service(repository).start(case.id)
    run_id = run.id
    commit = session.commit
    attempts = 0

    async def fail_once():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("synthetic commit failure")
        await commit()

    monkeypatch.setattr(session, "commit", fail_once)

    async def work():
        return RunResult("failed")

    await start_agent_job(
        run_id,
        work=work,
        on_finish=lambda result: repository.finish(run_id, result),
        outer_timeout_s=1,
    )
    events = [
        json.loads(line)
        for line in (tmp_path / f"{run_id}.jsonl").read_text().splitlines()
    ]
    assert [event["seq"] for event in events] == [
        step.seq for step in await repository.steps(run_id)
    ]
    await repository.finish(run_id, RunResult("failed"))
    assert len((tmp_path / f"{run_id}.jsonl").read_text().splitlines()) == 2


async def test_startup_rebuilds_committed_trace_after_process_interruption(
    session, seeded, tmp_path
):
    import json
    from app.repositories.run_trace_store import RunTraceStore

    case, _, _ = seeded
    repository = repo(session)
    run = await service(repository).start(case.id)
    run_id = run.id
    await repository.finish(run_id, RunResult("failed"))
    repository.trace = RunTraceStore(tmp_path)
    await repository.recover_interrupted()
    events = [
        json.loads(line)
        for line in (tmp_path / f"{run_id}.jsonl").read_text().splitlines()
    ]
    assert [event["seq"] for event in events] == [1, 2]
    assert events[-1]["stopReason"] == "failed"


@pytest.mark.parametrize("outcome", ["running", "failed"])
async def test_legacy_trace_is_preserved_during_poll_and_startup(
    session, seeded, tmp_path, outcome
):
    from app.repositories.run_trace_store import RunTraceStore

    case, _, _ = seeded
    repository = repo(session)
    run = await service(repository).start(case.id)
    run_id = run.id
    for step in await repository.steps(run_id):
        step.trace_event = None
    run.outcome = outcome
    await session.commit()
    path = tmp_path / f"{run_id}.jsonl"
    original = '{"type":"legacy","synthetic":true}\n'
    path.write_text(original)
    repository.trace = RunTraceStore(tmp_path)
    await repository.recover_interrupted()
    await repository.progress(run_id)
    assert path.read_text() == original
