"""Fake-clock SDK liveness contracts, not model decision-quality tests."""
import asyncio
from functools import partial
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, Mock

import pytest
from claude_agent_sdk import StreamEvent, SystemMessage
from pydantic import SecretStr

from app.agent import claude_policy, definition, runner
from app.agent.tools import AGENT_TOOLS, ToolExecutor
from app.domain.agent_types import ToolCall, ToolReply
from app.domain.run_types import RunContext


class Clock:
    def __init__(self):
        self.now = 0
        self.sleepers = []

    async def sleep(self, delay):
        future = asyncio.get_running_loop().create_future()
        self.sleepers.append((self.now + delay, future))
        await future

    async def wait(self, tasks, *, timeout):
        # Run ready callbacks before moving virtual time to the next event.
        for _ in range(20):
            await asyncio.sleep(0)
            done = {task for task in tasks if task.done()}
            if done:
                return done, tasks - done
        end = self.now + timeout
        if self.sleepers and self.sleepers[0][0] <= end:
            self.now, future = self.sleepers.pop(0)
            future.set_result(None)
            return await self.wait(tasks, timeout=end - self.now)
        self.now = end
        return set(), tasks


@pytest.mark.parametrize(
    "reason,messages",
    [("inactivity_timeout", 0), ("inactivity_timeout", 2), ("inner_timeout", 4)],
)
async def test_timeout_diagnostics_capture_last_heartbeat_and_run_total(
    monkeypatch, reason, messages
):
    from dataclasses import replace
    from app.domain.agent_types import PolicyHeartbeat

    clock = Clock()
    monkeypatch.setattr(runner, "monotonic", lambda: clock.now)
    monkeypatch.setattr(
        runner,
        "asyncio",
        N(
            create_task=asyncio.create_task,
            wait=clock.wait,
            CancelledError=asyncio.CancelledError,
        ),
    )
    monkeypatch.setattr(ToolExecutor, "call", AsyncMock(return_value=ToolReply({})))
    limits = definition.default_run_limits()
    spacing = limits.inactivity_timeout_s / 3
    if reason == "inner_timeout":
        limits = replace(limits, inner_timeout_s=spacing * 4.5)

    async def policy(context):
        for i in range(messages):
            await clock.sleep(spacing)
            yield PolicyHeartbeat(clock.now)
            if i == 0:
                # A tool operation must not reset the run-wide diagnostics.
                yield ToolCall("get_rules")
        await asyncio.Future()

    outcome = await runner.LocalAgentWorker(Mock(), policy)(
        RunContext(1, 2, 3, 4, limits)
    )
    assert outcome.stop_reason == reason
    assert outcome.heartbeat_diagnostics.heartbeats == messages
    expected = spacing / 2 if reason == "inner_timeout" else limits.inactivity_timeout_s
    assert outcome.heartbeat_diagnostics.since_last_heartbeat_s == expected


@pytest.mark.parametrize(
    "messages,stalls,partial_messages",
    [(4, False, False), (1, True, False), (4, False, True)],
)
async def test_sdk_message_activity_controls_only_inactivity_clock(
    monkeypatch, messages, stalls, partial_messages
):
    clock = Clock()
    monkeypatch.setattr(runner, "monotonic", lambda: clock.now)
    monkeypatch.setattr(claude_policy, "monotonic", lambda: clock.now, raising=False)
    monkeypatch.setattr(
        runner,
        "asyncio",
        N(
            create_task=asyncio.create_task,
            wait=clock.wait,
            CancelledError=asyncio.CancelledError,
        ),
    )
    limits = definition.default_run_limits()
    spacing = limits.inactivity_timeout_s / 3

    async def query(**kwargs):
        for _ in range(messages):
            await clock.sleep(spacing)
            if partial_messages:
                assert kwargs["options"].include_partial_messages is True
                yield StreamEvent(
                    uuid="synthetic",
                    session_id="synthetic",
                    event={
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "synthetic"},
                    },
                )
            else:
                yield SystemMessage(subtype="synthetic", data={})
        if stalls:
            await asyncio.Future()
        else:
            await next(
                tool for tool in AGENT_TOOLS if tool.name == "get_rules"
            ).handler({})

    monkeypatch.setattr(claude_policy, "query", query)
    invoke = AsyncMock(return_value=ToolReply({}))
    monkeypatch.setattr(ToolExecutor, "call", invoke)
    outcome = await runner.LocalAgentWorker(
        Mock(),
        partial(
            claude_policy.claude_policy,
            api_key=SecretStr("synthetic-key"),
        ),
    )(RunContext(1, 2, 3, 4, limits))
    if stalls:
        assert outcome.stop_reason == "inactivity_timeout"
        assert clock.now == spacing + limits.inactivity_timeout_s
        assert outcome.turns == 0
        invoke.assert_not_awaited()
    else:
        assert (
            outcome.stop_reason == "failed" and outcome.detail == "draft_not_finalized"
        )
        assert clock.now == spacing * messages > limits.inactivity_timeout_s
        assert outcome.turns == 1
        invoke.assert_awaited_once_with("get_rules", {})


async def test_timeout_result_survives_cleanup_cancellation_and_keeps_turns(
    monkeypatch
):
    clock = Clock()
    owner = asyncio.current_task()
    monkeypatch.setattr(runner, "monotonic", lambda: clock.now)
    monkeypatch.setattr(
        runner,
        "asyncio",
        N(
            create_task=asyncio.create_task,
            wait=clock.wait,
            CancelledError=asyncio.CancelledError,
            current_task=asyncio.current_task,
        ),
    )
    monkeypatch.setattr(ToolExecutor, "call", AsyncMock(return_value=ToolReply({})))

    class Policy:
        def __init__(self):
            self.turn = 0

        async def asend(self, reply):
            if self.turn < 6:
                self.turn += 1
                return ToolCall("read_document", {"document_id": self.turn})
            await asyncio.Future()

        async def aclose(self):
            # Reproduce SDK cleanup cancelling its caller's surrounding scope.
            owner.cancel()
            raise asyncio.CancelledError

    outcome = await runner.LocalAgentWorker(Mock(), lambda context: Policy())(
        RunContext(1, 2, 3, 4, definition.default_run_limits())
    )
    assert outcome.stop_reason == "inactivity_timeout" and outcome.turns == 6
    assert owner.cancelling() == 0
