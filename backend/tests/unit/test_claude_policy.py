"""Mocked SDK transport contracts; no model or extraction-loop evaluation."""
import asyncio
from contextlib import asynccontextmanager
from functools import partial
from types import SimpleNamespace as N
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from claude_agent_sdk import ResultMessage
from fastapi import FastAPI
from pydantic import SecretStr, ValidationError

from app.agent import definition
from app.agent.runner import LocalAgentWorker
from app.agent.tools import AGENT_TOOLS, ALLOWED_TOOL_NAMES, ToolExecutor, agent_server
from app.api import dependencies
from app.api.errors import ApiError, api_error_handler
from app.api.ui.endpoints.agent_runs import router
from app.core.config import Settings
from app.domain.run_types import RunContext
from app.domain.agent_types import PolicyHeartbeat


@pytest.fixture
def context():
    return RunContext(11, 22, 33, 44, definition.default_run_limits())


def result(subtype="success", **kwargs):
    return ResultMessage(
        subtype=subtype,
        duration_ms=0,
        duration_api_ms=0,
        is_error=kwargs.pop("is_error", False),
        num_turns=0,
        session_id="synthetic",
        **kwargs,
    )


def test_agent_mode_is_explicit_and_defaults_to_local(monkeypatch):
    monkeypatch.delenv("AGENT_MODE", raising=False)
    assert Settings(_env_file=None, DEBUG=False).AGENT_MODE == "local_dummy"
    assert (
        Settings(_env_file=None, DEBUG=False, AGENT_MODE="claude").AGENT_MODE
        == "claude"
    )
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DEBUG=False, AGENT_MODE="unknown")


@pytest.mark.parametrize(
    "mode,key",
    [
        ("local_dummy", None),
        ("local_dummy", "synthetic-key"),
        ("claude", "synthetic-key"),
        ("claude", None),
        ("claude", ""),
    ],
)
async def test_mode_selects_policy_and_persists_model_or_returns_http_503(
    monkeypatch, mode, key
):
    from app.agent.claude_policy import claude_policy
    from app.agent.local_policy import local_dummy_policy
    from datetime import UTC, datetime

    monkeypatch.setattr(dependencies.settings, "AGENT_MODE", mode)
    monkeypatch.setattr(
        dependencies.settings,
        "ANTHROPIC_API_KEY",
        SecretStr(key) if key is not None else None,
    )
    worker = Mock(prepare_finish=AsyncMock())
    worker_factory = Mock(return_value=worker)
    scheduler = Mock()
    repo = N(
        recover_expired=AsyncMock(),
        reserve=AsyncMock(
            return_value=N(
                id=11,
                version_id=33,
                outcome="running",
                started_at=datetime.now(UTC),
            )
        ),
    )
    monkeypatch.setattr(dependencies, "LocalAgentWorker", worker_factory)
    monkeypatch.setattr(dependencies, "RunDispatcher", Mock(return_value=scheduler))
    monkeypatch.setattr(dependencies, "make_run_repository", lambda session: repo)
    service = await dependencies.get_run_service(N(bind=None))
    factory = worker_factory.call_args.kwargs["policy_factory"]
    assert (factory.func if isinstance(factory, partial) else factory) is (
        claude_policy if mode == "claude" else local_dummy_policy
    )
    assert "synthetic-key" not in repr(factory)
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(router, prefix="/api/v1/ui")
    app.dependency_overrides[dependencies.get_run_service] = lambda: service
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/ui/cases/22/agent-runs", json={})
    if mode == "claude" and not key:
        assert response.status_code == 503
        assert response.json()["code"] == "E_EXTERNAL_SEND_NOT_APPROVED"
        assert response.json()["message"] == "実モデルが構成されていません"
        repo.reserve.assert_not_awaited()
        repo.recover_expired.assert_not_awaited()
        scheduler.assert_not_called()
    else:
        assert response.status_code == 202
        assert response.json()["runId"] == 11
        assert repo.reserve.call_args.kwargs["model"] == (
            definition.MODEL_ID if mode == "claude" else definition.DUMMY_MODEL_ID
        )
        scheduler.assert_called_once_with(repo.reserve.return_value)


@pytest.mark.parametrize(
    "terminal,reason,detail",
    [
        (result("error_max_turns"), "max_turns", None),
        (result(terminal_reason="max_turns"), "max_turns", None),
        (result("error_during_execution"), "failed", "model_error"),
        (
            result(is_error=True, result="synthetic-private-error-body"),
            "failed",
            "model_error",
        ),
        (RuntimeError("synthetic-private-error-body"), "failed", "model_error"),
        (result(), "failed", "draft_not_finalized"),
    ],
)
async def test_sdk_terminal_maps_to_run_result_without_error_body(
    monkeypatch, context, caplog, terminal, reason, detail
):
    from app.agent import claude_policy as policy

    async def query(**kwargs):
        if isinstance(terminal, Exception):
            raise terminal
        yield terminal

    monkeypatch.setattr(policy, "query", query)
    outcome = await LocalAgentWorker(
        Mock(), partial(policy.claude_policy, api_key=SecretStr("synthetic-key"))
    )(context)
    assert (outcome.stop_reason, outcome.detail) == (reason, detail)
    assert "synthetic-private-error-body" not in repr(outcome) + caplog.text


async def test_sdk_requires_bound_executor_before_query(monkeypatch, context):
    from app.agent import claude_policy as policy

    query = Mock()
    monkeypatch.setattr(policy, "query", query)
    with pytest.raises(RuntimeError, match="run-scoped"):
        await anext(policy.claude_policy(context, api_key=SecretStr("synthetic-key")))
    query.assert_not_called()


async def test_sdk_terminal_drains_transport_cleanup(monkeypatch, context):
    from app.agent import claude_policy as policy

    drained = asyncio.Event()

    async def query(**kwargs):
        yield result("error_max_turns")
        # SDK releases its transport after yielding the terminal message.
        drained.set()

    monkeypatch.setattr(policy, "query", query)
    outcome = await LocalAgentWorker(
        Mock(), partial(policy.claude_policy, api_key=SecretStr("synthetic-key"))
    )(context)
    assert outcome.stop_reason == "max_turns"
    assert drained.is_set()


@pytest.mark.parametrize(
    "arguments,rejected", [({}, False), ({"rule_set_id": 999}, True)]
)
async def test_sdk_handler_round_trip_uses_existing_executor_and_records_once(
    monkeypatch, context, arguments, rejected
):
    from app.agent import claude_policy as policy

    repository = N(
        get_rules=AsyncMock(return_value={"rule_set_id": context.rule_set_id}),
        record_result=AsyncMock(),
    )

    @asynccontextmanager
    async def operation(*args):
        yield repository

    gateway = N(
        begin_step=AsyncMock(return_value=7), operation=operation, fail_step=AsyncMock()
    )
    executor = ToolExecutor(context, gateway)
    captured = {}

    async def query(*, prompt, options):
        captured["options"] = options
        captured["prompt"] = [message async for message in prompt]
        handler = next(tool for tool in AGENT_TOOLS if tool.name == "get_rules")
        captured["response"] = await handler.handler(arguments)
        yield result()

    monkeypatch.setattr(policy, "query", query)
    stream = policy.claude_policy(context, api_key=SecretStr("synthetic-key"))
    with executor.bind():
        call = await anext(stream)
        gateway.begin_step.assert_not_awaited()
        with executor.bind(
            request=AsyncMock(side_effect=AssertionError("recursive SDK request"))
        ):
            reply = await executor.call(call.name, call.arguments)
        with pytest.raises(StopAsyncIteration):
            signal = await stream.asend(reply)
            while isinstance(signal, PolicyHeartbeat):
                signal = await anext(stream)
    assert captured["response"]["isError"] is rejected
    gateway.begin_step.assert_awaited_once()
    if rejected:
        repository.get_rules.assert_not_awaited()
        repository.record_result.assert_not_awaited()
        gateway.fail_step.assert_awaited_once()
        assert "E_NOT_FOUND" in captured["response"]["content"][0]["text"]
    else:
        assert str(context.rule_set_id) in captured["response"]["content"][0]["text"]
        repository.record_result.assert_awaited_once()
    options = captured["options"]
    assert options.model == definition.MODEL_ID
    assert options.system_prompt == definition.SYSTEM_PROMPT
    assert options.max_turns == definition.MAX_TURNS
    assert options.mcp_servers == {"app": agent_server}
    assert options.allowed_tools == ALLOWED_TOOL_NAMES + ["ToolSearch"]
    assert len(ALLOWED_TOOL_NAMES) == 13
    assert options.tools == []
    assert options.include_partial_messages is True
    assert options.permission_mode == "default"
    assert options.setting_sources == []
    from pathlib import Path

    assert options.cwd and not (Path(options.cwd) / ".claude").exists()
    assert set(options.disallowed_tools) == {
        "Bash",
        "Read",
        "Write",
        "Edit",
        "WebFetch",
        "WebSearch",
        "Glob",
        "Grep",
        "Task",
        "CronCreate",
        "CronDelete",
        "CronList",
        "DesignSync",
        "EnterWorktree",
        "ExitWorktree",
        "ListAgents",
        "Monitor",
        "NotebookEdit",
        "PushNotification",
        "ReportFindings",
        "ScheduleWakeup",
        "SendMessage",
        "Skill",
        "TaskOutput",
        "TaskStop",
        "Workflow",
    }
    assert options.stderr is not None
    assert options.stderr("synthetic-private-stderr") is None
    assert options.env["ANTHROPIC_API_KEY"] == "synthetic-key"
    hook = options.hooks["PreToolUse"][0].hooks[0]
    denied = await hook({"tool_name": "Bash", "tool_input": {}}, None, {"signal": None})
    assert denied["hookSpecificOutput"]["permissionDecision"] == "deny"
    for field in ("case_id", "version_id", "rule_set_id"):
        assert (
            f"{field}={getattr(context, field)}"
            in captured["prompt"][0]["message"]["content"]
        )


async def test_closing_policy_cancels_pending_sdk_handler(monkeypatch, context):
    from app.agent import claude_policy as policy

    stopped = asyncio.Event()

    async def query(**kwargs):
        try:
            await next(
                tool for tool in AGENT_TOOLS if tool.name == "get_rules"
            ).handler({})
            yield result()
        finally:
            stopped.set()

    monkeypatch.setattr(policy, "query", query)
    executor = ToolExecutor(context, Mock())
    with executor.bind():
        stream = policy.claude_policy(context, api_key=SecretStr("synthetic-key"))
        await anext(stream)
        executor.close()
        await stream.aclose()
    assert stopped.is_set()


async def test_sdk_rejects_mismatched_run_binding(monkeypatch, context):
    from app.agent import claude_policy as policy
    from dataclasses import replace

    query = Mock()
    monkeypatch.setattr(policy, "query", query)
    with ToolExecutor(replace(context, case_id=999), Mock()).bind():
        with pytest.raises(RuntimeError, match="matching run-scoped"):
            await anext(
                policy.claude_policy(context, api_key=SecretStr("synthetic-key"))
            )
    query.assert_not_called()


async def test_sdk_tasks_keep_concurrent_run_bindings_separate(monkeypatch, context):
    from app.agent import claude_policy as policy
    from dataclasses import replace

    seen = []

    async def query(**kwargs):
        executor = ToolExecutor.current()
        seen.append(executor.context.case_id)
        await asyncio.sleep(0)
        assert ToolExecutor.current() is executor
        await next(tool for tool in AGENT_TOOLS if tool.name == "get_rules").handler({})
        yield result()

    monkeypatch.setattr(policy, "query", query)

    async def start(run_context):
        executor = ToolExecutor(run_context, Mock())
        with executor.bind():
            stream = policy.claude_policy(
                run_context, api_key=SecretStr("synthetic-key")
            )
            assert (await anext(stream)).name == "get_rules"
            await stream.aclose()

    await asyncio.gather(start(context), start(replace(context, case_id=999)))
    assert sorted(seen) == [context.case_id, 999]
    with pytest.raises(RuntimeError, match="run-scoped"):
        ToolExecutor.current()


async def test_settings_and_partial_keep_api_key_secret():
    configured = Settings(
        _env_file=None, DEBUG=False, ANTHROPIC_API_KEY="synthetic-key"
    )
    assert isinstance(configured.ANTHROPIC_API_KEY, SecretStr)
    assert "synthetic-key" not in repr(configured)


@pytest.mark.parametrize(
    "name,allowed", [("ToolSearch", True), ("Task", False), ("SendMessage", False)]
)
async def test_runtime_tool_search_is_allowed_and_harness_tools_are_blocked(
    name, allowed
):
    from app.agent.hooks import guard_pre_tool_use

    output = await guard_pre_tool_use(
        {"tool_name": name, "tool_input": {"query": "https://synthetic.invalid"}},
        None,
        {"signal": None},
    )
    assert (
        output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
    ) is allowed


async def test_runtime_tool_name_is_preserved_in_denial_metadata():
    from app.agent.claude_policy import _record_denials

    executor = N(record_denial=AsyncMock())
    await _record_denials(
        executor,
        [
            {
                "tool_name": "ToolSearch",
                "tool_input": {"query": "synthetic-private-input"},
            }
        ],
    )
    executor.record_denial.assert_awaited_once_with(
        "ToolSearch", "E_TOOL_NOT_REGISTERED"
    )


@pytest.mark.parametrize(
    "subtype,reason,detail",
    [
        ("error_max_turns", "max_turns", None),
        ("success", "failed", "draft_not_finalized"),
    ],
)
async def test_terminal_result_takes_precedence_over_late_process_error(
    monkeypatch, context, caplog, subtype, reason, detail
):
    from claude_agent_sdk import ProcessError
    from app.agent import claude_policy as policy

    async def query(**kwargs):
        yield result(subtype)
        raise ProcessError(
            "synthetic-private-exit", exit_code=1, stderr="synthetic-private-stderr"
        )

    monkeypatch.setattr(policy, "query", query)
    outcome = await LocalAgentWorker(
        Mock(), partial(policy.claude_policy, api_key=SecretStr("synthetic-key"))
    )(context)
    assert (outcome.stop_reason, outcome.detail) == (reason, detail)
    assert "synthetic-private" not in repr(outcome) + caplog.text
