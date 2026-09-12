# Codex セッション作業規約（2026-09-12 改訂・研修者決定）

**実装は主に Codex が担当する。**Claude メインセッション（orchestrator 役）は、スライスの指示・
レビュー起動・memory 転記・品質ゲートの実行を担当し、原則としてコードを書かない。
この文書が Codex 側の恒久ルール。着手前に必ず読むこと。

---

## 0. 役割分担（これを崩さない）

| 担当 | やること | やらないこと |
|------|---------|-------------|
| **Codex（実装）** | RED テスト → 実装 → REFACTOR、レビュー指摘の修正、handoff の更新 | `.claude/memory.md` の編集、レビュー、スライスの取捨選択、commit |
| **Claude（orchestrator）** | スライス指示、reviewer 起動、memory 転記、`make check`、commit | 実装（指摘修正の代行を含む） |

- 自分が書いたコードを自分でレビューしない（CLAUDE.md 憲法6）。レビューは必ず別エージェント。
- **`.claude/memory.md` は読むだけ。編集しない。**進捗・決定・学び・希望 Status は
  `docs/t{ID}-handoff.md` に書き、Claude が memory へ転記する。
  理由: 同時追記で RV/LN の ID 衝突と Status 上書きが実際に起きた（memory §6 TODO-004）。

---

## 1. 品質ゲートは `make check`（2026-09-12 新設）

**リポジトリ直下の `Makefile` が検証の単一入口。**個別コマンドを手で組み立てない。

```sh
make check-be   # BE だけ触ったスライス（db 起動 → migration → ruff → pytest 全体）
make check-fe   # FE だけ触ったスライス（openapi → orval → tsc → eslint → jest）
make check      # スライス完了時のフルゲート
```

守ること:

- **`--confcutdir` や専用 tsconfig で範囲を切った実行を「検証した」と呼ばない。**
  切り出し実行は作業中の高速フィードバック用。**再レビュー依頼の根拠には `make check` の出力を貼る。**
- **ORM に列を足したら、同じ手順の中で `make migrate` を実行する。**
  `tests/conftest.py` が `Base.metadata` で TRUNCATE するため、モデルだけ先行すると
  無関係な既存統合テストが全滅する（memory LN-013）。
- **migration は開発 DB（octg_db）にも適用する。**統合テストは `TestClient` の lifespan で
  アプリ本体のエンジン（`settings.DATABASE_URL` = octg_db）に触るため、開発 DB のスキーマが
  古いと `tests/integration` が全滅する。`make migrate` は両方に適用する（memory LN-017）。
- 全体回帰を「保留」にしない。保留した結果、4回目のレビューで 44 ERROR が出た（RV-015 P1-1）。

---

## 2. WIP は 1（同時に触るスライスは1つ）

- 着手中のスライスを閉じるまで次に進まない。「A の指摘修正中に B を実装」をしない。
- 例外: Claude が **明示的に並行スライスを指示した場合のみ**（§5）。
- 1スライスの終わり = `make check` green ＋ handoff 更新 ＋「再レビュー依頼」の記入。そこで**止まる**。

---

## 3. ファイル配置の規約（チケット名をファイル名に入れない）

`routes_t202.py` のようなチケット名つきファイルは、チケットが閉じた瞬間に意味を失い、
次のスライスがどこに書けばいいか分からなくなる。**以後、新規ファイルにチケット ID を含めない。**

正の配置（既存の T-101/T-102 の構造に合わせる）:

| 種類 | 置き場 |
|------|--------|
| AGENT 名前空間のエンドポイント | `app/api/agent/endpoints/{資源}.py` |
| UI 名前空間のエンドポイント | `app/api/ui/endpoints/{資源}.py` |
| 名前空間ごとの DTO | `app/api/{agent,ui}/schemas/{資源}.py` |
| 両名前空間で共有する DTO / ハンドラ | `app/api/common/` |
| 横断の DI・lifespan | `app/api/dependencies.py` |

### 着手タスク C-1（優先度: T-203 の前）

以下をリネーム＋import 追従する。**振る舞いを変えない**（純粋な移動。`make check` が green のままであること）。

```
app/api/routes_t202.py        → app/api/common/route_errors.py
app/api/dependencies_t202.py  → app/api/dependencies.py
app/api/schemas_drafts.py     → app/api/common/schemas/drafts.py   （#20 は UI/AGENT 共有のため common）
app/api/schemas_runs.py       → app/api/ui/schemas/agent_runs.py   （#12-14 は UI 名前空間）
backend/tests/t201/           → tests/unit/ ・ tests/integration/ へ層ごとに配分
backend/tests/t202/           → 同上
frontend/orval.t202.config.ts → 削除（`orval.config.ts` に一本化）
frontend/tsconfig.t202.json   → 削除（`npm run typecheck` に一本化）
backend/scripts/export_openapi_isolated.py → 削除（`scripts/export_openapi.py` に一本化）
```

- テストの移動先は `.claude/rules/clean-architecture.md`「テストと層の対応」に従う
  （Repository/API の実 DB を使うもの → `tests/integration/`、決定的関数 → `tests/unit/`）。
- 移動でテストが落ちる場合、**落ちる理由を handoff に書く**。隔離設定を復活させて隠さない。
- `orval.config.ts` の `clean: true` で G1 の生成物が消える懸念がある場合は、
  消えるファイル名を handoff に列挙して Claude の判断を仰ぐ（勝手に `clean: false` を常設しない）。

---

## 4. 「1箇所に集約」はテストで固定した（消さないこと）

`backend/tests/unit/test_single_source_of_truth.py` が以下を機械的に検査する（memory CV-015）。

- 停止閾値・モデル識別子は `app/agent/definition.py` のみ（外での数値リテラル・文字列直書きを検出）
- `E_*` → HTTP status の対応表は `app/api/errors.py` のみ
- `storage_path` は `resolve_readable_path()` の引数としてのみ現れる

同種の「集約したのに複製された」指摘が出たら、**修正と同時にこのファイルへ検査を1つ足す**。
`tests/unit/test_api_path_separation.py` と合わせて、この2本は**削除・弱体化禁止**。

---

## 5. 並行作業の規則（同一スライスに2人を入れない）

- **同じスライスを2セッションで実装しない。**衝突の実績あり（memory TODO-004・LN-015）。
- 並行してよいのは、Claude が明示した**依存が独立で、触るファイルが重ならないスライス**だけ。
  現時点で並行可能なのは `T-301`（G3 BE）と `T-401`（G4 BE）— どちらも依存は T-201 のみ。
  並行指示が出たときは、handoff 冒頭に**自分が触るファイルの一覧**を先に書いてから着手する。
- 共有ファイル（`app/main.py` / `app/api/errors.py` / `app/models/__init__.py` /
  `alembic/versions/` / `docs/requirements/*`）を並行スライスで同時に編集しない。
  必要になったら handoff に書いて Claude に調停を依頼する。
- レビュー中は作業ツリーを触らない（レビュー対象がレビュー中に変わった実績あり: LN-015）。

---

## 6. 修正報告の書き方（自己申告を通さないための最低要件）

handoff の「レビュー対応」表に、指摘ごとに次の3列を書く。

| 指摘番号 | 変更内容（ファイル:行） | RED を確認したテスト名 と 実行コマンド・件数 |

- 「直した」だけの報告は再レビューで通らない（memory LN-006）。
- **実応答（HTTP レスポンス）をアサートするテストが無い箇所は、直っていないものとして扱う。**
- テストの強度は「変異させたら落ちるか」で示す（memory LN-009）。変異内容も1行で書く。
- 既存テストを**変更・削除した場合は必ず理由を書く**。レビュアーは改竄を疑って見る。

---

## 7. 次にやること（2026-09-12・再レビュー後に更新）

再レビュー結果（Claude reviewer 2体・独立実行）:

- **T-202 → DONE 可**（P1 0 / P2 0 / P3 6）。memory RV-018。もう触らない
- **T-201 → DONE 不可**（P2 1 / P3 4）。memory RV-017

### タスク A: T-201 の残 P2 — 索引が実 DB に存在しない（最優先）

`ix_agent_run_steps_document_locator` の `create_index` を、**すでに適用済みのリビジョン
`t201_artifacts` の中**に追記したため `alembic upgrade head` では作成されない。
実測（orchestrator）: 開発 DB octg_db には索引があり、**テスト DB octg_test には無い** —— DB 間で
スキーマが分岐している。

やること:

1. `alembic/versions/t201_artifacts.py` に後から足した `create_index`（28-33 行付近）を**取り消す**
2. **新規リビジョン**（`down_revision = "t202_run_metadata"`）を作り、そこで `create_index` する
3. `make migrate` で両 DB に適用し、**実スキーマで確認した出力を handoff に貼る**:
   `docker exec octg_postgres psql -U postgres -d octg_test -c '\d agent_run_steps'`
4. `tests/t201/test_draft_repository.py` の `test_scan_index_exists_in_model_and_migration` は
   **migration のソース文字列しか見ておらず false green**（`tests/t201/conftest.py` が
   `create_all` でスキーマを作るため、適用差分を原理的に検出できない）。
   実スキーマの確認は `check_t201_postgres.py` 側へ移す

> **恒久ルール（memory LN-018）**: 適用済みの Alembic リビジョンを後から編集しない。
> スキーマ変更の「完了」は migration のソース検査ではなく、**実 DB の `\d {table}` で確認する**。

### タスク B: T-201 の P3（安いので同時に閉じてよい）

- `tests/t201/test_draft_repository.py:87` 残範囲を件数でなく**集合の完全一致**でアサート
- `draft_repository.py:300-302` の「`read_email` が `email:` 以外を出した」「`read_document` が
  `email:` を出した」の**否定側テスト**を1本ずつ
- `email_parts` の `UNIQUE(document_id, part_role, seq)` 未追加（memory TODO-007）は
  T-203 着手前に**制約を足すか判定側で重複を弾くか**を handoff で提案する

### タスク C-1: チケット名ファイルの正規配置への移動（§3 参照）

振る舞い不変。`make check-be` green のまま完了させる。

### タスク D: T-203 の前に決めること（実装しない。handoff で提案し、Claude の決定を待つ）

- **旧 `app/agent/runner.py` / `trace.py` / `hooks.py` と新 `RunTraceStore` のどちらを正にするか**。
  現状 runner/trace はどこからも import されておらず、`hooks.py` は単体テストからのみ呼ばれる。
  つまり **ガードレールは未接続**で、「hooks で強制」（agent-development.md §5）は成立していない
  （memory TODO-006）。T-203 で `RunDispatcher` に差し込む設計を先に出す
- `stage_detail` の診断コードを上書きしない形（配列 or 別列）にするか（RV-018 P3-①）
- run ロック中のツール step 採番と `trace.sync()` の呼び出し頻度（RV-018 P3-②③）

### タスク E: T-203 本体（A〜D 完了後）

- 手順書: `.claude/skills/build-loop/agent-slices.md`
- 設計の正: `docs/requirements/agent-plan.md`。**ここに無いツール・完了条件・ガードレールを実装しない**
- `docs/t202-handoff.md`「T-203 への接続点」の `RunDispatcher` 契約を守る
- **エージェントループの単体テストを書かない**（ツール＝決定的関数のみ。ループは評価で検証）
- **locator は `email:{part_role}:{seq}`**（eml に `body:N` を使わない。memory CV-002 訂正済み。
  `body:N` を出すと完了条件が永久に満たせない）
- D05（外部 LLM 送信未承認）を維持。SDK の実送信経路を有効化しない

T-203 が終わるまで G3〜G6 には進まない（memory AD-011）。

### 別スライス候補（今はやらない・記録のみ）

`case_service.py` / `document_query_service.py` / `document_intake_service.py` が `app.models`（ORM）を
直接 import しており `clean-architecture.md`「services が ORM を直接参照していない」に抵触する
（T-101/T-102 由来）。Claude が改修スライスとして memory §3 に積むまで着手しない。
