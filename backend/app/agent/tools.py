"""Thirteen bound local tools. Every call passes the enforced hook and scope checks."""
import asyncio
from contextvars import ContextVar
import hashlib
import json
import logging

from claude_agent_sdk import HookContext, create_sdk_mcp_server, tool
from pydantic import ValidationError

from app.domain.agent_types import TOOL_ARGUMENTS, ToolReply
from app.domain.draft_errors import DraftError
from app.domain.errors import DomainError
from app.services.agent_tool_service import AgentToolService

_executor = ContextVar("local_tool_executor", default=None)


def digest_args(arguments):
    return hashlib.sha256(
        json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def tool_stage(name):
    if name in (
        "list_case_documents",
        "read_document",
        "read_email",
        "search_documents",
        "get_rules",
        "report_unreadable",
    ):
        return "reading"
    if name in ("validate_draft", "finalize_draft"):
        return "self_checking"
    return "extracting"


class ToolExecutor:
    def __init__(self, context, gateway):
        self.context = context
        self.gateway = gateway
        self.closed = asyncio.Event()

    def close(self):
        self.closed.set()

    async def call(self, name, arguments):
        registered = next((t for t in AGENT_TOOLS if t.name == name), None)
        if registered is None:
            return await self.invoke(name, arguments)
        token = _executor.set(self)
        try:
            result = await registered.handler(arguments)
            return ToolReply(
                json.loads(result["content"][0]["text"]),
                is_error=result["isError"],
            )
        finally:
            _executor.reset(token)

    async def invoke(self, name, arguments):
        from app.agent.hooks import guard_pre_tool_use

        if self.closed.is_set():
            raise asyncio.CancelledError
        registered = name in TOOL_ARGUMENTS
        safe_name = name if registered else "guardrail_denied"
        step_id = await self.gateway.begin_step(
            self.context,
            safe_name,
            digest_args(arguments),
            tool_stage(safe_name),
            self.closed,
        )
        try:
            decision = await guard_pre_tool_use(
                {"tool_name": "mcp__app__" + name, "tool_input": arguments},
                None,
                HookContext(signal=None),
            )
            if (
                decision.get("hookSpecificOutput", {}).get("permissionDecision")
                == "deny"
                or not registered
            ):
                reason = decision.get("hookSpecificOutput", {}).get(
                    "permissionDecisionReason"
                )
                code = (
                    reason
                    if reason in {"E_TOOL_NOT_REGISTERED", "E_EXTERNAL_LINK_BLOCKED"}
                    else "E_VALIDATION_FAILED"
                )
                if not registered:
                    code = "E_TOOL_NOT_REGISTERED"
                raise DraftError(code, "ガードレールで拒否しました")
            args = TOOL_ARGUMENTS[name].model_validate(arguments)
            for field in ("case_id", "version_id", "rule_set_id"):
                value = getattr(args, field, None)
                if value is not None and value != getattr(self.context, field):
                    raise DraftError("E_NOT_FOUND", "実行スコープが一致しません")
            if self.closed.is_set():
                raise asyncio.CancelledError
            async with self.gateway.operation(
                self.context, step_id, self.closed
            ) as repository:
                data = await AgentToolService(self.context, repository).execute(
                    name, args
                )
                await repository.record_result(step_id, name, args, data)
            return ToolReply(data)
        except asyncio.CancelledError:
            raise
        except (DomainError, ValidationError) as exc:
            code = exc.code if isinstance(exc, DomainError) else "E_REQUEST_INVALID"
            await self.gateway.fail_step(self.context, step_id, code, self.closed)
            return ToolReply({"code": code}, is_error=True)
        except Exception as exc:
            logging.getLogger(__name__).error(
                "Local tool failed (%s)", type(exc).__name__
            )
            await self.gateway.fail_step(
                self.context, step_id, "E_REQUEST_INVALID", self.closed
            )
            raise


def _registered_tool(name, schema):
    async def bound(arguments):
        executor = _executor.get()
        if executor is None:
            raise RuntimeError("A run-scoped executor is required")
        result = await executor.invoke(name, arguments)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result.data, ensure_ascii=False, default=str),
                }
            ],
            "isError": result.is_error,
        }

    return tool(name, "agent-plan: " + name, schema.model_json_schema())(bound)


AGENT_TOOLS = [
    _registered_tool(name, schema) for name, schema in TOOL_ARGUMENTS.items()
]
ALL_TOOLS = AGENT_TOOLS
AGENT_TOOL_NAMES = ["mcp__app__" + t.name for t in AGENT_TOOLS]
ALLOWED_TOOL_NAMES = AGENT_TOOL_NAMES
# Reserved for approved real-model wiring: ClaudeAgentOptions must receive
# mcp_servers, allowed_tools=ALLOWED_TOOL_NAMES, hooks=build_hooks(), SYSTEM_PROMPT.
# The local worker only invokes these handlers; it never starts the SDK transport.
agent_server = create_sdk_mcp_server(name="app", version="1.0.0", tools=AGENT_TOOLS)


@tool(
    "ping",
    "Local smoke check only; not registered on the agent server",
    {"message": str},
)
async def ping(args):
    # Foundation smoke tests only. Never add this tool to AGENT_TOOLS.
    return {"content": [{"type": "text", "text": "pong: " + args["message"]}]}
