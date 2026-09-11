# クリーンアーキテクチャ ガイド（Sprint 3: FastAPI + Next.js + Claude Agent SDK）

実装ハーネス（build-loop）が全スライスで守るアーキテクチャ規約。
**依存ルール**（内側は外側を知らない）を中心に、層 → ディレクトリ対応と
reviewer チェックリストを定義する。

> エージェント固有の原則（トレース・ガードレール・タイムアウト2層・実行の型）は
> `.claude/rules/agent-development.md` を正とする。本ファイルは層配置とレビュー観点を扱う。

## 依存ルール（最重要）

```
  外側 ────────────────────────────────▶ 内側
  Presentation      Business Logic       Data Access
  （UI/API）    →   （Service/Agent） →   （Repository）
   依存の向きは常に「外側 → 内側」。逆流は禁止。
   内側の層は外側の層を import/参照してはならない。
```

- Presentation は Business Logic を呼ぶ。Business Logic は Data Access を **interface/Repository 経由**で呼ぶ。
- Business Logic は ORM/SQL/HTTP を**直接触らない**（Repository に委譲）。
- **AI Agent（`app/agent/`）は Business Logic に属する**:
  - 起動は service 層から `jobs.start_agent_job()` 経由（endpoints から `run_agent()` を直接呼ばない）
  - ツール（tools.py）が DB・外部 API に触るときは repository / service を経由する（生 SQL・生 HTTP 禁止）

## 層 → ディレクトリ対応（Sprint 3）

### Backend（FastAPI + Claude Agent SDK）
| 層 | ディレクトリ | 責務 |
|----|-------------|------|
| DTO/スキーマ | `backend/app/api/v1/schemas/`（Pydantic） | Request/Response 型 |
| Data Access | `backend/app/repositories/` + `backend/app/models/`（ORM） | DB 操作の抽象化 |
| Business Logic | `backend/app/services/` | ビジネスルール・エージェント起動（jobs 経由） |
| Business Logic（Agent） | `backend/app/agent/`（definition / tools / runner / jobs / trace） | エージェント実行（agent-plan.md が設計の正） |
| Presentation-API | `backend/app/api/v1/endpoints/` + `middleware/` | エンドポイント・認証 |

### Frontend（Next.js 15 App Router + MUI / FSD）
| 層 | ディレクトリ | 責務 |
|----|-------------|------|
| Data Access | `frontend/src/features/*/api.ts` + `shared/api/generated/`（自動生成・編集禁止） | orval 生成フックの wrap |
| Business Logic | `frontend/src/features/*/hooks.ts`, `store.ts`, `entities/` | カスタム hooks・状態 |
| Presentation-UI | `frontend/src/features/*/components/`（Client Component）+ `src/app/`（page.tsx は薄く） | UI |

## フロント横断コード（shared / hooks）と共通化

feature 間で使う横断コードは `frontend/src/shared/` に集約する。
**shared は feature を import しない**（依存は feature → shared の一方向）。

| ディレクトリ | 入れるもの |
|----|------|
| `shared/ui/` | 汎用・ドメイン非依存の presentational コンポーネント（Button, Modal, DataTable 等） |
| `shared/hooks/` | 横断カスタム hooks（useDebounce, useDisclosure 等。ドメイン語彙を含まないもの） |
| `shared/lib/` | 純粋関数・ヘルパー（format, validators 等。副作用なし） |
| `shared/api/` | orval `generated/`（編集禁止）+ `mutator.ts` |
| `shared/theme/`, `shared/i18n/` | デザイントークン・翻訳 |

### hooks の置き場
- feature 固有のロジック・データ取得（TanStack Query wrap）→ `features/*/hooks.ts`
- ドメイン語彙を含まない汎用 hook → `shared/hooks/`
- 判断軸：「他 feature でも使うか／ドメイン語彙を含むか」

### 共通コンポーネント化の判断基準（早すぎる抽象化を避ける）
- **Rule of Three**：同じ UI が **3 箇所目**に出たら `shared/ui/` へ抽出（1〜2 箇所は feature ローカルで許容）
- 抽出対象は presentational（見た目・操作）のみ。差分は **props で吸収**する
- **API 呼び出し・ビジネスロジック・ドメイン語彙を持つ UI は feature に残す**（`features/*/components/`）
- 迷ったら feature ローカルに置き、重複が確定してから昇格する

## 1 スライスの実装順序（依存内側 → 外側）

### Web スライス
```
1. Pydantic DTO（型定義・テスト不要）
2. Repository        RED → GREEN
3. Service           RED → GREEN（Repository は mock）
4. API endpoint      RED → GREEN
5. 【統合ポイント】OpenAPI 出力 → orval 再生成 → typecheck
6. features/*/api.ts, hooks.ts   RED → GREEN
7. features/*/components + app/ の page  RED → GREEN
```

### エージェントスライス（詳細: `.claude/skills/build-loop/agent-slices.md`）
```
1. ツール（tools.py）       RED → GREEN（決定的関数として。repository/service は mock）
2. definition / ガードレール  agent-plan.md の写し + PreToolUse hook（implementer）
3. API 接続（jobs 経由）     RED → GREEN（POST 202 + run_id / GET ポーリング）
4. 【統合ポイント】OpenAPI 出力 → orval 再生成 → typecheck
5. features/*（ポーリング UI）RED → GREEN
6. ミニ評価: 正常系シナリオ1本を実行しトレースを agent-plan.md と突き合わせ（orchestrator）
```

## 統合ポイント（orchestrator が Bash で実行）

```bash
cd backend && uv run python scripts/export_openapi.py -o openapi.json
cd frontend && npm run orval
cd frontend && npm run typecheck
```

## stack コマンド

| 用途 | Backend | Frontend |
|------|---------|----------|
| format | `cd backend && uv run ruff format app tests` | `cd frontend && npx prettier --write "src/**/*.{ts,tsx}"` |
| lint | `cd backend && uv run ruff check --fix app tests` | `cd frontend && npm run lint` |
| 型 | （ruff/pyright 準拠） | `cd frontend && npm run typecheck` |
| test | `cd backend && uv run pytest tests/ -v` | `cd frontend && npm run test` |

## reviewer チェックリスト（Sprint 3）

### 依存ルール
- [ ] `services/` が ORM（SQLAlchemy）を直接参照していない（Repository 経由）
- [ ] `endpoints/` にビジネスロジックが漏れていない
- [ ] 内側の層が外側の層を import していない

### AI Agent 固有（エージェントスライスのとき）
- [ ] 使用ツールが agent-plan.md「ツール一覧」の範囲内（表にないツールを実装していない）
- [ ] definition.py の値（完了条件・max_turns・タイムアウト）が agent-plan.md と一致
- [ ] ガードレールが PreToolUse hook / disallowed_tools で強制されている（お願い止まりでない）
- [ ] 起動が `jobs.start_agent_job()` 経由（HTTP で `run_agent()` を同期 await していない）
- [ ] タイムアウトの大小関係（無応答 < 内側 < 外側）を崩していない
- [ ] トレースを通らない実行経路がない
- [ ] ツール内に生 SQL・生 HTTP がない（repository/service 経由）
- [ ] エージェントループの単体テストを書いていない（ツールのみテスト）

### Frontend 固有
- [ ] `shared/api/generated/`（orval 生成）を編集していない
- [ ] feature 間の直接 import が無い（`index.ts` 経由のみ）
- [ ] JSX 内に日本語直書きが無い（`t()` 使用）
- [ ] デザイン値のハードコードが無い（`theme/tokens.ts` 経由。真実源は `docs/requirements/03-spec.md` 3章）
- [ ] UI を含むスライスは `.claude/rules/design-guidelines.md` の reviewer チェックリストを併用して確認した
- [ ] Client Component に `"use client"` が明示されている（page.tsx は薄く Server Component のまま）
- [ ] 3 箇所以上重複する UI が `shared/ui/` に抽出されている（早すぎる共通化も NG）
- [ ] `shared/` 配下が特定 feature を import していない
- [ ] カスタム hook が適切な場所にある（feature 固有 → `features/*/hooks.ts` / 横断 → `shared/hooks/`）
- [ ] `shared/ui/` に API 呼び出し・ビジネスロジックが無い

### テスト品質
- [ ] 正常系・異常系の両方がある
- [ ] 各層のテストが責務に限定されている（下位は mock）
- [ ] 非同期テストが正しく書けている（pytest-asyncio）

## テストと層の対応

| 層 | テスト対象 | 下位依存 |
|----|-----------|---------|
| Repository | DB 入出力 | テスト用 DB / fixture |
| Service | ビジネスルール | Repository を **mock** |
| Agent tools | ツールの入出力（決定的関数） | repository/service を **mock** |
| API | 入出力契約・ステータス（202 + run_id 等） | Service / jobs を mock 可 |
| hooks | データ取得・状態（ポーリング含む） | api.ts / MSW を mock |
| components | UI 挙動 | hooks を mock |
| **エージェントループ** | **単体テスト対象外** | 評価シナリオ + トレースで検証（`agent-development.md` §4） |
