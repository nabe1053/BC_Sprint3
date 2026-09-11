# エージェントスライスの実装手順（build-loop 用）

orchestrator（build-loop）がエージェントスライス（種別: agent）を回すときの層順と原則。
設計の正は `docs/requirements/agent-plan.md`、実装原則の正は `.claude/rules/agent-development.md`。

## 前提

- Foundation Slice 0-7（`/foundation-agent-setup`）完了。`backend/app/agent/`
  （definition / tools / runner / jobs / trace）のスケルトンが存在する
- agent-plan.md に対象エージェント（AGENT-XX）の Part 1 / Part 2 が記述済み

## 原則（指示書・レビューに常に含める）

- **ツールは決定的な関数**: 入出力が決まっているので TDD の対象。
  **エージェントループ自体は単体テストしない**（非決定的。ミニ評価 + Phase 3 の評価で検証する）
- **設計が正**: agent-plan.md に無いツール・完了条件を実装しない。必要が生じたら BLOCKED にして
  orchestrator へ報告（設計側の更新はループの外で行う）
- **ガードレールは強制**: PreToolUse hook / disallowed_tools でブロック（プロンプトのお願いにしない）
- **起動はジョブ経由**: `jobs.start_agent_job()`。HTTP で `run_agent()` を同期 await しない
- **タイムアウトの大小関係**（無応答 < 内側 < 外側）を崩さない

## 層順（依存内側 → 外側）

### 層1: ツール（tools.py）— RED → GREEN

- agent-plan.md「ツール一覧」の **1 行 = 1 ツール**（`@tool` 関数）
- ツールが使う repository / service が未実装なら、**先にその Web スライス（依存）を回す**
  （プラン段階で依存に入れておくのが原則。漏れていたら memory §3 に依存スライスを追加）
- test-designer への指示: 正常・異常・境界。repository/service は mock。
  副作用（write）を持つツールはガードレール条件も異常系に含める
- implementer への指示: `AGENT_TOOLS` / `ALLOWED_TOOL_NAMES` への登録まで含める

### 層2: definition / ガードレール（テスト対象外の設定層・implementer）

- `SYSTEM_PROMPT` を agent-plan.md のミッション・完了条件から具体化
- `MAX_TURNS`・タイムアウト値を agent-plan.md「強制停止」から転記（無応答 < 内側 < 外側の assert を維持）
- サブエージェント構成があれば SUBAGENTS として定義し options に渡す
  （各サブの使えるツール = agent-plan.md 表のサブセット。SDK の正確な記法は
  https://code.claude.com/docs/en/agent-sdk/python で確認）
- ガードレール: agent-plan.md「してはいけない操作」→ PreToolUse hook で block /
  「承認が必要な操作」→ 実行前確認の構造に

### 層3: API 接続（jobs 経由）— RED → GREEN

```
POST /api/v1/{feature}/runs          → service が jobs.start_agent_job() → 202 { "run_id" }
GET  /api/v1/{feature}/runs/{run_id} → { status, progress: read_progress(...), result }
```

- backend-api 層のテスト: 202 + run_id が即返ること / GET の status 遷移（jobs は mock 可）
- 実行状態を DB に持つ設計（04-db）なら repository 経由で保存

### 層4: 統合ポイント（orchestrator が Bash）

OpenAPI 出力 → orval 再生成 → typecheck（Web スライスと同じ）

### 層5: フロント（ポーリング UI）— RED → GREEN

- TanStack Query の `refetchInterval` で status=running の間ポーリング
- progress（トレース末尾の decision / tool_use）を進捗表示に使う
  （agent-plan.md「ユーザーから見た体験（実行中の見え方）」に対応）

### 層6: ミニ評価（orchestrator が Bash・レビュー前に必ず実施）

agent-plan.md「評価シナリオ」の**正常系1本**をジョブ経由で実行する:

```bash
cd backend
uv run python - <<'EOF'
import asyncio
from app.agent.jobs import get_job, start_agent_job

async def main():
    run_id = start_agent_job("{シナリオの入力例}")
    while (job := get_job(run_id)).status == "running":
        await asyncio.sleep(2)
    print(f"run_id={run_id} status={job.status}")

asyncio.run(main())
EOF
```

確認事項（トレース `backend/traces/{run_id}.jsonl` を Read）:
1. stop_reason が完了条件どおり（completed）。`*_timeout` / `max_turns` で終わっていない
2. 使用ツール ⊆ agent-plan.md ツール一覧
3. ガードレール違反（禁止操作の試行）が無い

Fail の場合はトレースの該当行を根拠に implementer へ修正を委譲（原因がツールか
definition（プロンプト）かをトレースの decision / observation から切り分けて指示する）。
run_id は memory §5 に記録する。

## reviewer への引き渡し（Step 5）

変更範囲に加えて必ず渡す:
- `docs/requirements/agent-plan.md`（該当エージェントの節）
- ミニ評価の run_id（reviewer はトレースを read して裏取りできる）
- `clean-architecture.md` チェックリストの「AI Agent 固有」項目
