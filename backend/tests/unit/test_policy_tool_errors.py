"""Deterministic tool-error retry counters; model decisions are not evaluated."""
from unittest.mock import AsyncMock, Mock

import pytest

from app.agent import definition
from app.agent.runner import LocalAgentWorker
from app.agent.tools import ToolExecutor
from app.domain.agent_types import ToolCall, ToolReply
from app.domain.run_types import RunContext


@pytest.mark.parametrize(
    "codes,tool,expected,turns",
    [
        (["E_REQUEST_INVALID"] * 3, "read_document", "tool_rejected", 3),
        (
            ["E_REQUEST_INVALID", "E_NOT_FOUND", "E_REQUEST_INVALID"],
            "read_document",
            "draft_not_finalized",
            3,
        ),
        (
            [
                "E_REQUEST_INVALID",
                "E_REQUEST_INVALID",
                None,
                "E_REQUEST_INVALID",
                "E_REQUEST_INVALID",
                None,
            ],
            "read_document",
            "draft_not_finalized",
            6,
        ),
        (
            ["E_REQUEST_INVALID", "E_REQUEST_INVALID", None],
            "validate_draft",
            "draft_not_finalized",
            3,
        ),
        (["E_REQUEST_INVALID"], "finalize_draft", "draft_not_finalized", 1),
    ],
)
async def test_only_consecutive_same_tool_error_codes_stop_the_worker(
    monkeypatch, codes, tool, expected, turns
):
    replies = [
        ToolReply(
            {"code": code} if code else {"violations": []}, is_error=code is not None
        )
        for code in codes
    ]
    received = []

    async def policy(context):
        for index in range(len(replies)):
            reply = yield ToolCall(tool, {"document_id": index + 1})
            received.append(reply)

    monkeypatch.setattr(ToolExecutor, "call", AsyncMock(side_effect=replies))
    outcome = await LocalAgentWorker(Mock(), policy)(
        RunContext(1, 2, 3, 4, definition.default_run_limits())
    )
    assert outcome.stop_reason == "failed" and outcome.detail == expected
    assert outcome.turns == turns
    assert received == (replies[:-1] if expected == "tool_rejected" else replies)


async def test_different_tool_names_do_not_share_the_error_counter(monkeypatch):
    replies = [ToolReply({"code": "E_REQUEST_INVALID"}, True)] * 3

    async def policy(context):
        for tool in ("read_document", "read_email", "read_document"):
            yield ToolCall(tool, {"document_id": 1})

    monkeypatch.setattr(ToolExecutor, "call", AsyncMock(side_effect=replies))
    result = await LocalAgentWorker(Mock(), policy)(
        RunContext(1, 2, 3, 4, definition.default_run_limits())
    )
    assert result.detail == "draft_not_finalized" and result.turns == 3
