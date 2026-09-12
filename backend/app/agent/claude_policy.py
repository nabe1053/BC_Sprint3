"""Adapt SDK tool requests to the existing guarded ToolCall/ToolReply stream.

Only the SDK task queues requests. The runner executes them with the same bound
ToolExecutor, retaining its turn limits, completion checks and trace writes.
"""
import asyncio
from contextlib import aclosing
from tempfile import TemporaryDirectory
from time import monotonic

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from app.agent import definition
from app.agent.hooks import build_hooks, guard_pre_tool_use
from app.agent.tools import ALLOWED_TOOL_NAMES, ToolExecutor, agent_server
from app.domain.agent_types import LocalPolicyStop, PolicyHeartbeat, ToolCall


async def _record_denials(executor, denials):
    for denial in denials or []:
        if not isinstance(denial, dict):
            continue
        name = denial.get("tool_name")
        decision = await guard_pre_tool_use(
            {"tool_name": name, "tool_input": denial.get("tool_input", {})},
            None,
            {"signal": None},
        )
        code = decision.get("hookSpecificOutput", {}).get("permissionDecisionReason")
        if code not in ("E_TOOL_NOT_REGISTERED", "E_EXTERNAL_LINK_BLOCKED"):
            code = "E_TOOL_NOT_REGISTERED"
        safe_name = (
            name
            if name in ALLOWED_TOOL_NAMES + definition.DISALLOWED_TOOLS
            else "unregistered"
        )
        await executor.record_denial(safe_name, code)


async def claude_policy(context, *, api_key):
    executor = ToolExecutor.current()
    if executor.context != context:
        raise RuntimeError("A matching run-scoped executor is required")
    requests = asyncio.Queue()
    replies = set()

    async def request(name, arguments):
        reply = asyncio.get_running_loop().create_future()
        replies.add(reply)
        try:
            requests.put_nowait((ToolCall(name, arguments), reply))
            return await reply
        finally:
            replies.discard(reply)

    async def prompt():
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": (
                    f"case_id={context.case_id}, version_id={context.version_id}, "
                    f"rule_set_id={context.rule_set_id} の作成案を、登録ツールで作成してください。"
                ),
            },
            "parent_tool_use_id": None,
            "session_id": "",
        }

    async def consume():
        reason = None
        try:
            with TemporaryDirectory(prefix="agent-run-") as cwd, executor.bind(
                request=request
            ):
                options = ClaudeAgentOptions(
                    model=definition.MODEL_ID,
                    system_prompt=definition.SYSTEM_PROMPT,
                    mcp_servers={"app": agent_server},
                    allowed_tools=ALLOWED_TOOL_NAMES,
                    hooks=build_hooks(),
                    max_turns=definition.MAX_TURNS,
                    permission_mode="default",
                    setting_sources=[],
                    cwd=cwd,
                    disallowed_tools=definition.DISALLOWED_TOOLS,
                    stderr=lambda line: None,
                    env={"ANTHROPIC_API_KEY": api_key.get_secret_value()},
                )
                async with aclosing(
                    query(prompt=prompt(), options=options)
                ) as messages:
                    async for message in messages:
                        requests.put_nowait((PolicyHeartbeat(monotonic()), None))
                        if isinstance(message, ResultMessage):
                            await _record_denials(executor, message.permission_denials)
                            if (
                                message.subtype == "error_max_turns"
                                or message.terminal_reason == "max_turns"
                            ):
                                reason = "max_turns"
                            elif message.is_error or message.subtype != "success":
                                reason = "model_error"
                            # Drain the SDK iterator so its transport/task group
                            # is released in this same task before reporting stop.
        except Exception:
            # SDK diagnostics may contain input text or credentials. Never log them.
            reason = "model_error"
        finally:
            requests.put_nowait((reason, None))

    task = asyncio.create_task(consume())
    # Consume late exceptions even when cancellation cleanup reaches its bound.
    task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
    try:
        while True:
            call, reply = await requests.get()
            if isinstance(call, PolicyHeartbeat):
                yield call
                continue
            if reply is None:
                if call is not None:
                    raise LocalPolicyStop(call)
                return
            response = yield call
            if not reply.done():
                reply.set_result(response)
    finally:
        for reply in replies:
            reply.cancel()
        task.cancel()
        await asyncio.wait({task}, timeout=definition.CANCEL_CLEANUP_S)
