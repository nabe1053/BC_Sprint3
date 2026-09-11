# Training Sprint 3 - 開発ガイド（memory 駆動ハーネス）

Sprint 3 のテーマは **AIエージェント構築**。Web アプリ（Next.js + FastAPI）はエージェントを
動かすための器であり、主役はエージェント（`backend/app/agent/`・設計の正は `docs/requirements/agent-plan.md`）。
実行はすべて**ローカル環境**（クラウドデプロイなし）。
実装は **memory 駆動の手動スライスループ**で、クリーンアーキテクチャ＋TDD を守りながら進める
（`/build-loop` は使わない — 決定事項5）。

## ハーネスの憲法（最重要・全エージェント遵守）

1. **`.claude/memory.md` が単一の真実源（進捗・決定・知恵）。** 作業前に必ず読む。
   **更新できるのは実装を指揮するメインセッション（以下 orchestrator 役）だけ**。
   サブエージェント（test-designer / implementer / reviewer）は**読むだけ**で、
   指摘・学びは戻り値で返し orchestrator 役が追記する（規約: `.claude/rules/memory-protocol.md`）。
2. **実装はスライス単位の手動ループで回す**（`/build-loop` は使わない。下記「実装フロー」）。
   1スライス = 1ユーザー機能を Presentation → Business Logic → Data Access まで縦に貫く単位。
   スライスの粒度・依存順・Status は memory §3 バックログで管理する。
3. **クリーンアーキの依存ルール厳守**（内側は外側を知らない）: `.claude/rules/clean-architecture.md`
4. **TDD 必須**: RED（テスト失敗）を確認せず GREEN に進まない: `.claude/rules/tdd-guide.md`
   例外: **エージェントループは単体テストしない**（ツール=決定的関数のみが対象。ループは評価で検証）。
5. **エージェント開発の原則**（`.claude/rules/agent-development.md`）:
   - 設計が正（agent-plan.md に無いものを実装しない）
   - すべての実行をトレース（`backend/traces/{run_id}.jsonl`）に記録
   - ガードレールは hooks で強制（お願いにしない）
   - タイムアウトは2層（無応答 < 内側 < 外側=`jobs.py`）。ハングは外側が必ず回収
   - 起動はジョブ経由（POST 202 + run_id → GET ポーリング。HTTP で完了を同期待ちしない）
6. **レビュー・ゲート**: 実装した本人はレビューしない。スライスの実装が終わったら、
   **必ず reviewer サブエージェントを Task 起動する**（手動ループでも省略しない。自分で書いた
   コードを自分でレビューしたことにしない）。指摘は implementer（または orchestrator 役）が修正し、
   指摘ゼロになるまで次スライスに進まない（修正 3 回を超えたら BLOCKED 記録）。
7. **必ず終端する**: 詰んだスライスは `BLOCKED` として memory §6 に記録し、依存のない他スライスへ進む。
   手動ループなので**スライスの区切りで研修者に確認を取る**（自律周回はしない）。
8. **中断復帰**: memory §3 の Status から再開できる。

## 実装フロー（手動・スライス単位）

`/build-loop` は使わず、以下を1スライスずつ手で回す。各ステップの中身は既存ルールが正。

```
① memory.md + 設計書(01〜06, agent-plan.md)を読む
   → 未着手ならスライスに分割し memory §3 バックログへ（全部 Status=PLANNED）
② 次スライスを選ぶ（依存が DONE のもの。エージェントのツールが使う API/テーブルを
   提供する Web スライスを、エージェントスライスより先に）→ Status=IMPLEMENTING
③ 層順に TDD（層→dir 対応・実装順序は `.claude/rules/clean-architecture.md`）
     Web:   DTO → Repository → Service → API →【統合】→ api.ts/hooks → components/page
     Agent: tools → definition/ガードレール → jobs経由API →【統合】→ ポーリングUI
            （手順の詳細は `.claude/skills/build-loop/agent-slices.md`）
   RED（失敗を目で確認）→ GREEN → REFACTOR。型定義のみ例外。
   【統合】= OpenAPI 出力 → orval 再生成 → typecheck（コマンドは clean-architecture.md）
④ reviewer サブエージェントを Task 起動（read-only・指摘のみ）→ Status=REVIEWING
   → 指摘を修正（Status=FIXING）→ 指摘ゼロで次へ。3 回超過は BLOCKED
⑤ エージェントスライスはミニ評価（正常系1本をジョブ実行し、トレースを agent-plan.md と突き合わせ）
⑥ memory へ記録（§1 決定 / §4 指摘 / §5 学び / §3 Status=DONE）＋ 品質ゲート＆ `/git-commit`
⑦ ② に戻る（未完スライスが無くなれば初版完成 → Phase 3 エージェント評価へ）
```

> test-designer / implementer / reviewer は build-loop 経由でなくても Task で個別に起動してよい。
> レビュー（④）だけは必ず別エージェントに投げる（憲法6）。

## 開発フロー全体

```
Phase 0: セットアップ      r2b-build-sprint3（本テンプレ配置）
Phase 1: Foundation       foundation エージェント（Slice 0-1〜0-7・ループ外）
                          ※本プロジェクトは **Slice 0-4（JWT 認証）をスキップ**（下記の決定事項）
                          0-7 = /foundation-agent-setup（app/agent/ スケルトン・トレース・
                          タイムアウト2層・ジョブの型・疎通テスト）
Phase 2: 実装ループ        手動スライスループ（上記「実装フロー」。初版完成まで）
Phase 3: エージェント評価   06-scenario-test.md のエージェント評価シナリオを実行し、
                          トレース（backend/traces/）を agent-plan.md と突き合わせる（下記）
Phase 4: 継続改善          memory §3 に改修スライスを追加し、同じ手動フローで回す
                          （評価 Fail の修正も同様）
Phase 5: 開発環境の設定     /r2b-env-sprint3（評価の自動化などを自分の skill として作る）
```

### Phase 3: エージェント評価のやり方

エージェントが**設計どおり**動いているかを検証する。単体テストでは検証できない
「エージェントループの振る舞い」は、シナリオ実行 + トレースで評価する。

1. `docs/requirements/06-scenario-test.md` のエージェント評価シナリオを順に実行し、判定欄に記録
2. 各実行の `backend/traces/{run_id}.jsonl` を開き、agent-plan.md と突き合わせる：
   - 使ったツールがツール一覧の範囲内か
   - ガードレール違反（禁止操作）がないか
   - 完了条件の「判定方法」どおりに終了したか（`*_timeout` / `max_turns` で終わっていないか）
   - フローが IPO 拡張表のスケッチから大きく乖離していないか
3. Fail は原因を 要件(02)・設計(agent-plan.md)・実装 に切り分け、memory §3 に改修スライスを追加して
   手動フローで修正する

> この突き合わせを毎回手でやるのが面倒だと感じたら、それが Env フェーズ
> （`/r2b-env-sprint3`）の出発点。評価ランナーやトレースレビューを**自分の skill として作る**
> レシピが用意されている。

## エージェント / スキル

### スキル
| スキル | 用途 |
|-------|------|
| ~~`/build-loop`~~ | 実装ループ本体 — **本プロジェクトでは使わない**（決定事項5）。`agent-slices.md` のみ参照する |
| `/foundation-backend-setup` | Slice 0-1: FastAPI 初期化（ループ外・基盤） |
| `/foundation-postgres-docker` | Slice 0-2: PostgreSQL Docker |
| `/foundation-database-setup` | Slice 0-3: ORM・マイグレーション |
| ~~`/foundation-auth-jwt`~~ | Slice 0-4: JWT 認証 — **本プロジェクトでは使わない**（決定事項1） |
| `/foundation-frontend-setup` | Slice 0-5: Next.js 15 + MUI |
| `/foundation-api-integration` | Slice 0-6: OpenAPI 出力・orval 再生成 |
| `/foundation-agent-setup` | Slice 0-7: Claude Agent SDK・`app/agent/` スケルトン・疎通テスト |
| `/git-commit` | 品質チェック後に commit |
| `/r2b-env-sprint3` | 開発環境の設定フェーズ（Env・Build 後） |
| `/design-spec` | 仕様＋モック（`./docs/requirements/mocks/mockup.html`）の作成・更新 |

### エージェント
| エージェント | 役割 | 呼び出し |
|------------|------|---------|
| **foundation** | Foundation Phase（Slice 0-1〜0-7）をガイド（ループ外） | プロンプトで起動 |
| **test-designer** | 🔴 RED: 失敗するテストを層ごとに設計（エージェントのツール含む） | orchestrator 役が Task |
| **implementer** | 🟢 GREEN/REFACTOR ＋ 指摘修正 | orchestrator 役が Task |
| **reviewer** | 🔵 実装範囲を独立レビュー（read-only・指摘のみ。agent-plan.md 突き合わせ含む） | **スライスごとに必須**（憲法6） |

> 旧構成（planner / fullstack-integration / 層別エージェント群 / agent-implementation スキル）は
> build-loop に統合・置換された（エージェントスライスの手順は `.claude/skills/build-loop/agent-slices.md`）。

## 技術スタック

| レイヤー | 技術 | 備考 |
|---------|------|------|
| **フロントエンド** | Next.js 15 (App Router) | ローカル起動（`npm run dev`） |
| **バックエンド** | FastAPI + Python 3.12 | ローカル起動（uvicorn）・クリーンアーキ3層 |
| **データベース** | PostgreSQL | ローカル Docker（docker-compose）※下記 |
| **AI エージェント** | Claude Agent SDK（`claude-agent-sdk`） | カスタムツール（in-process MCP）＋ hooks によるガードレール |
| **トレース** | JSONL（`backend/traces/{run_id}.jsonl`） | agent-plan.md の IPO 拡張表と同型。評価・進捗表示に使う |
| **ORM** | SQLAlchemy 2.0（AsyncSession） | 非同期対応 |
| **認証** | **実装しない**（Slice 0-4 スキップ） | 02 N02「認証なし・ローカル単一利用者の PoC」。下記「本プロジェクトの決定事項」参照 |
| **API クライアント** | orval + TanStack Query | OpenAPI から自動生成（`shared/api/generated/`） |
| **パッケージ管理（Python）** | uv | 高速・再現可能 |
| **テスト** | pytest + pytest-asyncio / Jest + RTL | ツールは決定的関数として単体テスト |

> **Docker / DB 構成（Sprint 3 の決定事項）**
> - DB は **PostgreSQL**、起動は **docker-compose**（`docker-compose up -d`）。Sprint 1/2 と同一スタック
> - **Sprint 3 で Docker を使うのはこの DB 起動のみ**。アプリのコンテナ化・デプロイには使わない
>   （backend/Dockerfile はローカル再現用の任意成果物）
> - PostgreSQL を継続する理由: エージェントのジョブ（裏で実行状態を書く）と API（読む）の
>   並行アクセスに強い・JSONB がツール入出力/実行ログに合う・将来 pgvector に拡張できる

## 本プロジェクトの決定事項（設計フェーズからの引き継ぎ）

設計成果物（`docs/requirements/`）のうち、Build に影響する決定を明示する。**判断に迷ったら設計書が正**。

### 1. 認証は実装しない（Slice 0-4 をスキップ）

- 根拠: `02-requirement.md` 4章 **N02**「認証方式: なし（ローカル単一利用者の PoC）／担当者・上司・業務責任者は**記録上の役割であり、アクセス制御ではない**。確認者名は入力必須だが自己申告であり本人性は検証しない」
- したがって **`users` テーブル・パスワードハッシュ・JWT・Cookie 処理・ログイン画面をいずれも作らない**（`04-db.md` 0.1）
- 記録者名（担当者名・確認者名・修正者名・判断者）は**画面の入力値**として各記録テーブルの `recorded_by` に入れる。`NOT NULL` かつ空文字禁止（CHECK）で、**AI は補完しない**（`04-db.md` 0.2 原則5）
- `frontend/src/shared/api/mutator.ts` は**認証コードを除去済み**。テンプレート既定では 401 で `/api/v1/auth/refresh` を叩き `/login` へリダイレクトする**生きたコードパス**があり、存在しないエンドポイントを叩いていた。現在は非 2xx を `ApiError`（`code` つき）として投げるだけで、**リトライもリダイレクトもしない**（401 が返るのは実装の誤りなので隠さず可視化する）
- **代わりに守ること**: `05-api-ipo.md` 7.1 のとおり、エージェントが人の記録 API を呼べない境界は**認可ではなくツール登録とパス分離**で守る。**実装済み**: `/api/v1/agent/*`（AGENT-01 のツールが呼ぶ API のみ）と `/api/v1/ui/*`（画面が呼ぶ API。人の記録は必ずこちら）。版プレフィックスは `app/main.py` の `API_V1` 定数1箇所で管理する
- 分離が崩れたことは `backend/tests/unit/test_api_path_separation.py` が機械的に検出する（版プレフィックスの一元化・agent/ui のどちらかに属すること・人の記録 API が `/agent/*` に無いこと）。**このテストを消さないこと**

### 2. DB は PostgreSQL（設計書を修正済み）

- `04-db.md` は当初 SQLite 前提だったが、本テンプレートの構成（PostgreSQL on Docker）に合わせて**書き換え済み**
- 型は PostgreSQL の型で確定している。要件から決まる2つは変えないこと:
  - **`numeric`**（数量・寸法）— 浮動小数点を使わない。`06-scenario-test.md` の採点が「整数数量は厳密一致」を求めるため
  - **`timestamptz`**（すべての日時）— TZ を落とさない。見積期限の TZ を補わない方針と同じ理由
- CHECK 制約・部分UNIQUE索引・複合外部キーは **ORM のモデル定義だけでは表現しきれない**ため、Alembic のマイグレーションに明示的に書く（`04-db.md` 0.5）

### 3. 外部LLM への送信は未承認（D05）

- 初版は**ローカル読取＋ダミー応答**で実装・検証する。`agent_runs.model` にはダミー応答の識別子を入れる
- 実 LLM へ送るのは、送信先・送信範囲・保存条件が承認され、**ユーザーの事前確認を得た後**（`agent-plan.md` 3章・`02-requirement.md` D05）
- 送信対象は研修用架空データ `sample-01`〜`10` に限定。提案書・実業務資料・認証情報・対象外のローカルファイルは**除外**。フォルダ全体を送信対象にしない

### 4. 換算は無効のまま実装する（D03）

- `rule_sets.conversion_enabled` の既定は `false`。**換算値を保持する列を作らない**（作ると未承認換算が入り得る）
- 「換算しないこと」自体が評価対象（`06-scenario-test.md` TEST-06・AE03）。**換算値を1つでも出力したら不合格**

### 5. build-loop を使わない（手動スライスループで実装する）

- 実装は `/build-loop` の自律周回ではなく、**研修者が指揮する手動スライスループ**で進める
  （上記「実装フロー」）。理由: スライスごとに内容を確認しながら進めるため
- ただし**ハーネスの規律は落とさない**: memory.md 単一真実源・TDD の RED 先行・
  クリーンアーキの依存ルール・**別エージェントによるレビュー**は手動でも必須
- memory.md の編集者は **orchestrator 役（メインセッション）ただ1つ**。
  サブエージェントは読むだけ（同時書込による破壊を防ぐための規約）
- `.claude/skills/build-loop/agent-slices.md` は**エージェントスライスの手順書として引き続き参照する**
  （スキル本体 SKILL.md は使わない）

## ディレクトリ構造

```
training-sprint3/
├── .claude/
│   ├── memory.md                    # ★ハーネスの脳（進捗・決定・知恵。orchestrator のみ編集）
│   ├── settings.json                # 許可リスト・design-lint フック
│   ├── skills/                      # build-loop（agent-slices.md のみ参照）, foundation-*, git-commit
│   ├── agents/                      # test-designer, implementer, reviewer, foundation
│   └── rules/                       # clean-architecture, design-guidelines, memory-protocol, agent-development, tdd-guide
├── backend/                         # FastAPI
│   ├── app/
│   │   ├── api/v1/                  # endpoints / schemas（Presentation）
│   │   ├── core/                    # 設定・依存注入
│   │   ├── models/                  # ORM（Data Access）
│   │   ├── services/                # ビジネスロジック（エージェント起動もここから）
│   │   ├── repositories/            # Data Access
│   │   ├── agent/                   # ★AI エージェント（Claude Agent SDK）
│   │   │   ├── definition.py        #   システムプロンプト・完了/停止条件（agent-plan.md Part 1 に対応）
│   │   │   ├── tools.py             #   カスタムツール群（agent-plan.md ツール一覧と1対1）
│   │   │   ├── runner.py            #   実行ループ・max_turns・内側タイムアウト
│   │   │   ├── jobs.py              #   実行の型: バックグラウンドジョブ + run_id ポーリング（外側タイムアウト）
│   │   │   └── trace.py             #   トレースレコーダー（JSONL）
│   │   ├── middleware/              # 認証等
│   │   └── main.py
│   ├── scripts/export_openapi.py    # OpenAPI スキーマ出力
│   ├── tests/
│   ├── traces/                      # 実行トレース（{run_id}.jsonl・git管理外）
│   ├── openapi.json                 # OpenAPI スキーマ（自動生成・git管理外）。
│   │                                #   orval.config.ts の target がここを読む
│   ├── pyproject.toml               # uv 依存管理（claude-agent-sdk 含む）
│   └── .env                         # ANTHROPIC_API_KEY 等
├── frontend/                        # Next.js 15（App Router / FSD）
│   └── src/
│       ├── app/                     # ページ（page.tsx は薄く）
│       ├── features/                # 機能単位（api.ts / hooks.ts / components/ / index.ts）
│       ├── shared/                  # api(generated+mutator) / ui / hooks / lib / theme / i18n
│       └── entities/
├── docs/
│   ├── requirements/                # 設計ドキュメント（01〜06 + agent-plan.md。実装の入力）
│   └── env/                         # 開発環境カスタマイズ台帳（Env フェーズ）
└── docker-compose.yml               # PostgreSQL 開発環境
```

## クリーンアーキテクチャ（依存ルール）

```
Presentation（UI/API） → Business Logic（Service / Agent） → Data Access（Repository）
依存は常に「外側 → 内側」。内側は外側を知らない。逆流禁止。
```

- Backend: `api/(endpoints,schemas,middleware)` → `services/`（+ `agent/`） → `repositories/`(+`models/`)
- **Agent の位置づけ**: `app/agent/` は Business Logic。起動は service 層から `jobs.start_agent_job()`。
  ツールが DB に触るときは repository 経由
- Frontend: `app/ + features/*/components` → `hooks.ts/store.ts/entities` → `api.ts`(+`generated/`)
- 詳細・層→dir 対応・reviewer チェックリスト: `.claude/rules/clean-architecture.md`

## 画面モックについて

UI の全体像は仕様（基本設計）の一部として作成する。`/design-spec` を実行すると
全画面をまとめたモック `./docs/requirements/mocks/mockup.html` が生成される（再実行で更新可）。
`open ./docs/requirements/mocks/mockup.html` でブラウザ確認できる。

## Next.js 特有のルール

### Server / Client Component の使い分け

```typescript
// ❌ NG - データフェッチ hooks は Server Component で使えない
// app/(portal)/dashboard/page.tsx（デフォルト: Server Component）
const { data } = useGetApplications(); // エラー

// ✅ OK - Client Component に切り出す
// features/applications/components/ApplicationList.tsx
"use client";
export function ApplicationList() {
  const { data } = useGetApplications(); // OK
}
```

page.tsx は薄く保ち（Server Component のまま feature を組み立てるだけ）、
データフェッチ・状態は `features/*/components/`（`"use client"`）に置く。

## 重要なルール

### Frontend
- orval 生成コード（`shared/api/generated/`）は編集しない
- JSX 内に日本語を直書きしない（`t()` を使う）
- feature 間の直接 import 禁止（`index.ts` 経由）
- デザイン値をハードコードしない（`theme/tokens.ts`。トークンの真実源は `docs/requirements/03-spec.md` 3章）
- UIデザインのガードレール（色相2つルール・脱・標準MUI・3状態設計）: `.claude/rules/design-guidelines.md`
- Client Component には `"use client"` を明示
- 横断コードは `shared/` に集約：共通UI→`shared/ui/`・横断hook→`shared/hooks/`・純粋関数→`shared/lib/`（shared は feature を import しない）
- 共通化は **Rule of Three**（同じUIが3箇所目で `shared/ui/` へ抽出。早すぎる共通化はしない）

### Backend
- uv を使用（pip は使わない）
- 依存ルール厳守（endpoints → services → repositories、逆流禁止）
- テストなしの実装はしない

### AI Agent（詳細は `.claude/rules/agent-development.md`）
- **エージェント実行は `app/agent/` に閉じ込め、起動は service 層から `jobs.start_agent_job()` で**（endpoints から直接呼ばない）
- **HTTP で完了を同期待ちしない**: POST → 202 + run_id → GET /runs/{run_id} ポーリングが実行の型。進捗はトレース末尾を返す
- **すべての実行をトレースに記録する**（記録されない実行は評価できない）
- **完了条件は機械判定可能に**（agent-plan.md の「判定方法」をコードにする）
- **ガードレールは hooks で強制する**（プロンプトのお願いだけに頼らない）
- **タイムアウトは2層**: 内側（エージェントの停止条件）< 外側（`jobs.py` のフェイルセーフ）。
  ハングは外側が必ず回収する

## 困ったときは

- memory の書き方: `.claude/rules/memory-protocol.md`
- クリーンアーキ・reviewer チェックリスト: `.claude/rules/clean-architecture.md`
- UIデザイン: `.claude/rules/design-guidelines.md`
- エージェント開発: `.claude/rules/agent-development.md`
- エージェントスライスの実装手順: `.claude/skills/build-loop/agent-slices.md`
- TDD: `.claude/rules/tdd-guide.md`
