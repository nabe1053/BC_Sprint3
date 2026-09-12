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

## 7. 次にやること（2026-09-12 15:40・T-203 1回目 / T-201 6回目レビュー後に更新）

再レビュー結果（Claude reviewer 2体・独立実行。詳細と orchestrator の判断は
**`docs/reviews/g2-review-2026-09-12-2.md`** — 着手前に全文を読む）:

- **T-203 → DONE 不可**（P1 1 / P2 5 / P3 6）。memory RV-020
- **T-201 → DONE 可（条件付き）**（P2 1 / P3 5）。memory RV-021。条件 = 下記タスク B
- **T-202 → DONE**（RV-018）。触らない

**今回のラウンドで A → B → C を1サイクルで直し、`make check-be` green を貼って再レビュー依頼する。**
全体回帰の保留は解除済み（研修者承認・t203-handoff 冒頭）。`DEBUG=false make check-be` を最終差分で必ず実行する。

### タスク A: T-203 RV-020 の修正（最優先）

1. **P1 — URL ガードレールの過剰遮断（`app/agent/hooks.py:69`）**: コードを直す。agent-plan AE06 は変えない。
   - URL 検査は「取得・送信の意図を持つ引数」（読取系ツールのスカラ引数）に限定する。
     記録系ツールの原文フィールド（`quote` / `excerpt` / `reason` / `*_raw`）は検査対象から外す
   - RED: 原文に `https://…` を含む `record_question` / `record_evidence` / `record_source_inventory` が
     **成功**する単体テストを書き、現コードで失敗を確認してから直す
   - ミニ評価にシナリオ `ae06_url_in_source` を追加（原文中に URL 指示がある資料 → `completed`、
     確認事項に当該記述が残る、外部取得の呼出しがトレースに無い）
   - 未登録ツール拒否と外部 URL 拒否を区別する固定コード（`E_TOOL_NOT_REGISTERED` /
     `E_EXTERNAL_LINK_BLOCKED`）を `observation.code` に載せる（P3-2 を同時に閉じる）
2. **P2-1 / P2-2 — 設計書追記で閉じる（実装変更なし）**: agent-plan.md「T-203 ローカル実行の具体化」節に
   停止理由の内訳 `tool_rejected` と管理イベント `guardrail_denied` を明記。04-db.md §3.2 補足の一覧に
   `tool_rejected` / `local_dummy_unsupported` / `validation_unresolved` と `guardrail_denied` を追記。
   追記した行を handoff に引用する
3. **P2-3 — `stage_detail` を `資料 n/N` の材料にする**（`agent_tool_repository.py:281-282`）:
   読取段階は `{"documentsRead": x, "documentsTotal": N}` 相当（`list_case_documents` の件数と
   `read_*` の進捗から算出）。固定診断コードとの混在をやめる形を handoff で説明。T-204 が直接依存する
4. **P2-4 — 旧 `app/agent/trace.py`（`TraceRecorder`）を削除**。**削除は本指示で承認済み**。
   `tools.py` の `digest_args` 二重定義も解消。参照 0 を `grep` で確認して handoff に貼る
5. **P2-5 は記録のみ**（既定ダミー方針では同一違反3回ループに到達しない）。handoff「残件」に
   「実モデル接続時に方針側へ自己修復ループを実装」と明記
6. P3-1（`ping` / `SYSTEM_PROMPT` / `build_hooks` の未使用にコメント）・P3-3（`CANCEL_CLEANUP_S` と
   `CANCEL_GRACE_S` の二重定数）・P3-5（hook に `HookContext` を渡す）は安いので同時に閉じる。
   P3-4（`read_email` の `email:*` 全走査）は要確認として記録のみ

### タスク B: T-201 RV-021 の条件（Makefile 1行）

- `check-be` の依存に `check-run-step-index` を追加する（`Makefile:30` 付近）。理由は RV-021 P2
  （`create_all` の conftest では migration 差分を検出できず、自動で守るものがゼロ）。
- できれば `tests/integration/` にテスト DB の `pg_indexes` を読むテストを1本（`be-test` に入る）。
- P3-1（`add_run_step_locator_index.py` の downgrade を `pass`＋所有者コメントに）・P3-4（接続先の
  直書きを Makefile の変数から渡す）は同時に閉じてよい。P3-2/3/5 は記録のみ。
- これを直した時点で **T-201 は DONE**（Claude が memory を更新する）。

### タスク C: 再レビュー依頼の書き方

- `docs/t203-handoff.md` / `docs/t201-handoff.md` の冒頭に「レビュー対応（RV-020 / RV-021）」表:
  指摘番号 / 変更ファイル:行 / RED を確認した検査・コマンド・件数 / 変異内容1行（LN-009）
- 最終差分で `DEBUG=false make check-be` と `DEBUG=false make agent-eval`（14 ケース: 既存 13 + ae06）の
  実出力を貼る。範囲を切った実行を「検証した」と呼ばない（CV-016）
- 末尾に「再レビュー依頼」と希望 Status を書いて**止まる**。T-204・C-1・G3 には進まない

### タスク C-1 / D / E（T-203 完了後）

- C-1（チケット名ファイルの正規配置への移動・§3）は T-203 DONE 後に着手。`dependencies_t202.py` /
  `routes_t202.py` / `tests/t201` `tests/t202` / `check_t201_postgres.py` / `orval.t202.config.ts` /
  `tsconfig.t202.json` が対象（CV-017）。振る舞い不変・`make check` green のまま
- T-204（ポーリング UI）は T-203 DONE ＋ Claude の指示後。T-103 との先後は Claude が決める

### タスク F: T-103（G1 FE）の指摘修正 — 指示書は `docs/t103-instructions.md`

RV-019（P1 5 / P2 8 / P3 5 ＋ 未完成 9）の修正内容・優先順・完了条件を**指示書に確定済み**。
着手するときはそちらを読む（本節に内容を二重化しない）。前提の決定は AD-013・AD-009・AD-008・AD-005。

- **WIP=1 を守る**（§2）。T-201 / T-203 のレビュー対応中は着手しない
- 実施順（AD-011）では G2 を縦に通すのが先。T-103 は **T-204 と同じ FE なので、
  どちらを先にやるかは Claude が指示する**（勝手に並行しない）
- 完了条件は `make check-fe` green ＋ design-lint 違反ゼロ ＋ `docs/t103-handoff.md` の
  レビュー対応表（指摘ごとに 変更ファイル / RED→GREEN の実結果 / 実行コマンドと件数）

### 別スライス候補（今はやらない・記録のみ）

`case_service.py` / `document_query_service.py` / `document_intake_service.py` が `app.models`（ORM）を
直接 import しており `clean-architecture.md`「services が ORM を直接参照していない」に抵触する
（T-101/T-102 由来）。Claude が改修スライスとして memory §3 に積むまで着手しない。
