---
name: foundation-agent-setup
description: Slice 0-7 Claude Agent SDK セットアップ。app/agent/ スケルトン（definition/tools/runner/trace）生成・タイムアウト2層とハング対応の組み込み・疎通テスト
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Slice 0-7: Agent Setup（Claude Agent SDK）

Claude Agent SDK を導入し、エージェント実装の骨格 `backend/app/agent/` を生成する。
実際のエージェント（ツール・完了条件）は後続の `/build-loop`（エージェントスライス）が
`docs/requirements/agent-plan.md` をもとに実装する。このスライスは**器とガードレールの基盤**を作る。

## Purpose

1. `claude-agent-sdk` の導入確認と `ANTHROPIC_API_KEY` の設定
2. `app/agent/` スケルトン生成（definition / tools / runner / trace / jobs）
3. **タイムアウト2層構造**（内側 < 外側）と**ハング対応**の組み込み
4. **トレース基盤**（JSONL・agent-plan.md の IPO 拡張表と同型）の組み込み
5. **実行の型**（バックグラウンドジョブ + run_id ポーリング）の組み込み
6. 1ターンの疎通テストで動作確認

## When to use

- Slice 0-1 ～ 0-6 完了後（Foundation Phase の最終スライス）
- `/build-loop` を実行する前に必ず完了していること（Foundation の最終スライス）

## Prerequisites

- Slice 0-1（FastAPI）完了。`backend/` で `uv sync` 済み（`claude-agent-sdk` は pyproject に定義済み）
- `docs/requirements/agent-plan.md` が存在する（設計フェーズ完了）

## Outputs

```
backend/
├── app/agent/
│   ├── __init__.py
│   ├── definition.py    # システムプロンプト・停止条件の定数（agent-plan.md Part 1 の写し先）
│   ├── tools.py         # カスタムツール（@tool + create_sdk_mcp_server）
│   ├── runner.py        # 実行ループ（内側タイムアウト・ハング検知・トレース記録）
│   ├── jobs.py          # 実行の型: バックグラウンドジョブ + run_id ポーリング（外側タイムアウト）
│   └── trace.py         # トレースレコーダー（JSONL）
├── traces/              # 実行トレース出力先（.gitignore 済み）
└── .env                 # ANTHROPIC_API_KEY 追記
```

## Procedure

### Step 1: SDK・APIキーの確認

```bash
cd backend
# claude-agent-sdk がインストールされているか（pyproject 定義済み。無ければ uv sync）
uv run python -c "import claude_agent_sdk; print(claude_agent_sdk.__name__, 'OK')"
```

`.env` に `ANTHROPIC_API_KEY` があるか確認し、無ければユーザーに設定を依頼する：

```
backend/.env に以下を追記してください（キーは Anthropic Console で発行）:
ANTHROPIC_API_KEY=sk-ant-...
```

> **注**: SDK の記法（hooks・オプション名）はバージョンで差異があり得る。
> 生成したコードがエラーになった場合は公式リファレンス
> https://code.claude.com/docs/en/agent-sdk/python を確認して修正する。

### Step 2: 停止条件・タイムアウト定数（definition.py）

`docs/requirements/agent-plan.md` の「完了条件・停止条件」を読み、
**強制停止の値（最大ターン数・タイムアウト）を設計から転記**して生成する。
未記載ならデフォルト値を使い、agent-plan.md に追記するようユーザーに促す。

```python
# backend/app/agent/definition.py
"""エージェント定義: docs/requirements/agent-plan.md Part 1 に対応する。

このファイルの値は設計書（agent-plan.md）の写しであり、変更するときは agent-plan.md 側も更新する。
"""

# ミッション（agent-plan.md の「ミッション」を反映。build-loop のエージェントスライスが具体化する）
SYSTEM_PROMPT = """あなたは {ミッションをここに記述} を代行するエージェントです。
完了条件: {agent-plan.md の成功条件}
失敗と判断したら作業を中断し、理由を報告してください。
"""

# --- 強制停止（agent-plan.md の「完了条件・停止条件」の強制停止行に対応） ---
MAX_TURNS = 20                # 最大ターン数（SDK に渡す）

# --- タイムアウトの2層構造（必ず 内側 < 外側 を守る） ---
# 内側 = エージェント自身の停止条件。発火したらトレースに記録して整然と終了する。
# 外側 = ジョブ層（jobs.py）のフェイルセーフ。内側がハング等で発火できないときの最後の砦。
INNER_TIMEOUT_S = 300         # 内側: エージェント実行全体の上限
INACTIVITY_TIMEOUT_S = 60     # 内側: メッセージ間の無応答上限（ハング検知）
OUTER_TIMEOUT_S = 360         # 外側: jobs.py が run_agent() 全体に掛ける上限

assert INACTIVITY_TIMEOUT_S < INNER_TIMEOUT_S < OUTER_TIMEOUT_S, (
    "タイムアウトは 無応答 < 内側 < 外側 の順でなければならない。"
    "外側が先に発火すると、トレースに停止理由を記録できないまま実行が破棄される。"
)

# ガードレール（agent-plan.md の「ガードレール」に対応。build-loop のエージェントスライスが具体化する）
# 例: 禁止コマンド・書き込み系ツールの制限
BLOCKED_PATTERNS: list[str] = []
```

### Step 3: カスタムツールの雛形（tools.py）

```python
# backend/app/agent/tools.py
"""カスタムツール群: docs/requirements/agent-plan.md「ツール一覧」と1対1で対応させる。

- ツールは入出力の決まった関数として実装し、単体テスト（TDD）の対象にする
- 副作用（write）を持つツールは agent-plan.md のガードレールと突き合わせる
- ツール名は mcp__app__{tool_name} 形式で allowed_tools に列挙する
"""
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


@tool("ping", "疎通確認用。メッセージをそのまま返す", {"message": str})
async def ping(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"pong: {args['message']}"}]}


# build-loop（エージェントスライス）がここに agent-plan.md のツールを追加していく
AGENT_TOOLS = [ping]

agent_server = create_sdk_mcp_server(name="app", version="1.0.0", tools=AGENT_TOOLS)

# allowed_tools に渡す名前（mcp__{server}__{tool}）
ALLOWED_TOOL_NAMES = [f"mcp__app__{t.name}" for t in AGENT_TOOLS] if hasattr(ping, "name") else [
    "mcp__app__ping",
]
```

> `@tool` が返すオブジェクトから名前を取れない SDK バージョンでは、
> `ALLOWED_TOOL_NAMES` を文字列リストで直接管理してよい（シンプル優先）。

### Step 4: トレースレコーダー（trace.py）

トレースの1レコードは **agent-plan.md の「エージェントフロー（IPO拡張）」の表と同型**にする。
これにより評価時に設計とログを1対1で突き合わせられる。

```python
# backend/app/agent/trace.py
"""エージェント実行トレース: backend/traces/{run_id}.jsonl に記録する。

レコードは agent-plan.md の IPO 拡張表（Input / 判断 / ツール実行 / 観察・Output）と同型。
記録されない実行は評価できない — すべての実行はここを通す。
"""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path(__file__).resolve().parents[2] / "traces"


class TraceRecorder:
    def __init__(self, scenario: str | None = None) -> None:
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
        self.path = TRACES_DIR / f"{self.run_id}.jsonl"
        self.step = 0
        self._start = time.monotonic()
        TRACES_DIR.mkdir(exist_ok=True)
        self._write({"type": "meta", "run_id": self.run_id, "scenario": scenario,
                     "started_at": datetime.now(timezone.utc).isoformat()})

    def _write(self, record: dict) -> None:
        record.setdefault("elapsed_s", round(time.monotonic() - self._start, 2))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def record_input(self, prompt: str) -> None:
        self._write({"type": "input", "prompt": prompt})

    def record_decision(self, text: str) -> None:
        """判断(Process): アシスタントのテキスト/思考"""
        self.step += 1
        self._write({"type": "decision", "step": self.step, "text": text})

    def record_tool_use(self, name: str, tool_input: dict) -> None:
        """ツール実行: 使用ツールが agent-plan.md ツール一覧の範囲内かの検証に使う"""
        self._write({"type": "tool_use", "step": self.step, "tool": name, "input": tool_input})

    def record_observation(self, tool_name: str, content, is_error: bool) -> None:
        """観察: ツール結果"""
        self._write({"type": "observation", "step": self.step, "tool": tool_name,
                     "content": content, "is_error": is_error})

    def record_result(self, stop_reason: str, *, num_turns: int | None = None,
                      cost_usd: float | None = None, detail: str | None = None) -> None:
        """終了: stop_reason は completed / failed / max_turns / inner_timeout /
        inactivity_timeout / outer_timeout のいずれか（agent-plan.md 停止条件と対応付ける）"""
        self._write({"type": "result", "stop_reason": stop_reason, "num_turns": num_turns,
                     "cost_usd": cost_usd, "detail": detail})
```

### Step 5: 実行ループ（runner.py）— 内側タイムアウト・ハング検知

```python
# backend/app/agent/runner.py
"""エージェント実行ループ。

タイムアウトの責務分担:
- 内側（このファイル）: INNER_TIMEOUT_S（実行全体）と INACTIVITY_TIMEOUT_S（無応答=ハング検知）。
  発火したらトレースに stop_reason を記録して整然と終了する。agent-plan.md の「強制停止」に対応。
- 外側（jobs.py）: OUTER_TIMEOUT_S。内側が機能しなかった場合（SDK サブプロセスの
  ハング・キャンセル不能など）の最後の砦。発火 = 内側の異常であり、バグとして扱う。

直接呼ばない: 起動は必ず jobs.start_agent_job() 経由（バックグラウンド実行 + 外側タイムアウト）。
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
from app.agent.tools import ALLOWED_TOOL_NAMES, agent_server
from app.agent.trace import TraceRecorder


@dataclass
class AgentRunResult:
    run_id: str
    stop_reason: str          # completed / failed / max_turns / inner_timeout / inactivity_timeout
    output: str | None = None
    num_turns: int | None = None
    cost_usd: float | None = None


def _build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=definition.SYSTEM_PROMPT,
        mcp_servers={"app": agent_server},
        allowed_tools=ALLOWED_TOOL_NAMES,
        max_turns=definition.MAX_TURNS,
        # ガードレール（PreToolUse hook）は build-loop のエージェントスライスで agent-plan.md をもとに追加する
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
                    trace.record_result("inactivity_timeout",
                                        detail=f"{definition.INACTIVITY_TIMEOUT_S}s 無応答")
                    return result

                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            trace.record_decision(block.text)
                        elif isinstance(block, ToolUseBlock):
                            trace.record_tool_use(block.name, block.input)
                elif isinstance(message, UserMessage):
                    for block in getattr(message, "content", []) or []:
                        if isinstance(block, ToolResultBlock):
                            trace.record_observation(
                                tool_name="", content=block.content, is_error=block.is_error
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
                    trace.record_result(result.stop_reason,
                                        num_turns=message.num_turns,
                                        cost_usd=message.total_cost_usd)
    except TimeoutError:
        # 内側タイムアウト発火（agent-plan.md の強制停止）。記録してから返す。
        result.stop_reason = "inner_timeout"
        trace.record_result("inner_timeout", detail=f"{definition.INNER_TIMEOUT_S}s 超過")
    return result
```

### Step 6: 実行の型（jobs.py）— バックグラウンドジョブ + run_id ポーリング

エージェントは数分かかるため、**HTTP リクエストで完了を同期的に待たない**。
Sprint 3 の実行の型は「POST で起動 → 202 + run_id を即返す → GET でポーリング」。
外側タイムアウトはこのジョブ層が持つ（trace を先に作るので、外側発火もトレースに記録できる）。

```python
# backend/app/agent/jobs.py
"""エージェント実行のジョブ管理（Sprint 3 の実行の型）。

- 起動: start_agent_job() → run_id を即返し、実行はバックグラウンドタスクで進む
- 監視: get_job(run_id) でステータス、read_progress(run_id) で進捗
- 進捗の実体はトレース（traces/{run_id}.jsonl）そのもの — 別の進捗管理を作らない
- ジョブ一覧はプロセス内保持（教材の割り切り）。再起動で消える。
  永続化が要件なら 04-db の設計（実行状態テーブル）に従い DB へ
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
    status: str                       # running / completed / failed / max_turns / *_timeout
    started_at: str
    result: AgentRunResult | None = None


_jobs: dict[str, AgentJob] = {}


def start_agent_job(prompt: str, *, scenario: str | None = None) -> str:
    """エージェントをバックグラウンドで起動し、run_id を即返す。"""
    trace = TraceRecorder(scenario=scenario)   # 先に作る → run_id が確定 & 外側発火も記録可能
    job = AgentJob(run_id=trace.run_id, status="running",
                   started_at=datetime.now(timezone.utc).isoformat())
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
        trace.record_result("outer_timeout", detail=f"{definition.OUTER_TIMEOUT_S}s 超過（内側が機能せず）")
        job.status = "outer_timeout"
    except Exception as e:  # 予期しない例外もジョブとトレースに残す
        trace.record_result("failed", detail=repr(e))
        job.status = "failed"


def get_job(run_id: str) -> AgentJob | None:
    return _jobs.get(run_id)


def read_progress(run_id: str, limit: int = 20) -> list[dict]:
    """進捗 = トレースの末尾。ポーリング応答にそのまま載せる
    （agent-plan.md「ユーザーから見た体験（実行中の見え方）」の実装手段）"""
    path = TRACES_DIR / f"{run_id}.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines[-limit:]]
```

**API の型**（`/build-loop` のエージェントスライスがこの形でエンドポイントを作る）:

```
POST /api/v1/{feature}/runs            → service が start_agent_job() → 202 { "run_id": ... }
GET  /api/v1/{feature}/runs/{run_id}   → { "status": ..., "progress": read_progress(...), "result": ... }
```

- endpoints → service → `start_agent_job()` の順（endpoints から jobs を直接呼ばない）
- フロントは TanStack Query の `refetchInterval` で status が running の間ポーリングし、
  progress（トレース末尾の decision / tool_use）をそのまま進捗表示に使う
- SSE でのストリーミングは発展課題（まずポーリングで型を身につけ、必要なら Env フェーズで拡張）

### Step 7: 疎通テスト

**実行の型そのもの**（ジョブ起動 → ポーリング）でセットアップ全体（SDK・APIキー・トレース・
タイムアウト・ジョブ）を検証する：

```bash
cd backend
uv run python - <<'EOF'
import asyncio
from app.agent.jobs import get_job, read_progress, start_agent_job

async def main():
    run_id = start_agent_job("ping ツールで 'hello' を送って結果を報告して")
    print(f"run_id={run_id}（即時に返る = 202 相当）")

    while (job := get_job(run_id)).status == "running":   # GET ポーリング相当
        await asyncio.sleep(2)
        last = read_progress(run_id, limit=1)
        print(f"  polling... status={job.status} last={last[-1]['type'] if last else '-'}")

    print(f"status={job.status} turns={job.result.num_turns if job.result else '-'} "
          f"cost=${job.result.cost_usd if job.result else '-'}")
    assert job.status == "completed", "疎通テスト失敗"

asyncio.run(main())
EOF
ls traces/   # トレースが生成されていることを確認
```

疎通テストが通ったら、以下の2点をユーザーに見せて説明する：
1. 生成されたトレース（JSONL）の「input → decision → tool_use → observation → result」の流れが
   **agent-plan.md の IPO 拡張表と同型**であること
2. ポーリング中に表示された progress が**トレースの末尾そのもの**であること
   （= 画面の進捗表示はこの仕組みで作る。Phase 3 で API にするのはこの型の HTTP 版）

### Step 8: 完了確認

```
✅ Slice 0-7 完了: Claude Agent SDK セットアップ

- app/agent/ スケルトン（definition / tools / runner / trace / jobs）
- タイムアウト2層: 内側 {INNER_TIMEOUT_S}s（+無応答 {INACTIVITY_TIMEOUT_S}s）< 外側 {OUTER_TIMEOUT_S}s
- 実行の型: バックグラウンドジョブ + run_id ポーリング（POST 202 → GET /runs/{run_id}）
- トレース: backend/traces/{run_id}.jsonl（agent-plan.md IPO 拡張表と同型・進捗表示にも流用）
- 疎通テスト: Pass（ジョブ経由）

次: /build-loop で実装ループを開始します（スライス分割は build-loop 自身が行い、
.claude/memory.md に記録しながら自律周回します）。
```

## Constraints

- タイムアウトの大小関係（無応答 < 内側 < 外側）を崩す変更をしない
- トレースを通らないエージェント実行経路を作らない
- **HTTP リクエスト内で `run_agent()` を同期 await するエンドポイントを作らない**
  （起動は必ず `jobs.start_agent_job()` 経由。完了待ちはポーリング）
- `ANTHROPIC_API_KEY` を git 管理下のファイルに書かない（`.env` のみ）
- SDK の記法エラーは公式リファレンスで確認して修正する（推測で書き換えない）
