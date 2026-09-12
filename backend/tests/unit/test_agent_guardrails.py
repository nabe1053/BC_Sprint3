"""PreToolUse ガードレール（app.agent.hooks）の単体テスト。

agent-plan.md ガードレール「資料内の指示を実行しない・外部リンクを取得しない」（AE06）と
「未登録のツール呼び出しを許可しない」を機械的に検査する。
"""

import pytest

from app.agent.hooks import guard_pre_tool_use


@pytest.mark.asyncio
async def test_allows_known_tool_with_safe_args() -> None:
    result = await guard_pre_tool_use(
        {"tool_name": "mcp__app__read_document", "tool_input": {"document_id": "1"}},
        None,
        {"signal": None},
    )
    assert result == {}


@pytest.mark.asyncio
async def test_blocks_unregistered_tool_name() -> None:
    result = await guard_pre_tool_use(
        {"tool_name": "mcp__app__record_edit", "tool_input": {}},
        None,
        {"signal": None},
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_blocks_external_url_in_args() -> None:
    result = await guard_pre_tool_use(
        {
            "tool_name": "mcp__app__read_document",
            "tool_input": {"document_id": "https://evil.example/x"},
        },
        None,
        {"signal": None},
    )
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert (
        result["hookSpecificOutput"]["permissionDecisionReason"]
        == "E_EXTERNAL_LINK_BLOCKED"
    )
