"""Adapt SDK tool requests to the existing guarded ToolCall/ToolReply stream.

Only the SDK task queues requests. The runner executes them with the same bound
ToolExecutor, retaining its turn limits, completion checks and trace writes.
"""
import asyncio
from contextlib import aclosing

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from app.agent import definition
from app.agent.hooks import build_hooks
from app.agent.tools import ALLOWED_TOOL_NAMES, ToolExecutor, agent_server
from app.domain.agent_types import LocalPolicyStop, ToolCall


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
            with executor.bind(request=request):
                options = ClaudeAgentOptions(
                    model=definition.MODEL_ID,
                    system_prompt=definition.SYSTEM_PROMPT,
                    mcp_servers={"app": agent_server},
                    allowed_tools=ALLOWED_TOOL_NAMES,
                    hooks=build_hooks(),
                    max_turns=definition.MAX_TURNS,
                    permission_mode="default",
                    env={"ANTHROPIC_API_KEY": api_key},
                )
                async with aclosing(
                    query(prompt=prompt(), options=options)
                ) as messages:
                    async for message in messages:
                        if isinstance(message, ResultMessage):
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
