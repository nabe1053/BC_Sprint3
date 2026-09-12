## RV-029 対応

タスクK-2を完了。`backend/tests/unit/test_regression_gate.py:28` の子make環境を `MAKEFLAGS=""` から **`MAKEFLAGS="-j8"`** に変更した。これにより外部環境に依存せず、`.NOTPARALLEL:` の削除を既存の回帰テストが検出する。

| 指摘 | 変更 | RED→GREEN・変異 |
|---|---|---|
| RV-029 P2-1 | `test_regression_gate.py:28` の1行。既存3assertとテスト数を保全 | リポジトリを変更しない隔離コピーで `.NOTPARALLEL:` を除去すると `PYTEST_MUST_NOT_RUN` のassertionで **1 FAIL（0.02s）**。宣言を戻すと **1 PASS（0.01s）** |

入口は `make -f Makefile -f /tmp/layout-gate-checks.mk gate-mutation`。DB・アプリを起動しない既存ゲート検査1本で変異を確認し、その後に通常の全体ゲートを実行した。前回の比較証跡のMAKEFLAGS空指定は履歴となり、この修正で置き換わる。

```text
$ DEBUG=false CI=true make check
404 passed, 124 warnings in 20.89s
✅ check-be: backend green
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        10.358 s
✅ check: all green
```

[変異結果](test-results/layout-gate-mutation-2026-09-12.log) / [RED](test-results/layout-gate-red-2026-09-12.log) / [GREEN](test-results/layout-gate-green-2026-09-12.log) / [全体ゲート](test-results/layout-gate-regression-2026-09-12.log)

Codexによるcommitなし。memory・CLAUDE.md・AGENTS.mdの編集、規約の複製や再生成なし。最新§7「2026-09-12 23:50」の明示指示に従い、この条件付きDONE対応の提出後は更新待ちを挟まずタスクL（T-205）へ進む。

再レビュー依頼

---

## C-2（タスク K）

**整理完了・再レビュー依頼。** §7「2026-09-12 23:10」で着手し、作業中の「23:30」更新でも最優先はC-2であることを確認した。最終 `DEBUG=false CI=true make check` は **BE404 / FE166（15スイート）PASS**。テストの追加・削除なし。Codexはcommitしていない。

### レビュー対応

| 指示 | 変更内容（ファイル:行） | 確認結果 |
|---|---|---|
| K-1 / TODO-010 | `Makefile:13` に `.NOTPARALLEL:`。`:77`〜`:80` のINDEX環境変数4個をtarget-specific exportへ移動し、TEST_DB定義後に配置。`backend/tests/unit/test_regression_gate.py:28` の子makeはMAKEFLAGSを空にする | 実レシピを置き換えたDB非接触プローブで旧Makefileは `-j8` の順序・環境変数の適用範囲がRED、変更後はGREEN。既存ゲート回帰テストの3assertを保全 |
| K-2 / TODO-010 | `backend/scripts/check_scan_index.py:23`。環境変数欠落を捕捉し、`SystemExit("make check-run-step-index から実行してください")` を出す | INDEX変数を1個ずつ欠落させた4ケースで、旧版はKeyError、変更後は指定案内。接続処理は実行していない。指定値を使う既存テストもPASS |
| K-3 / TODO-012① | `git mv` で `backend/scripts/check_t202_postgres.py`→`check_run_metadata.py`、`backend/tests/integration/test_api_path_separation_t102.py`→`test_api_path_separation_live.py` | スクリプトのAST・移動テスト本体は一致。実行コード側の参照を追従。設計書・過去ログは履歴として保持 |
| K-4 / TODO-012②③⑥ | `backend/tests/fixtures/sqlite_support.py:1`へSQLiteコンパイラと共有metadataのSQLite indexオプション処理を抽出。`integration/conftest.py:80`から呼ぶ。`:87`/`:95`のアダプタ名を変更、`:104`のcase_codeをSEED-CASEへ | 2コンパイラ関数のAST一致。metadataループも引数への置換以外は一致。プロセス全体へのSQLiteコンパイラ登録と共有metadata書換が従来どおりであることをコメントに明記。PostgreSQL向け処理を変えていない |
| K-5 / TODO-012④⑤ | 4つの指定ビルダと共有snapshotを `tests/fixtures/draft_data.py:5` 以降へ。共有repo/serviceを `run_support.py:8` 以降へ。経路語彙を `route_contract.py` へ。`integration/test_run_regressions.py:248`を `test_run_endpoints_are_in_ui_only_route_contract` に改名 | テストモジュール相互importは0。7ビルダのAST一致。汎用パス検査3本は通常収集で1回だけ実行し、runpyによる二重実行を除去。残した会員判定assertは共有定数への参照だけ変更 |
| K-6 / RV-028 P3-6 | `git mv` で `IntakeRecovery.test.tsx` をdocuments featureへ移動。IntakePageは `../IntakePage`、mockは同featureの `../../hooks` を参照 | テスト本体は完全一致。実HTTPの2ケースも最終ゲートでPASS |

CV-021の「テストモジュール同士をimportしない」を満たすため、指定4ビルダに依存するsnapshot・repo/serviceの既存共有も抽出した。新しい業務ロジックやテスト期待値は追加していない。

### 振る舞いを保全した3点の証跡

1. **importを除いた旧新diff**: [比較ファイル](test-results/layout-chore-without-imports-2026-09-12.diff)。ASTからimportを除去し、位置移動・指定変更を省略せず記録した。抽出した9関数（7ビルダ＋2コンパイラ）は旧新AST一致。SQLiteのforループはmetadata引数への置換だけ。純リネームのスクリプト、FEテストも本体一致。
2. **テスト関数名集合**: `test_*.py` 内の290件→290件。指定されたファイル移動と関数名1件の変更を対応付けると集合一致。無加工ではその関数名1件だけが変わる。conftestの旧 `test_connection` はpytest収集対象ではない補助関数なので、この集合には含めない。290件のうち288件はimportを除いた関数ASTも一致。残る2件は明示指示のMAKEFLAGS引数追加とrunpy二重実行の除去。
3. **assert総数**: Python ASTのAssertは **611→611**。全assert式も、`tests["UI_ONLY_SEGMENTS"]` を共有定数参照へ対応付ける1箇所を除き一致。assertの削除・弱体化なし。

[3点比較ログ](test-results/layout-chore-proof-2026-09-12.log) / [Makeと欠落環境変数の旧版RED→変更後GREEN](test-results/layout-chore-contracts-2026-09-12.log)

作業時入口は `make -f Makefile -f /tmp/layout-chore-checks.mk chore-proof chore-contracts`。旧版ソースは着手時に採取したもの。プローブは一時Makefileの合成レシピだけを動かし、DB・pytest・実ジョブを起動していない。再実行できない一時ドライバはリポジトリに採取せず、比較diffとログを保存した。

### 全体ゲート・保全

開始時刻: `2026-09-12T23:01:36+09:00`。pytestの同時実行がないことを確認してから、全体ゲートを1回実行した。BE失敗・再実行なし。

```text
$ DEBUG=false CI=true make check
404 passed, 124 warnings in 19.58s
✅ check-be: backend green
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.62 s, estimated 8 s
✅ check: all green
```

[全体ゲートログ](test-results/layout-chore-regression-2026-09-12.log) / [テスト・スクリプトの整形とlint](test-results/layout-chore-format-2026-09-12.log) / [appの読み取り専用lint確認](test-results/layout-chore-app-readonly-2026-09-12.log)

BEの124 warningsは既存のFastAPI/Pydantic非推奨警告。FE typecheck / eslintはエラー・警告なし。`backend/app/` とmigrationは着手時ハッシュ一致。SQLite補助処理の抽出はテスト側だけで行った。全体ゲートのapp formatterが変更を加えないことを、事前の読み取り専用lintと事後ハッシュでも確認した。

作業中、並行側のcommit `5e132f1` に、こちらで先に `git mv` した3ファイルの移動が含まれたことを確認した。移動を戻さず、その後の差分を保全している。**Codexによるcommitはなし。** 同commitで更新された `docs/requirements/02-requirement.md`・`agent-plan.md`・`.claude/memory.md` は並行側の変更として保全し、編集していない。

`backend/app/api/common/endpoints_reference.py:6` のdocstringには旧テスト名の参照が残る。`backend/app/`非接触という今回の指定に従い、ここは変更していない（実行時importではない）。次にappの整理を許可されたラウンドで追従できる。

希望Status: REVIEW。§7見出し「2026-09-12 23:30」の更新まで待機。T-205・実モデル接続は未着手。実モデル呼び出し・`.env`の読み取りなし。

再レビュー依頼
