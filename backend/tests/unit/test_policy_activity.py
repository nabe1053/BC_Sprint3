"""Fake-clock SDK liveness contracts, not model decision-quality tests."""
import asyncio
from functools import partial
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, Mock

import pytest
from claude_agent_sdk import SystemMessage
from pydantic import SecretStr

from app.agent import claude_policy, definition, runner
from app.agent.tools import AGENT_TOOLS, ToolExecutor
from app.domain.agent_types import ToolReply
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


@pytest.mark.parametrize("messages,stalls", [(4, False), (1, True)])
async def test_sdk_message_activity_controls_only_inactivity_clock(
    monkeypatch, messages, stalls
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
