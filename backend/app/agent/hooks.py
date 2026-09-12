"""ガードレール（PreToolUse hook）。

agent-plan.md「ガードレール／してはいけない操作」を、プロンプトのお願いにせず
hooks で強制する（.claude/rules/agent-development.md）。

Foundation では機械的に検査できるものだけを実装する:
- ツール一覧（ALLOWED_TOOL_NAMES）に無いツールの呼び出しを拒否する（多重防御。
  ClaudeAgentOptions.allowed_tools が既に絞っているが、hook 側でも検査する）
- 読取系ツールのスカラ引数に外部URLを含む呼び出しを拒否する
  （資料内の「このリンクを開け」を実行しない・外部リンクを自動取得しない。AE06）

未承認の換算・択一合算・原表記の書き換え・人の記録の代筆・状態の前進・対外送付は、
そもそも該当するツールをエージェントに与えない（tools.py に書き込み用ツールを
登録しない）ことで担保する（agent-plan.md ツール一覧の注記・05-api-ipo.md 7章）。
"""

from typing import Any

from claude_agent_sdk import HookContext, HookMatcher

from app.agent import definition


def _contains_blocked_pattern(value: Any) -> str | None:
    """Only scalar read arguments express access intent; source records are data."""
    if isinstance(value, str):
        for pattern in definition.BLOCKED_ARG_PATTERNS:
            if pattern in value.lower():
                return pattern
        return None
    return None


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


async def guard_pre_tool_use(
    input_data: dict[str, Any], tool_use_id: str | None, context: HookContext
) -> dict[str, Any]:
    """PreToolUse hook 本体。deny の場合は空以外の hookSpecificOutput を返す。"""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {}) or {}

    # 多重防御: allowed_tools に無いツール名は拒否する。
    from app.agent.tools import ALLOWED_TOOL_NAMES  # 遅延 import（循環回避）

    if tool_name not in ALLOWED_TOOL_NAMES:
        return _deny("E_TOOL_NOT_REGISTERED")

    read_tools = {
        "mcp__app__list_case_documents",
        "mcp__app__read_document",
        "mcp__app__read_email",
        "mcp__app__search_documents",
        "mcp__app__get_rules",
    }
    hit = (
        tool_name in read_tools
        and isinstance(tool_input, dict)
        and any(_contains_blocked_pattern(value) for value in tool_input.values())
    )
    if hit:
        return _deny("E_EXTERNAL_LINK_BLOCKED")

    return {}


def build_hooks() -> dict[str, list[HookMatcher]]:
    """Future approved SDK execution passes this to ClaudeAgentOptions(hooks=...).

    The local worker calls the hook directly; this factory does not send anything.
    """
    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[guard_pre_tool_use])],
    }
