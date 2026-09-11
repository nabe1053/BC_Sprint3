# OCTG Item List Agent - Backend (FastAPI)

FastAPI + PostgreSQL + Claude Agent SDK によるローカル実行 REST API サーバー。
Sprint 3 は認証を実装しない（`CLAUDE.md` 決定事項1）。

## セットアップ

### 1. 環境変数
```bash
cp .env.example .env
# 必要なら backend/.env に ANTHROPIC_API_KEY を追記（Slice 0-7 の疎通テストのみ必須）
```

### 2. PostgreSQL を起動（リポジトリルートで）
```bash
docker compose up -d
docker compose ps   # octg_postgres が healthy になっていること
```

### 3. 依存パッケージ
```bash
uv sync
```

### 4. マイグレーション適用
```bash
uv run alembic upgrade head
```

### 5. 開発サーバー起動
```bash
uv run uvicorn app.main:app --reload
```
- Swagger UI: http://localhost:8000/docs
- ヘルスチェック: http://localhost:8000/api/v1/health

## DB 初期化・評価やり直し手順（04-db.md 0.6）

評価をやり直す場合、PostgreSQL の named volume を削除して Alembic を再適用する：

```bash
docker compose down
docker volume rm bc_sprint3_postgres_data
docker compose up -d
sleep 3
cd backend && uv run alembic upgrade head
```

## テスト・Lint

Repository 層の統合テスト（`tests/integration/`）はテスト専用データベース
（既定 `octg_test`）を使う（本番用 `octg_db` を汚さないため）。初回のみ以下の
手順でテスト DB を用意する（m-7）。

```bash
# 1. テスト用データベースを作成（PostgreSQL がローカル起動済みであること）
docker exec -it octg_postgres psql -U postgres -c "CREATE DATABASE octg_test;"

# 2. テスト DB にマイグレーションを適用（本番用 DATABASE_URL とは別に指定する）
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/octg_test \
  uv run alembic upgrade head

# 3. テストを実行
uv run pytest tests/ -v
```

`tests/conftest.py` の `TEST_DATABASE_URL`（環境変数 `TEST_DATABASE_URL` で
上書き可）が既定でこの `octg_test` を見に行く。テストの前後で対象テーブルを
TRUNCATE して掃除するため、既存データを壊さないよう本番用 DB とは分離すること。

```bash
uv run ruff format --check app tests
uv run ruff check app tests
```

## OpenAPI スキーマ出力（Slice 0-6）

```bash
uv run python scripts/export_openapi.py -o openapi.json
```

## エージェント（Slice 0-7・Claude Agent SDK）

`app/agent/`（definition / tools / hooks / runner / trace / jobs）がスケルトン。
実行の型は「POST → 202 + run_id → GET ポーリング」（`jobs.start_agent_job()` 経由）。
タイムアウトは2層（無応答60s < 内側900s < 外側960s）。

ツールは `agent-plan.md` の13点のみを登録する（`app/agent/tools.py` の `AGENT_TOOLS`）。
D05（外部LLM送信）が未承認のため、Foundation の各ツールはダミー応答のスタブ。
build-loop のエージェントスライスが `/agent/*` API 呼び出しに差し替える。

疎通テスト（`ANTHROPIC_API_KEY` が必要。未設定なら SKIP して正常終了する）:

```bash
# backend/.env に ANTHROPIC_API_KEY=sk-ant-... を追記してから
uv run python scripts/agent_smoke_test.py
ls traces/   # {run_id}.jsonl が生成されていることを確認
```

ツール・ガードレールの単体テスト（キー不要）:

```bash
uv run pytest tests/unit/test_agent_tools.py tests/unit/test_agent_guardrails.py -v
```

## ディレクトリ構造

- `app/api/agent/` : `/agent/*`（AGENT-01 のツールが呼ぶ API のみ。05-api-ipo.md 7章の13ツールに対応する
  API 番号 4・6・7・8・9・11・15〜21）
- `app/api/ui/` : `/ui/*`（画面が呼ぶ API。人の記録 API・出力・起動系はすべてここ）
- `app/core/` : 設定・DB・依存注入
- `app/models/` : SQLAlchemy ORM（Foundation では9テーブルのみ。残りは build-loop で追加）
- `app/repositories/` : Data Access 層
- `app/services/` : ビジネスロジック（エージェント起動もここから `jobs.start_agent_job()`）
- `app/agent/` : Claude Agent SDK（definition / tools / runner / trace / jobs）
- `alembic/` : マイグレーション（CHECK・UNIQUE・複合FK も明示的に記述）
- `traces/` : エージェント実行トレース（git 管理外）

## 認証について

Sprint 3 は認証を実装しない（`02-requirement.md` N02: ローカル単一利用者の PoC）。
`/agent/*` と `/ui/*` のパス分離で、AGENT-01 が人の記録 API（D層）を呼べない境界を構造的に守る
（`05-api-ipo.md` 7.1）。
