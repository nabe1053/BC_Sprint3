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

## 0b. 常駐ループ（2026-09-12 研修者決定・memory AD-014 案 B）

Codex はこのループで動く。研修者の中継を待たない。

```
1. 本ファイル §7「次にやること」を読む（見出しの更新時刻を控える）
2. §7 の最優先タスクを1つ実施する（WIP=1。§7 に無いことはしない）
3. `make check`（BE のみなら check-be / FE のみなら check-fe）green と handoff の
   「レビュー対応」表・「再レビュー依頼」を書いて止まる（commit はしない）
4. §7 の見出しの更新時刻が変わるまで待つ（例: 60 秒ごとに `head -n 140 docs/reviews/CODEX-INSTRUCTIONS.md | grep '^## 7'`）。
   変わったら 1 へ戻る。§7 に「停止」と書かれていたら終了する
```

Claude（orchestrator）は handoff を監視し、レビュー結果を §7 に書いて更新時刻を変える。
§7 の更新前に次のタスクを推測して着手しない。研修者確認が要る判断（設計・破壊的操作・D05）は
§7 に「研修者確認待ち」と書かれるので、その間は待つ。

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

### 着手タスク C-1（**完了・2026-09-12 RV-026。以下は履歴**）

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

## 7. 次にやること（2026-09-12 23:10・T-204 DONE・G2 が縦に1本通った）

- **T-204 → DONE**（memory RV-028、commit `58f79f0`）。G1 全部・G2 全部・C-1 が閉じた
- **Claude が G2 ミニ評価を実施中**（実ジョブ 1 本を起動しトレースを agent-plan.md と突き合わせ。`backend/app/**` と DB は Claude が触っている）。
  その間 Codex は **タスク K（C-2）** の「サーバー非依存の項目」だけ進める。**`backend/app/` 配下は触らない**（ミニ評価の対象が動いているため）
- 完了合図: handoff 見出し `## C-2（タスク K）` ＋ 末尾 `再レビュー依頼`。ファイルは `docs/c2-handoff.md`

### タスク K: C-2 整理 chore（記録のみ P3 のまとめ。振る舞い不変）

対象は memory TODO-010 / TODO-012 のうち **`backend/app/` を触らないもの**（TODO-009 と TODO-011 ① は次ラウンド）:
1. Makefile: `.NOTPARALLEL:` を追加（`-j` 継承でゲート順序が崩れる。RV-023）/ `INDEX_TEST_URL` 等を target-specific export に /
   `export` 行を `TEST_DB :=` の後ろへ。`test_regression_gate.py` の make 起動は `MAKEFLAGS` を空にして呼ぶ
2. `scripts/check_scan_index.py`: 環境変数欠落時の `KeyError` を「`make check-run-step-index` から実行してください」の `SystemExit` に
3. リネーム（`git mv`・CV-017）: `scripts/check_t202_postgres.py` → `check_run_metadata.py`、
   `tests/integration/test_api_path_separation_t102.py` → `test_api_path_separation_live.py`。参照追従（Makefile・docs は履歴のまま）
4. `tests/integration/conftest.py`: SQLite `@compiles` と共有 metadata 書換を `tests/fixtures/sqlite_support.py` に切り出しコメント明示 /
   `TestConnection` → `SyncConnectionAdapter`、`test_connection` → `_connection` / seeded の `case_code="T202"` → `"SEED-CASE"`
5. テスト間 import の解消（CV-021）: `integration/test_agent_run_lifecycle.py` `integration/test_draft_repository.py` が `tests.unit.*` から取る
   ビルダ（`item` / `header` / `item_data` / `header_data`）を `tests/fixtures/` へ移す。`test_actual_application_path_separation_under_isolated_settings`
   の改名と `runpy` 二重実行の解消
6. FE: `features/agent-runs/components/__tests__/IntakeRecovery.test.tsx` → `features/documents/components/__tests__/` へ（RV-028 P3-6。
   `@/features/documents/hooks` の深い mock は index 経由か同 feature 内からの参照に）
7. 完了条件: **振る舞い不変の 3 点証明**（import 行を除く旧新 diff・テスト関数名の集合・assert 総数が一致。LN-032）＋
   `DEBUG=false CI=true make check` all green（BE 404 / FE 166）＋ `docs/c2-handoff.md`。commit しない。
   **注意**: `make check` は Claude のミニ評価と DB（octg_test）を共有しない（開発 DB は octg_db）が、pytest の同時実行は避ける（LN-027）。
   Claude が `backend/app` を触っている間に `make check-be` が失敗したら、再実行せず handoff に時刻と出力を書いて止まる

### C-2 の後（着手は §7 更新待ち）
- TODO-009 / TODO-011 ①（`backend/app/` を触る整理）→ G3 T-301（BE）。並行可は T-401（§5）

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
