"""Thirteen bound local tools. Every call passes the enforced hook and scope checks."""
import asyncio
from contextlib import contextmanager
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
_policy_request = ContextVar("policy_tool_request", default=None)


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

    async def record_denial(self, name, code):
        await self.gateway.record_denial(
            self.context,
            name,
            code,
            digest_args({"tool": name, "code": code}),
            self.closed,
        )

    @classmethod
    def current(cls):
        executor = _executor.get()
        if executor is None:
            raise RuntimeError("A run-scoped executor is required")
        return executor

    @contextmanager
    def bind(self, request=None):
        """SDK tasks inherit this run; optional requests return to the runner first."""
        token = _executor.set(self)
        request_token = _policy_request.set(request)
        try:
            yield
        finally:
            _policy_request.reset(request_token)
            _executor.reset(token)

    async def call(self, name, arguments):
        registered = next((t for t in AGENT_TOOLS if t.name == name), None)
        if registered is None:
            return await self.invoke(name, arguments)
        with self.bind():
            result = await registered.handler(arguments)
            return ToolReply(
                json.loads(result["content"][0]["text"]),
                is_error=result["isError"],
            )

    async def invoke(self, name, arguments):
        step_id = None
        try:
            from app.agent.hooks import guard_pre_tool_use

            if self.closed.is_set():
                raise asyncio.CancelledError
            request = _policy_request.get()
            if request is not None:
                # SDK handler -> this executor -> runner -> call() -> guarded invoke().
                # Only the SDK task inherits request; runner execution clears it.
                return await request(name, arguments)
            registered = name in TOOL_ARGUMENTS
            safe_name = name if registered else "guardrail_denied"
            step_id = await self.gateway.begin_step(
                self.context,
                safe_name,
                digest_args(arguments),
                tool_stage(safe_name),
                self.closed,
            )
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
        except Exception as exc:
            code = (
                exc.code
                if isinstance(exc, DomainError)
                else "E_REQUEST_INVALID"
                if isinstance(exc, ValidationError)
                else "E_INTERNAL"
            )
            if code == "E_INTERNAL":
                logging.getLogger(__name__).error(
                    "Local tool failed (%s)", type(exc).__name__
                )
            if step_id is not None:
                try:
                    await self.gateway.fail_step(
                        self.context, step_id, code, self.closed
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as failure:
                    logging.getLogger(__name__).error(
                        "Local tool failure recording failed (%s)",
                        failure.code
                        if isinstance(failure, DomainError)
                        else type(failure).__name__,
                    )
            data = {"code": code}
            if isinstance(exc, ValidationError):
                data["errors"] = [
                    {"loc": list(error["loc"]), "msg": error["msg"]}
                    for error in exc.errors(
                        include_input=False, include_context=False, include_url=False
                    )
                ]
            return ToolReply(data, is_error=True)


def _registered_tool(name, schema):
    async def bound(arguments):
        executor = ToolExecutor.current()
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

    return tool(
        name, schema.__doc__ or "agent-plan: " + name, schema.model_json_schema()
    )(bound)


AGENT_TOOLS = [
    _registered_tool(name, schema) for name, schema in TOOL_ARGUMENTS.items()
]
ALL_TOOLS = AGENT_TOOLS
AGENT_TOOL_NAMES = ["mcp__app__" + t.name for t in AGENT_TOOLS]
ALLOWED_TOOL_NAMES = AGENT_TOOL_NAMES
# Both policies execute these same run-bound handlers.
agent_server = create_sdk_mcp_server(name="app", version="1.0.0", tools=AGENT_TOOLS)


@tool(
    "ping",
    "Local smoke check only; not registered on the agent server",
    {"message": str},
)
async def ping(args):
    # Foundation smoke tests only. Never add this tool to AGENT_TOOLS.
    return {"content": [{"type": "text", "text": "pong: " + args["message"]}]}
