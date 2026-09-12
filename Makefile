# 品質ゲートの単一入口。
# 「通しで緑を見る」を安くするために作った（レビュー4回目で migration 未適用による
# 44 ERROR が発覚した反省。memory LN-013 / LN-017）。
#
#   make check     … スライス完了時のフルゲート（BE → 統合 → FE）
#   make check-be  … BE だけ触ったスライス用（高速）
#   make migrate   … 開発 DB・テスト DB の両方に alembic upgrade head
#
# 注意: テスト DB だけでなく **開発 DB にも適用する**。統合テストは TestClient の
# lifespan で app 本体のエンジン（settings.DATABASE_URL = octg_db）に触るため、
# 開発 DB のスキーマが古いと tests/integration が全滅する（LN-017）。

.NOTPARALLEL:

BACKEND  := backend
FRONTEND := frontend
DB_CONTAINER ?= octg_postgres
DB_USER ?= postgres
DEV_DATABASE ?= octg_db
TEST_DB  := postgresql+psycopg://postgres:postgres@localhost:5432/octg_test

.PHONY: check check-be check-fe db migrate be-lint be-test openapi orval fe-type fe-test fe-lint help
.PHONY: check-run-step-index

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## ---- フルゲート ------------------------------------------------------------

check: check-be openapi orval fe-type fe-lint fe-test ## スライス完了時のフルゲート
	@echo "✅ check: all green"

check-be: db migrate check-run-step-index be-lint be-test ## バックエンドのみ（BE スライス用）
	@echo "✅ check-be: backend green"

check-fe: openapi orval fe-type fe-lint fe-test ## フロントのみ（FE スライス用）
	@echo "✅ check-fe: frontend green"

## ---- 個別ステップ ----------------------------------------------------------

db: ## PostgreSQL を起動して healthy を待つ
	@docker compose up -d
	@for i in $$(seq 1 30); do \
	  docker exec $(DB_CONTAINER) pg_isready -U $(DB_USER) >/dev/null 2>&1 && exit 0; \
	  sleep 1; \
	done; echo "❌ postgres が healthy になりません"; exit 1

migrate: ## 開発 DB とテスト DB の両方に migration を適用
	@echo "── alembic upgrade head (octg_db / 開発)"
	@cd $(BACKEND) && uv run alembic upgrade head
	@echo "── alembic upgrade head (octg_test / テスト)"
	@cd $(BACKEND) && DATABASE_URL='$(TEST_DB)' uv run alembic upgrade head

be-lint: ## ruff format + check
	@cd $(BACKEND) && uv run ruff format app tests && uv run ruff check --fix app tests

be-test: ## backend 全体回帰（分割実行しない）
	@cd $(BACKEND) && uv run pytest tests/ -q

openapi: ## OpenAPI を backend/openapi.json へ出力（orval の target）
	@cd $(BACKEND) && uv run python scripts/export_openapi.py -o openapi.json

orval: ## 生成クライアント再生成 + mutator 結線の確認（LN-010）
	@cd $(FRONTEND) && npm run orval
	@grep -rq "customInstance" $(FRONTEND)/src/shared/api/generated \
	  || { echo "❌ 生成コードが customInstance を呼んでいない（orval の mutator 設定を確認: LN-010）"; exit 1; }

fe-type: ## tsc --noEmit（全体。分割 tsconfig を使わない）
	@cd $(FRONTEND) && npm run typecheck

fe-lint: ## eslint
	@cd $(FRONTEND) && npm run lint

fe-test: ## jest
	@cd $(FRONTEND) && npm run test

check-run-step-index: export INDEX_CONTAINER = $(DB_CONTAINER)
check-run-step-index: export INDEX_USER = $(DB_USER)
check-run-step-index: export INDEX_DEV_DATABASE = $(DEV_DATABASE)
check-run-step-index: export INDEX_TEST_URL = $(TEST_DB)
check-run-step-index: ## 両 DB の実スキーマで走査索引を読取専用検証
	@cd $(BACKEND) && uv run python -B scripts/check_scan_index.py --index-only

.PHONY: agent-test agent-eval agent-eval-lint agent-mutations
agent-test: ## エージェントの決定的ツール境界をTDD確認
	@cd $(BACKEND) && uv run pytest \
	  tests/unit/test_agent_execution_tools.py tests/integration/test_agent_tool_repository.py \
	  tests/unit/test_agent_tools.py tests/unit/test_agent_guardrails.py \
	  tests/unit/test_single_source_of_truth.py tests/unit/test_api_path_separation.py \
	  tests/unit/test_regression_gate.py \
	  tests/unit/test_live_index_check_configuration.py \
	  tests/integration/test_run_regressions.py -q --tb=short --disable-warnings

agent-eval-lint: ## ミニ評価スクリプトの整形・静的検査
	@cd $(BACKEND) && uv run ruff format scripts/evaluate_local_agent.py scripts/check_agent_mutations.py scripts/check_scan_index.py
	@cd $(BACKEND) && uv run ruff check scripts/evaluate_local_agent.py scripts/check_agent_mutations.py scripts/check_scan_index.py

agent-mutations: agent-eval-lint ## ガードレールの変異強度確認（ソース変更なし）
	@cd $(BACKEND) && uv run python -B scripts/check_agent_mutations.py

agent-eval: agent-eval-lint ## ローカルジョブのミニ評価（外部送信なし）
	@cd $(BACKEND) && DATABASE_URL='$(TEST_DB)' uv run python -B scripts/evaluate_local_agent.py
