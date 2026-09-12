"""Deterministic exception and cancellation boundaries; no DB or model calls."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest

from app.agent import definition, jobs, runner
from app.agent.tools import ToolExecutor
from app.domain.agent_types import ToolCall, ToolReply
from app.domain.draft_errors import DraftError
from app.domain.run_types import RunContext


@pytest.fixture
def context():
    return RunContext(1, 2, 3, 4, definition.default_run_limits())


@pytest.mark.parametrize(
    "failure,code",
    [
        (DraftError("E_RUN_NOT_ACTIVE", "private-source"), "E_RUN_NOT_ACTIVE"),
        (DraftError("E_NOT_FOUND", "private-source"), "E_NOT_FOUND"),
        (RuntimeError("private-source"), "E_INTERNAL"),
    ],
)
async def test_begin_step_failure_becomes_safe_tool_reply(context, failure, code):
    gateway = N(begin_step=AsyncMock(side_effect=failure), fail_step=AsyncMock())
    result = await ToolExecutor(context, gateway).invoke("get_rules", {})
    assert result == ToolReply({"code": code}, is_error=True)
    gateway.fail_step.assert_not_awaited()
    assert "private-source" not in repr(result)


@pytest.mark.parametrize("fail_recording", [False, True])
async def test_unexpected_operation_failure_returns_internal_even_if_recording_fails(
    context, fail_recording, caplog
):
    @asynccontextmanager
    async def operation(*args):
        raise RuntimeError("private-source")
        yield

    gateway = N(
        begin_step=AsyncMock(return_value=8),
        operation=operation,
        fail_step=AsyncMock(
            side_effect=RuntimeError("private-source") if fail_recording else None
        ),
    )
    executor = ToolExecutor(context, gateway)
    result = await executor.invoke("get_rules", {})
    assert result == ToolReply({"code": "E_INTERNAL"}, is_error=True)
    gateway.fail_step.assert_awaited_once_with(
        context, 8, "E_INTERNAL", executor.closed
    )
    assert "private-source" not in caplog.text


async def test_request_callback_failure_is_converted_and_cancel_is_preserved(context):
    gateway = N(begin_step=AsyncMock(), fail_step=AsyncMock())
    executor = ToolExecutor(context, gateway)
    with executor.bind(
        request=AsyncMock(side_effect=DraftError("E_NOT_FOUND", "private-source"))
    ):
        assert await executor.invoke("get_rules", {}) == ToolReply(
            {"code": "E_NOT_FOUND"}, True
        )
    gateway.begin_step.assert_not_awaited()
    gateway.begin_step.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await executor.invoke("get_rules", {})
    gateway.fail_step.assert_not_awaited()


@pytest.mark.parametrize("mode", ["tool_error", "complete", "policy_error"])
async def test_cleanup_cancel_preserves_worker_result_and_turns(
    context, monkeypatch, mode
):
    owner = asyncio.current_task()

    class Policy:
        async def asend(self, reply):
            if mode == "policy_error":
                raise DraftError("E_NOT_FOUND", "private-source")
            return ToolCall("finalize_draft")

        async def aclose(self):
            owner.cancel()
            raise asyncio.CancelledError

    call = AsyncMock(return_value=ToolReply({}))
    if mode == "tool_error":
        call.side_effect = DraftError("E_RUN_NOT_ACTIVE", "private-source")
    monkeypatch.setattr(ToolExecutor, "call", call)
    result = await runner.LocalAgentWorker(N(), lambda context: Policy())(context)
    assert result.turns == (0 if mode == "policy_error" else 1)
    assert (result.stop_reason, result.detail) == (
        ("completed", None) if mode == "complete" else ("failed", "worker_failed")
    )
    assert owner.cancelling() == 0


@pytest.mark.parametrize(
    "cancel_target,detail",
    [("worker", "worker_failed"), ("job", "process_interrupted")],
)
async def test_jobs_distinguish_worker_cancellation_from_job_interruption(
    cancel_target, detail
):
    started = asyncio.Event()
    owner = []

    async def work():
        owner.append(asyncio.current_task())
        started.set()
        await asyncio.Future()

    finish = AsyncMock()
    job = asyncio.create_task(jobs._execute(work, finish, definition.OUTER_TIMEOUT_S))
    await started.wait()
    (owner[0] if cancel_target == "worker" else job).cancel()
    await asyncio.wait_for(job, 1)
    result = finish.await_args.args[0]
    assert result.stop_reason == "failed" and result.detail == detail
    assert result.turns is None


@pytest.mark.parametrize("callback", [runner._consume, jobs._worker_done])
@pytest.mark.parametrize("domain_error", [True, False])
def test_task_diagnostic_logs_only_fixed_code_or_type(caplog, callback, domain_error):
    error = (
        DraftError("E_RUN_NOT_ACTIVE", "private-source")
        if domain_error
        else RuntimeError("private-source")
    )
    task = asyncio.Future()
    task.set_exception(error)
    callback(task)
    assert ("E_RUN_NOT_ACTIVE" if domain_error else "RuntimeError") in caplog.text
    assert "private-source" not in caplog.text
