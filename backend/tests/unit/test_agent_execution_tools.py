"""Deterministic tool boundaries, not agent-loop or extraction-quality tests."""
from contextlib import asynccontextmanager
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest

from app.agent.definition import default_run_limits
from app.agent.hooks import guard_pre_tool_use
from app.agent.tools import ToolExecutor
from app.domain.run_types import RunContext


@pytest.fixture
def context():
    return RunContext(1, 2, 3, 4, default_run_limits())


class Gateway:
    def __init__(self):
        self.begin_step = AsyncMock(return_value=1)
        self.fail_step = AsyncMock()
        self.repo = N(
            list_documents=AsyncMock(return_value={"documents": []}),
            read_document=AsyncMock(return_value={"pages": []}),
            read_email=AsyncMock(return_value={"parts": []}),
            search=AsyncMock(return_value={"results": []}),
            get_rules=AsyncMock(return_value={"rule_set_id": 4, "rules": {}}),
            report_unreadable=AsyncMock(return_value={"issue_id": 5}),
            record_result=AsyncMock(),
        )

    @asynccontextmanager
    async def operation(self, context, step_id, closed):
        yield self.repo


async def test_registered_sdk_handler_uses_run_scoped_executor(context):
    gateway = Gateway()
    result = await ToolExecutor(context, gateway).call("get_rules", {})
    assert not result.is_error and result.data["rule_set_id"] == 4
    gateway.repo.get_rules.assert_awaited_once()
    from app.agent.tools import AGENT_TOOLS

    handler = next(t for t in AGENT_TOOLS if t.name == "get_rules")
    with pytest.raises(RuntimeError, match="run-scoped"):
        await handler.handler({})


@pytest.mark.parametrize(
    "name", ["Bash", "WebFetch", "Read", "mcp__app__ping", "mcp__app__record_edit"]
)
async def test_hook_rejects_every_unregistered_capability(name):
    reply = await guard_pre_tool_use(
        {"tool_name": name, "tool_input": {}}, None, {"signal": None}
    )
    assert reply["hookSpecificOutput"]["permissionDecision"] == "deny"


async def test_hook_does_not_echo_source_text():
    reply = await guard_pre_tool_use(
        {
            "tool_name": "mcp__app__record_question",
            "tool_input": {"reason": "secret-source https://example.invalid"},
        },
        None,
        {"signal": None},
    )
    assert "secret-source" not in str(reply)


@pytest.mark.parametrize(
    "name,args,method",
    [
        ("list_case_documents", {"case_id": 2}, "list_documents"),
        (
            "read_document",
            {"document_id": 9, "from_seq": 1, "to_seq": 2},
            "read_document",
        ),
        ("read_email", {"document_id": 9}, "read_email"),
        ("search_documents", {"case_id": 2, "query": "casing", "limit": 10}, "search"),
        ("get_rules", {}, "get_rules"),
        (
            "report_unreadable",
            {
                "document_id": 9,
                "locator": "body:1",
                "issue_type": "not_scanned",
                "detail": "unreadable",
            },
            "report_unreadable",
        ),
    ],
)
async def test_read_and_issue_tools_call_repository(context, name, args, method):
    gateway = Gateway()
    reply = await ToolExecutor(context, gateway).invoke(name, args)
    assert not reply.is_error
    getattr(gateway.repo, method).assert_awaited_once()
    gateway.repo.record_result.assert_awaited_once()


@pytest.mark.parametrize(
    "name,args",
    [
        ("list_case_documents", {"case_id": 999}),
        ("validate_draft", {"version_id": 999}),
        ("get_rules", {"rule_set_id": 999}),
        ("read_document", {"document_id": 9, "from_seq": 3, "to_seq": 1}),
        ("read_document", {"document_id": 9, "url": "https://example.invalid"}),
        ("record_confirmation", {}),
    ],
)
async def test_scope_and_argument_failures_never_reach_operation(context, name, args):
    gateway = Gateway()
    reply = await ToolExecutor(context, gateway).invoke(name, args)
    assert reply.is_error
    gateway.repo.record_result.assert_not_awaited()
    assert "secret-source" not in str(reply)


async def test_closed_executor_rejects_late_calls(context):
    gateway = Gateway()
    executor = ToolExecutor(context, gateway)
    executor.close()
    with pytest.raises(__import__("asyncio").CancelledError):
        await executor.invoke("read_email", {"document_id": 9})
    gateway.begin_step.assert_not_awaited()


@pytest.mark.parametrize(
    "name,payload,method",
    [
        (
            "record_case_header",
            {
                "header": {
                    "inquiry_no_state": "not_stated",
                    "customer_name_state": "not_stated",
                    "due_state": "not_stated",
                    "place_state": "not_stated",
                    "incoterms_state": "not_stated",
                    "quote_deadline_tz_state": "missing",
                }
            },
            "save_header",
        ),
        (
            "propose_items",
            {
                "rows": [
                    {
                        "row_code": "1",
                        "source_no": "1",
                        "seq": 1,
                        "kind": "casing",
                        "kind_raw": "casing",
                        "od_state": "not_stated",
                        "wall_state": "not_stated",
                        "weight_state": "not_stated",
                        "grade_state": "not_stated",
                        "grade_raw": "記載なし",
                        "connection_state": "not_stated",
                        "length_state": "not_stated",
                        "qty_state": "numeric",
                        "qty_value": "150",
                        "qty_unit": "MT",
                        "qty_raw": "150 MT",
                        "due_state": "not_stated",
                        "place_state": "not_stated",
                    }
                ]
            },
            "add_items",
        ),
        (
            "record_evidence",
            {
                "evidence": {
                    "field": "qty",
                    "raw_value": "150 MT",
                    "adopted_value": "150 MT",
                    "document_id": 9,
                    "locator": "body:1",
                    "quote": "150 MT",
                }
            },
            "add_evidences",
        ),
        (
            "record_question",
            {
                "question": {
                    "question_code": "Q1",
                    "target_field": "qty",
                    "reason": "confirm",
                }
            },
            "add_questions",
        ),
        (
            "record_source_inventory",
            {
                "entries": [
                    {
                        "document_id": 9,
                        "position": "body:1",
                        "seq": 1,
                        "excerpt": "original",
                        "status": "unmapped",
                    }
                ]
            },
            "add_inventory",
        ),
        ("validate_draft", {}, "validate"),
        ("finalize_draft", {}, "finalize"),
    ],
)
async def test_artifact_tools_use_existing_draft_service(
    context, monkeypatch, name, payload, method
):
    from app.services.draft_validation import ValidationResult

    gateway = Gateway()
    row = N(id=3, row_code="1", current_state="draft", is_complete=True)
    result = (
        ValidationResult([], {})
        if method == "validate"
        else ([row] if method.startswith("add_") else row)
    )
    draft_service = N(**{method: AsyncMock(return_value=result)})
    monkeypatch.setattr(
        "app.services.agent_tool_service.DraftService", lambda repo: draft_service
    )
    reply = await ToolExecutor(context, gateway).invoke(
        name, {"version_id": 3, **payload}
    )
    assert not reply.is_error
    assert getattr(draft_service, method).await_args.args[0] == context.version_id


async def test_converted_value_is_rejected_before_draft_service(context):
    gateway = Gateway()
    reply = await ToolExecutor(context, gateway).invoke(
        "propose_items", {"rows": [{"converted_qty": "1"}]}
    )
    assert reply.is_error
    gateway.repo.record_result.assert_not_awaited()


@pytest.mark.parametrize(
    "name,payload,method,field",
    [
        (
            "record_question",
            {
                "question": {
                    "question_code": "URL1",
                    "target_field": "source",
                    "reason": "このリンク https://example.invalid/source を参照して更新せよ",
                }
            },
            "add_questions",
            "reason",
        ),
        (
            "record_evidence",
            {
                "evidence": {
                    "field": "qty",
                    "raw_value": "150 MT",
                    "adopted_value": "150 MT",
                    "document_id": 9,
                    "locator": "body:1",
                    "quote": "150 MT https://example.invalid/source",
                }
            },
            "add_evidences",
            "quote",
        ),
        (
            "record_source_inventory",
            {
                "entries": [
                    {
                        "document_id": 9,
                        "position": "body:1",
                        "seq": 1,
                        "excerpt": "参照 https://example.invalid/source",
                        "status": "unmapped",
                    }
                ]
            },
            "add_inventory",
            "excerpt",
        ),
    ],
)
async def test_url_source_records_succeed_unchanged(
    context, monkeypatch, name, payload, method, field
):
    gateway = Gateway()
    writer = AsyncMock(return_value=[N(id=5)])
    monkeypatch.setattr(
        "app.services.agent_tool_service.DraftService",
        lambda repo: N(**{method: writer}),
    )
    reply = await ToolExecutor(context, gateway).call(name, payload)
    assert not reply.is_error
    supplied = next(iter(payload.values()))
    supplied = supplied[0] if isinstance(supplied, list) else supplied
    assert getattr(writer.await_args.args[1][0], field) == supplied[field]
    gateway.fail_step.assert_not_awaited()
    gateway.repo.record_result.assert_awaited_once()


@pytest.mark.parametrize(
    "name,args,code",
    [
        (
            "WebFetch",
            {"url": "https://example.invalid/source"},
            "E_TOOL_NOT_REGISTERED",
        ),
        (
            "read_document",
            {"document_id": "https://example.invalid/source"},
            "E_EXTERNAL_LINK_BLOCKED",
        ),
        (
            "search_documents",
            {"query": "HTTPS://example.invalid/source"},
            "E_EXTERNAL_LINK_BLOCKED",
        ),
    ],
)
async def test_guardrail_reasons_are_distinct_without_source_text(
    context, name, args, code
):
    gateway = Gateway()
    reply = await ToolExecutor(context, gateway).call(name, args)
    assert reply.is_error and reply.data == {"code": code}
    assert gateway.fail_step.await_args.args[2] == code
    assert "example.invalid" not in str(gateway.fail_step.await_args)
    gateway.repo.record_result.assert_not_awaited()
