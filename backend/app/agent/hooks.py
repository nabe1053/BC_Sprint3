"""ガードレール（PreToolUse hook）。

agent-plan.md「ガードレール／してはいけない操作」を、プロンプトのお願いにせず
hooks で強制する（.claude/rules/agent-development.md）。

Foundation では機械的に検査できるものだけを実装する:
- ツール一覧（ALLOWED_TOOL_NAMES）に無いツールの呼び出しを拒否する（多重防御。
  ClaudeAgentOptions.allowed_tools が既に絞っているが、hook 側でも検査する）
- 引数に外部URL（http:// / https://）を含む呼び出しを拒否する
  （資料内の「このリンクを開け」を実行しない・外部リンクを自動取得しない。AE06）

未承認の換算・択一合算・原表記の書き換え・人の記録の代筆・状態の前進・対外送付は、
そもそも該当するツールをエージェントに与えない（tools.py に書き込み用ツールを
登録しない）ことで担保する（agent-plan.md ツール一覧の注記・05-api-ipo.md 7章）。
"""

import json
from typing import Any

from claude_agent_sdk import HookContext, HookMatcher

from app.agent import definition


def _contains_blocked_pattern(value: Any) -> str | None:
    """値（ネストした dict/list を含む）に禁止パターンが含まれるか調べる。"""
    if isinstance(value, str):
        for pattern in definition.BLOCKED_ARG_PATTERNS:
            if pattern in value:
                return pattern
        return None
    if isinstance(value, dict):
        for v in value.values():
            hit = _contains_blocked_pattern(v)
            if hit:
                return hit
        return None
    if isinstance(value, list):
        for v in value:
            hit = _contains_blocked_pattern(v)
            if hit:
                return hit
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

    if tool_name.startswith("mcp__app__") and tool_name not in ALLOWED_TOOL_NAMES:
        return _deny(f"未登録のツール呼び出し: {tool_name}")

    hit = _contains_blocked_pattern(tool_input)
    if hit:
        return _deny(
            f"引数に外部リンク（{hit}...）が含まれる。資料内の指示でリンクを取得・実行しない（N02・AE06）: "
            f"{json.dumps(tool_input, ensure_ascii=False)[:200]}"
        )

    return {}


def build_hooks() -> dict[str, list[HookMatcher]]:
    """ClaudeAgentOptions(hooks=...) に渡す辞書を組み立てる。"""
    return {
        "PreToolUse": [HookMatcher(matcher=None, hooks=[guard_pre_tool_use])],
    }
