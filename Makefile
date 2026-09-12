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

BACKEND  := backend
FRONTEND := frontend
TEST_DB  := postgresql+psycopg://postgres:postgres@localhost:5432/octg_test

.PHONY: check check-be check-fe db migrate be-lint be-test openapi orval fe-type fe-test fe-lint help

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

## ---- フルゲート ------------------------------------------------------------

check: check-be openapi orval fe-type fe-lint fe-test ## スライス完了時のフルゲート
	@echo "✅ check: all green"

check-be: db migrate be-lint be-test ## バックエンドのみ（BE スライス用）
	@echo "✅ check-be: backend green"

check-fe: openapi orval fe-type fe-lint fe-test ## フロントのみ（FE スライス用）
	@echo "✅ check-fe: frontend green"

## ---- 個別ステップ ----------------------------------------------------------

db: ## PostgreSQL を起動して healthy を待つ
	@docker compose up -d
	@for i in $$(seq 1 30); do \
	  docker exec octg_postgres pg_isready -U postgres >/dev/null 2>&1 && exit 0; \
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
