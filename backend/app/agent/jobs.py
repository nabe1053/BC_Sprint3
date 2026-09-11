"""エージェント実行のジョブ管理（Sprint 3 の実行の型）。

- 起動: start_agent_job() → run_id を即返し、実行はバックグラウンドタスクで進む
- 監視: get_job(run_id) でステータス、read_progress(run_id) で進捗
- 進捗の実体はトレース（traces/{run_id}.jsonl）そのもの — 別の進捗管理を作らない
- ジョブ一覧はプロセス内保持（教材の割り切り）。再起動で消える。
  永続化が要件なら 04-db.md の `agent_runs` / `agent_run_steps` へ書く（build-loop で実装）
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from app.agent import definition
from app.agent.runner import AgentRunResult, run_agent
from app.agent.trace import TRACES_DIR, TraceRecorder


@dataclass
class AgentJob:
    run_id: str
    status: str  # running / completed / failed / max_turns / *_timeout / repeated_call
    started_at: str
    result: AgentRunResult | None = None


_jobs: dict[str, AgentJob] = {}


def start_agent_job(prompt: str, *, scenario: str | None = None) -> str:
    """エージェントをバックグラウンドで起動し、run_id を即返す。"""
    trace = TraceRecorder(
        scenario=scenario
    )  # 先に作る → run_id が確定 & 外側発火も記録可能
    job = AgentJob(
        run_id=trace.run_id,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    _jobs[trace.run_id] = job
    asyncio.create_task(_execute(job, prompt, trace))
    return trace.run_id


async def _execute(job: AgentJob, prompt: str, trace: TraceRecorder) -> None:
    try:
        # 外側タイムアウト: 内側（runner）が機能しなかったときの最後の砦
        result = await asyncio.wait_for(
            run_agent(prompt, trace=trace), definition.OUTER_TIMEOUT_S
        )
        job.result = result
        job.status = result.stop_reason
    except TimeoutError:
        # 外側発火 = 内側の異常（ハング）。トレースに記録し、バグとして調査する
        trace.record_result(
            "outer_timeout",
            detail=f"{definition.OUTER_TIMEOUT_S}s 超過（内側が機能せず）",
        )
        job.status = "outer_timeout"
    except Exception as e:  # 予期しない例外もジョブとトレースに残す
        trace.record_result("failed", detail=repr(e))
        job.status = "failed"


def get_job(run_id: str) -> AgentJob | None:
    return _jobs.get(run_id)


def read_progress(run_id: str, limit: int = 20) -> list[dict]:
    """進捗 = トレースの末尾。ポーリング応答にそのまま載せる
    （agent-plan.md「ユーザーから見た体験（実行中の見え方）」の実装手段）。"""
    path = TRACES_DIR / f"{run_id}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]
