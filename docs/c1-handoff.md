# C-1 引き継ぎ（2026-09-12）

## タスクH対応（§7 20:45）

チケット名の付いたAPI・スキーマ・検査スクリプトと、T-201/T-202のテスト配置を整理した。**移動前後とも `DEBUG=false CI=true make check` がall green。BE404件・FE78件で一致する。** import/パス参照の置換以外のテストAST、assert 611か所、OpenAPIのJSON内容は移動前と一致した。コードの機能追加、テストのassert変更・削除、commitは行っていない。

## 移動対応表

全14ファイルを`git mv`で移動した。共有fixtureの統合と承認済み削除は次節。

| 移動前 | 移動後 |
|---|---|
| `backend/app/api/routes_t202.py` | `backend/app/api/common/route_errors.py` |
| `backend/app/api/dependencies_t202.py` | `backend/app/api/dependencies.py` |
| `backend/app/api/schemas_drafts.py` | `backend/app/api/common/schemas/drafts.py` |
| `backend/app/api/schemas_runs.py` | `backend/app/api/ui/schemas/agent_runs.py` |
| `backend/tests/t201/test_draft_inputs.py` | `backend/tests/unit/test_draft_inputs.py` |
| `backend/tests/t201/test_draft_service.py` | `backend/tests/unit/test_draft_service.py` |
| `backend/tests/t201/test_draft_validation.py` | `backend/tests/unit/test_draft_validation.py` |
| `backend/tests/t201/test_draft_repository.py` | `backend/tests/integration/test_draft_repository.py` |
| `backend/tests/t202/test_run_api.py` | `backend/tests/unit/test_run_api.py` |
| `backend/tests/t202/test_write_api.py` | `backend/tests/unit/test_draft_write_api.py` |
| `backend/tests/t202/test_runs.py` | `backend/tests/integration/test_runs.py` |
| `backend/tests/t202/test_review_fixes.py` | `backend/tests/integration/test_run_regressions.py` |
| `backend/tests/t202/test_integration.py` | `backend/tests/integration/test_agent_run_lifecycle.py` |
| `backend/scripts/check_t201_postgres.py` | `backend/scripts/check_scan_index.py` |

`backend/app/api/common/schemas/__init__.py`はパッケージ用の空ファイルとして追加。依存元のAPI・app/main.py・評価スクリプト・テストのimportとmonkeypatch対象文字列を追従した。API名・ルート・DTOのフィールド・例外の判定処理は変更していない。

### テストの分類とfixtureの統合

- **unit**：入力型、検証関数、RepositoryをモックするDraftService、ServiceをモックするRun/Write API。
- **integration**：SQLiteで実SQLを実行するDraftRepository、RunRepository/RunService、API→実サービス→DBとジョブの結合、DBを使う回帰検査。既存の混在モジュールは実DB利用を基準にファイルごとintegrationへ置き、テスト関数の分割・assert変更は行わない。
- `tests/t201/conftest.py`のSQLite型コンパイラ・AsyncTestSession・sessionと、`tests/t202/conftest.py`のTestConnection・connectionメソッド・seededを、既存`tests/integration/conftest.py`へ統合した。SQLiteのFK/部分索引/transaction・投入データを維持した。
- session/seededの利用先はいずれもintegrationであり、unitとの共有fixtureを新設する必要はなかった。PostgreSQLの既存db_session/clientは変更しない。ルートの`tests/conftest.py`も変更していない。
- `sys.modules`へ偽のdatabase/configを入れる分岐、conftest.pyの動的import、sys.pathへの挿入を除去。通常収集では元からルートの実設定・Baseを使用しており、同じBaseを通常importする。旧conftest 2ファイルを削除し、`--confcutdir`前提を残さない。
- テスト同士の補助関数参照は`tests.unit.*` / `tests.integration.*`の明示importへ置換した。関数内容は維持。

### 参照と承認済み削除

- Makefile：`check-run-step-index`と`agent-eval-lint`を`check_scan_index.py`へ、`agent-test`を移動後の`integration/test_run_regressions.py`へ追従。
- `tests/unit/test_live_index_check_configuration.py`のスクリプトパスも追従。
- 既存`check_g2_mutations_isolated.py`は旧テストパスを参照していたため、移動後のRepository/Validationテストへ追従し`--confcutdir`を除去。関数の変異内容・対象テスト名は維持し、標準fixtureを使う旨をコメントへ記載した。この補助スクリプト自体の変異試験は今回再実行していない。
- タスクHで承認された`frontend/orval.t202.config.ts`・`frontend/tsconfig.t202.json`・`backend/scripts/export_openapi_isolated.py`を`git rm`で削除。正規orval/tsconfig/OpenAPI exporterを使用する。
- Alembicの適用済みリビジョンとID、既存`check_t202_postgres.py`など今回列挙されていないファイル名は変更しない。過去のhandoffに書かれた旧パスも履歴として保全する。

## 保護検査と振る舞い不変の証拠

| 指示・検査 | 対応と結果 |
|---|---|
| test_single_source_of_truth.py | app配下をrglobするため、新common/schemas・dependenciesも自動で対象になる。assertの変更なし、全体ゲートでPASS |
| test_api_path_separation.py | `app.main.app`の実routesを検査するため配置に依存しない。assertの変更なし、全体ゲートでPASS |
| test_regression_gate.py | Makefileのcheck-beを実行し、索引検査失敗時にpytestへ進まないことを検証。チェック対象のMakefile名・ターゲット名は維持。assertの変更なし、PASS |
| テスト内容 | 移動前の全test_*.pyを保存して比較。import/パス置換を正規化したASTに差分0。全assert **611か所のAST差分0** |
| 件数 | 移動前BE404 / FE78 → 移動後BE404 / FE78。テスト追加・削除なし |
| API契約 | 移動前後の正規OpenAPI JSONを構造比較して一致。生成物を手編集せず、通常orvalで再生成 |
| 配置参照 | app/tests/scripts/Makefile/正規FE設定に、旧APIモジュール・旧テストディレクトリ・旧索引スクリプト・削除した設定/exporter・confcutdirの参照0 |
| 保全 | memory、全適用済みrevision、frontend/src（生成物・翻訳を含む）の開始時ハッシュ一致を確認。memory・CODEX-INSTRUCTIONS.mdに元からある他セッションの差分は保全し、編集・復元・ステージングしていない |

純粋な移動のため、REDを作る新規テストや人工変異は追加していない。移動前後の同じ全体ゲートとAST/契約の一致を証拠とする。Makefileのgateを迂回する実行はしていない。

## 実行結果

全ログ：[移動前](test-results/layout-before-regression-2026-09-12.log) / [移動後](test-results/layout-after-regression-2026-09-12.log)。接続URIが出た場合だけ伏せる処理を通して保存した。

```text
$ DEBUG=false CI=true make check  # 移動前
131 files left unchanged
404 passed, 124 warnings in 18.71s
Test Suites: 11 passed, 11 total
Tests:       78 passed, 78 total
Time:        3.357 s
✅ check: all green
exit 0

$ DEBUG=false CI=true make check  # 移動後
130 files left unchanged
404 passed, 124 warnings in 18.85s
Test Suites: 11 passed, 11 total
Tests:       78 passed, 78 total
Time:        3.311 s
✅ check: all green
exit 0
```

両実行とも開発/テストDBの`alembic upgrade head`と走査索引検査がPASS。追加migrationはなく、適用済みrevisionを編集していない。通常のテストDB初期化はゲートに従って実行される。FEの既存orval.t202設定警告は対象ファイル削除により解消した。外部モデル送信・エージェント評価・FE機能変更はない。

## gitの移動検出

[git status / rename出力](test-results/layout-renames-2026-09-12.log)に実出力を保存。`git status --short`は14ファイルをRまたはRMとして表示し、`git diff HEAD --summary -M`も14件のrename（94〜100%）を検出した。

`git mv`による移動はindexに入り、その後のimport追従は作業ツリーにある。全差分の確認には`git diff HEAD --find-renames`を使う。無関係な既存差分はステージしていない。commit/pushなし。

## 提出状態

**再レビュー依頼。希望Status: C-1 REVIEWING。** §0bの常駐ループに従い、§7見出しの`2026-09-12 20:45`が変わるまで作業ツリーを変更せず待機する。T-204・G3以降を推測して着手しない。memory更新とDONE判定はClaude担当。
