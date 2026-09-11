"""エージェント実行ループ。

タイムアウトの責務分担:
- 内側（このファイル）: INNER_TIMEOUT_S（実行全体）と INACTIVITY_TIMEOUT_S（無応答=ハング検知）。
  発火したらトレースに stop_reason を記録して整然と終了する。agent-plan.md の「強制停止」に対応。
- 外側（jobs.py）: OUTER_TIMEOUT_S。内側が機能しなかった場合（SDK サブプロセスの
  ハング・キャンセル不能など）の最後の砦。発火 = 内側の異常であり、バグとして扱う。

直接呼ばない: 起動は必ず jobs.start_agent_job() 経由（バックグラウンド実行 + 外側タイムアウト）。

ガードレール: PreToolUse hook（app.agent.hooks）を必ず適用する。ツール一覧は
app.agent.tools.ALLOWED_TOOL_NAMES（agent-plan.md の13点 + 疎通テスト用 ping）に限定する。
"""

import asyncio
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from app.agent import definition
from app.agent.hooks import build_hooks
from app.agent.tools import ALLOWED_TOOL_NAMES, agent_server
from app.agent.trace import TraceRecorder, digest_args


@dataclass
class AgentRunResult:
    run_id: str
    stop_reason: str  # completed / failed / max_turns / inner_timeout / inactivity_timeout / ...
    output: str | None = None
    num_turns: int | None = None
    cost_usd: float | None = None


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=definition.SYSTEM_PROMPT,
        mcp_servers={"app": agent_server},
        allowed_tools=ALLOWED_TOOL_NAMES,
        max_turns=definition.MAX_TURNS,
        hooks=build_hooks(),
    )


async def run_agent(
    prompt: str, *, scenario: str | None = None, trace: TraceRecorder | None = None
) -> AgentRunResult:
    """エージェントを1回実行し、全メッセージをトレースに記録する。

    trace は jobs.py が run_id を先に確定させるために注入する（省略時は内部で生成）。
    直接 await しない — 起動は jobs.start_agent_job() 経由（外側タイムアウト込み）。
    """
    trace = trace or TraceRecorder(scenario=scenario)
    trace.record_input(prompt)
    result = AgentRunResult(run_id=trace.run_id, stop_reason="failed")

    # 強制停止条件: 同一ツール・同一引数の連続呼び出し（agent-plan.md「強制停止」）。
    last_calls: list[tuple[str, str]] = []

    try:
        # 内側タイムアウト: 実行全体の上限
        async with asyncio.timeout(definition.INNER_TIMEOUT_S):
            stream = query(prompt=prompt, options=_build_options()).__aiter__()
            while True:
                try:
                    # ハング検知: メッセージ間の無応答が INACTIVITY_TIMEOUT_S を超えたら停止
                    message = await asyncio.wait_for(
                        stream.__anext__(), definition.INACTIVITY_TIMEOUT_S
                    )
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    result.stop_reason = "inactivity_timeout"
                    trace.record_result(
                        "inactivity_timeout",
                        detail=f"{definition.INACTIVITY_TIMEOUT_S}s 無応答",
                    )
                    return result

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            trace.record_decision(block.text)
                        elif isinstance(block, ToolUseBlock):
                            trace.record_tool_use(block.name, block.input)

                            call_key = (block.name, digest_args(block.input))
                            last_calls.append(call_key)
                            last_calls[:] = last_calls[
                                -definition.REPEATED_CALL_LIMIT :
                            ]
                            if (
                                len(last_calls) == definition.REPEATED_CALL_LIMIT
                                and len(set(last_calls)) == 1
                            ):
                                result.stop_reason = "repeated_call"
                                trace.record_result(
                                    "repeated_call",
                                    detail=(
                                        f"同一ツール・同一引数を{definition.REPEATED_CALL_LIMIT}"
                                        "回連続で呼び出した"
                                    ),
                                )
                                return result
                elif isinstance(message, UserMessage):
                    for block in getattr(message, "content", []) or []:
                        if isinstance(block, ToolResultBlock):
                            trace.record_observation(
                                tool_name="",
                                content=block.content,
                                is_error=block.is_error,
                            )
                elif isinstance(message, ResultMessage):
                    completed = not message.is_error
                    if message.num_turns and message.num_turns >= definition.MAX_TURNS:
                        result.stop_reason = "max_turns"
                    else:
                        result.stop_reason = "completed" if completed else "failed"
                    result.output = message.result
                    result.num_turns = message.num_turns
                    result.cost_usd = message.total_cost_usd
                    trace.record_result(
                        result.stop_reason,
                        num_turns=message.num_turns,
                        cost_usd=message.total_cost_usd,
                    )
    except TimeoutError:
        # 内側タイムアウト発火（agent-plan.md の強制停止）。記録してから返す。
        result.stop_reason = "inner_timeout"
        trace.record_result(
            "inner_timeout", detail=f"{definition.INNER_TIMEOUT_S}s 超過"
        )
    return result
