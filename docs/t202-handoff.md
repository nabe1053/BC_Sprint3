# T-202 引き継ぎ（2026-09-12）

## 更新：全体回帰の明示承認後（2026-09-12）

ユーザーの保留解除後、T-203接続を含む最終コードで全体ゲートを実行。BE392件PASS、ミニ評価13ケースPASS。フルゲートはG1の型検査8エラーとJest失敗で不合格。詳細とログは `docs/t203-handoff.md` 最新節に記録した。下記の「最終差分の全体回帰未実施」は本結果で更新する。T-202の独立した修正、memory編集は行っていない。

## 最新: RV-015対応・再レビュー依頼（VS Code引継ぎ後）

**希望Status: REVIEWING（コード修正済み・再レビュー待ち、P1-1はユーザー指示で保留）。DONEではない。** 以下の旧「独立レビュー済み」「62件」の報告は追加レビュー前の履歴。今回の独立レビューは未実施であり、実装者の検証をその代用にしない。Claudeメインセッションへ再レビューを依頼する。memoryは編集せず、転記を同セッションへ依頼する。

### レビュー対応とRED / GREEN

主な再現テストは`backend/tests/t202/test_review_fixes.py`へ追加。

| 指摘 | 変更ファイル・対応 | 再現と実結果 |
|---|---|---|
| P1-1 migration未適用による全体回帰44 ERROR | 最新ユーザー指示が優先。全体回帰・DB適用・通常設定読込・別テストDB初期化を実施しない | **保留**。レビュー記載の44 ERRORは今回再実行した値ではない |
| P1-2 停止閾値・モデル重複 | `agent/definition.py:default_run_limits`だけで既定値を組み立て、`domain/run_types.py`は必須値のみのDTOに変更。`api/dependencies_t202.py`で注入。`services/run_service.py`からモデルを`repositories/run_repository.py:reserve`の必須引数へ渡す | `test_definition_defaults_reach_reserved_run`: definitionの値を変更して実予約へ反映されることを確認、RED → GREEN |
| P2-1 GETの書込・ロック・JSONL全書換 | `run_service.py:progress`の期限回収、`run_repository.py:progress`のexportを除去。回収は再実行要求・プロセス起動、exportは開始・終了・明示再出力・起動時に行う | `test_progress_never_writes_locks_or_exports`: commit/回収/非SELECT/FOR UPDATEを拒否し、trace非呼出しを確認、RED → GREEN |
| P2-2 実行中runがディスク障害で終端 | `_export_or_fail(starting=False)`ではrunningを維持しtrace_write_failed/job_trace_failureだけを保存。worker投入前の開始トレース障害は従来どおりfailed。成功終端時の障害もfailed、既存の停止理由は保全 | `test_running_trace_failure_does_not_terminate_worker`: RED → GREEN。既存の終端・再試行・旧トレース保持テストもPASS |
| P2-3 HTTPエラー表重複 | `domain/errors.py`へDomainError基底を移し、`services/exceptions.py`は同型を再公開。`domain/draft_errors.py`を継承へ変更。`api/routes_t202.py`は共通`api/errors.py:domain_error_handler`へ委譲し独自STATUS表を除去 | `test_draft_error_uses_shared_domain_hierarchy`: RED → GREEN。APIの既存400/404/409/413/503契約もPASS |
| P2-4 メッセージ・フィールド名からコード推測 | `domain/draft_types.py`がPydanticCustomErrorを送出。必須・型違反もスキーマ内の明示マッピングで型へ変換し、HTTP側はerror.typeだけを使用。ネストした両端のコードも保全 | `test_validation_code_comes_from_type_not_message_or_field` / `test_schema_errors_carry_business_codes`: 2件RED → GREEN。追加した`test_nested_end_business_error_keeps_typed_code`でKeyErrorを検出し、RED → GREEN |
| P2-5 保管パス検証重複 | `repositories/run_input_files.py`がDocumentStorageGateway.resolve_readable_pathを再利用。共通root検証に加え、run側は当該案件内だけという条件を適用 | `test_input_size_uses_shared_storage_validation`: RED → GREEN。通常/相対/別案件/symlink逸脱/欠損の5ケースもPASS |
| P2-6 原本欠損の契約外404 | `run_service.py`で原本が読めない場合は容量の再確認だけ省略。抽出済み本文を再利用する。件数・ページ数・読取可能性の検査は維持 | `test_missing_original_allows_previously_extracted_content`: RED → GREEN。05-api-ipoへ判断を明記 |
| P2-7 SSOT未登録 | `docs/requirements/05-api-ipo.md`第6章の表にE_REQUEST_INVALID/E_JOB_START_FAILED/E_RUN_NOT_ACTIVEを追記。job_trace_failureはツール追加ではない管理イベントとして補足 | 文書修正。コードは従来末尾の補足にあったが、第6章には無かったことを確認 |
| P2-8 例外診断欠落・即時再試行 | `agent/jobs.py`はworkerと保存失敗の例外型名のみをログへ出し、保存再試行に0.1/0.2秒のバックオフ | `test_worker_diagnostics_are_safe_and_persistence_retries_back_off`: RED → GREEN。本文文字列をログへ出さないことも検証 |
| P2-9 cancel待機 | workerの後始末に20msの猶予。asyncio.waitを使用し非協調cancelでも上限を維持。完了保存もwait_forの無期限cancel待ちを避け、1回5秒×3回＋バックオフを16秒以内に収める | `test_cancel_cleanup_gets_bounded_grace_before_terminal_callback`: RED → GREEN。既存非協調workerテストと追加の非協調完了callbackテストもPASS |

最初の再現群は7 failed、その修正後69 passed。次のコード型/共通storage/current別名の再現群は4 failed / 7 passed、その修正後73 passed。ネストした両端の再現は1 failed / 73 passed、修正後74 passed。追加のパス5ケース・保存上限・実ルーター分離を含め、最終81 passed。

### P3の対応と残件

- P3-1/3/4: T-203には未着手。RunTraceStoreを新ジョブのJSONL経路とする現状を明記し、旧runner/hooks/TraceRecorderの統合・ガードレール差込口・runロック内のツールstep採番・decision/observation拡張はT-203開始前の残件としてagent-planへ記録。今回、その実装は追加しない。
- P3-2: 04-dbへstage_detailの固定診断コードと表示時の対応づけを追記。原文・例外内容を入れない。
- P3-5: downgradeのRuntimeErrorを維持。データを消す後退migrationは自動提供しない方針を記録し、memoryへの転記をClaudeへ依頼する。
- P3-6/8: PostgreSQL用スクリプトは合成スキーマ検証であり、実スキーマ適用・2セッション直列化の保証ではない。今回はDBスクリプトも再実行しない。
- P3-7: `tests/t202/test_run_api.py`は実agentルーターもmount。`tests/unit/test_api_path_separation.py`のUI_ONLY_SEGMENTSにagent-runsを追加し、T-202隔離ハーネスから既存3チェックを実appに対して実行。root conftestは読み込まない。
- P3-9: ruleVersion=currentを現行規則へ解決（RED → GREEN）。`api/schemas_drafts.py`のcountsをitems/questions/inventoryの具象モデルに変更。rejectedは空tuple契約（JSONは空配列、OpenAPIはmaxItems:0）。Orvalの生成TSではunknown[]となる点は残るが、APIが非空を返すことは許容しない。draft_repositoryをformat。orval.t202.config.tsはG1保全・無断削除禁止のため保持する。

### 最終検証（実行済み）

backend:

```sh
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t202 tests/t202 -q --tb=short --disable-warnings
# 81 passed, 105 warnings in 2.44s
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t201 tests/t201 -q --tb=short --disable-warnings
# 104 passed in 0.71s
.venv/bin/python -B scripts/export_openapi_isolated.py
# Exported 24 route paths to backend/openapi.json
```

frontend:

```sh
npm run orval -- --config orval.t202.config.ts
# success / clean:false、生成ファイルの手編集なし
./node_modules/.bin/tsc --noEmit --project tsconfig.t202.json
# exit 0
```

生成クライアントがcustomInstanceを使用することを確認。全体FE型検査は今回実行せず、G1の編集中ファイルを編集していない。警告は既存FastAPI/Pydantic組合せのalias属性警告。依存更新はしていない。

Pythonのlint/format対象25ファイル（backend相対）:

```text
app/agent/definition.py app/agent/jobs.py
app/api/dependencies_t202.py app/api/errors.py app/api/routes_t202.py app/api/schemas_drafts.py
app/domain/errors.py app/domain/draft_errors.py app/domain/draft_types.py app/domain/run_types.py
app/models/agent_runs.py
app/repositories/draft_repository.py app/repositories/run_input_files.py app/repositories/run_repository.py
app/services/exceptions.py app/services/draft_validation.py app/services/run_service.py
alembic/versions/t201_artifacts.py
tests/t201/test_draft_repository.py tests/t201/test_draft_validation.py
tests/t202/test_review_fixes.py tests/t202/test_run_api.py tests/t202/test_runs.py
tests/unit/test_api_path_separation.py scripts/check_g2_mutations_isolated.py
```

上の明示パス群を引数として`.venv/bin/ruff format`（13 files reformatted, 12 files left unchanged）、`.venv/bin/ruff check --no-cache`（exit 0）を実行。`git diff --check`もexit 0。

### 未実施と動作上の限界

- 全体回帰・実DBへのmigration適用・通常設定読込・別DB初期化・実案件/外部LLM実行・独立レビューは未実施。コミット/プッシュ/削除も行っていない。
- 進捗GETは最後に保存された状態を返す。保存が全再試行で失敗すると、次の実行開始要求またはプロセス起動による回収までrunningが残り得る。GET自体では回収しない仕様へ変更した。
- PostgreSQLの版行/run行ロック待機・実スキーマ上のmigration連鎖は未検証。T-201索引追加もコードだけで、DBには適用していない。
- memoryとG1の既存変更・未追跡成果物を保全した。T-203/T-204へは進まず、**再レビュー依頼**で止める。

T-202 の API と実行管理を実装。独立レビュー済み（最終指摘なし）。全体回帰はユーザーの指示で保留し、DONE にはしていない。T-203 は未着手。

## 実装範囲

- #15〜19: 案件情報・明細・根拠・確認事項・インベントリの保存。AGENT 名前空間のみ。
- #20: 同じ読取専用検証ハンドラを UI / AGENT に公開。7種類の違反を camelCase で返す。
- #21: 完了条件を再検査して確定。確定済み版・終了済み実行への遅延書込を拒否。
- #12: UI から実行開始。案件ロック内で入力上限・読取可能資料・現行規則・引継ぎ確認を検査し、run/version を同時予約して202を返す。版間で人の記録や成果物をコピーしない。
- #13/#14: DB に保存した実行状態と順序付きトレースを取得。成功し確定した版だけ versionId を公開する。
- jobs 経由でバックグラウンド実行。バックグラウンド保存にはリクエストと別のセッションを使う。外側タイムアウト・キャンセル・例外を終端結果へ変換し、一時的な完了保存失敗は3回まで再試行する。
- 単一サーバープロセスの起動時に残存 running を failed に回収する。ポーリング/再実行時にも保存済み外側期限+16秒を超えた実行を回収する。
- JSONL は資料本文・例外の内容を記録しない。入力資料のID/ハッシュ・規則ID・実装版・モデル・停止閾値・結果を記録する。ディスク書込失敗時もDBの失敗記録を残す。
- 規則の is_current、実行の impl_version/limits、単一現行規則・案件ごとの単一running・stop_reason 制約を追加する migration を用意。
- agent_run_steps.trace_event に出力イベントを同時保存し、DB commit 後にJSONLをseq順で原子的に再構築する。保存再試行で同じseqを重複しない。プロセス中断後は起動時・ポーリング時に再構築する。開始イベントのない旧実行では再構築せず、既存JSONLを保持する。

## T-203 への接続点

現行の `local_worker_unavailable(context)` は `failed / agent_implementation_pending` で終端する。生成処理のない状態を成功と見せないための境界であり、今回、資料の抽出・判断処理は追加していない。

T-203 はローカル worker を `RunDispatcher` に注入する。受け取る `RunContext` は run_id/case_id/version_id/rule_set_id/limits。完了時に `RunResult` を返す。ツール経由で検証・確定を通した版だけが completed として受理される。内側/無応答制限・最大ターン・反復検知・ガードレール・段階進捗更新・ツール呼出しのDB/JSONL記録は T-203 で接続する。

SDK runner をこの境界から直接呼ばない。外部送信未承認（D05）を維持する。旧SDK向け TraceRecorder には本文を記録する経路があるため、今回の安全なジョブトレースとは別に扱う。資料内の指示や本文を新しいジョブトレースへ流さない。

## 検証

独立レビューの指摘3件は再現テストで修正し、最終レビューは指摘なし。レビュアーも62件を独立再実行してPASS。

バックエンド作業ディレクトリで、機密設定や root conftest を読み込まない以下の確認を実施。

```sh
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t202 tests/t202 -q --tb=short --disable-warnings
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t201 tests/t201 -q --tb=short --disable-warnings
.venv/bin/python -B scripts/check_t202_postgres.py
.venv/bin/python -B scripts/export_openapi_isolated.py
```

- T-202: 62件 PASS。実API→保存→検証→確定→ジョブ完了の統合確認、引継ぎ確認、タイムアウト、非協調キャンセル、一時保存障害、再起動回収、保存後の遅延書込を含む。
- T-201: 77件 PASS。旧テストの同一案件2runningは新制約と矛盾するため、比較対象の旧runをfailedに修正。
- PostgreSQL: 新規の一意な検証スキーマ内で migration と4件の拒否制約・旧レコード補足・終了後再実行を確認し、全て ROLLBACK。既存テーブル・資料・設定は読まない。
- 変更Pythonファイルの Ruff と `git diff --check` PASS。
- OpenAPI 24パスを実際のルーターから出力し、`npm run orval -- --config orval.t202.config.ts` でクライアント再生成。clean:false で既存ファイルを削除しない。customInstance の接続を確認。
- 生成クライアント＋mutator単独のTypeScript検査はPASS（frontendで `./node_modules/.bin/tsc --noEmit --project tsconfig.t202.json`）。
- フロントエンド全体の `npm run typecheck` は、並行作業中のG1に8件のエラー（未作成の画面モジュール、API戻り値の共用型、テスト型）を検出。G1のファイルには手を加えていない。
- FastAPI/Pydantic の既存バージョン組合せから alias 属性の警告が出る。実リクエストでcamelCaseのみを受理することはテストで確認済み。依存更新はしていない。

## 未実施・注意点

- ユーザー指定で全体回帰テストは保留。通常の設定読込、別テストDB初期化は行っていない。
- migration の実DBへの適用、現行規則の設定、実案件でのジョブ起動は未実施。既存規則から現行版を勝手に選ばず、移行後も is_current はfalseのまま。実際に使う現行規則は別途設定が必要。
- migration は既存の重複runningや不正stop_reasonを削除・補正しない。そのような行があれば制約追加は失敗するので、確認の上で処置する。
- DBとファイルを跨ぐ単一トランザクションはない。DBに確定したtrace_eventが正。JSONL出力失敗はDBにtrace_write_failedを残し、既存の失敗/停止理由は保全する。未出力イベントはDBから冪等に再出力する。T-203のツール記録にもこの出力方式を使う。
- 複数サーバープロセスでの運用には対応していない。起動時回収は単一プロセスのローカルPoCを前提とする。
- コミット・プッシュ・資料/DBの削除・外部送信は行っていない。

## 運用指示（2026-09-12 研修者決定）

**memory.md は読むだけ・編集禁止。**修正結果・学び・Status 希望はこの handoff に書く。詳細と修正対象は `docs/reviews/CODEX-INSTRUCTIONS.md` と `docs/reviews/g2-review-2026-09-12.md`。

## T-203への接続実施（2026-09-12、ユーザー明示指示）

`dependencies_t202.py`でLocalAgentWorkerをRunDispatcherへ注入した。dispatcherには停止時の未走査範囲を保存するbefore_finishを追加し、run_serviceは実装識別子をdefinitionから取得する。既存のPOST 202・進捗GET・jobsの終了保存/再試行契約は維持する。DIモックは新しいキーワード引数を受理させたが、既存assertは変更していない。

検証と残件は `docs/t203-handoff.md` に集約。限定テスト68件、ジョブ/APIミニ評価13ケースPASS。保留に反した途中の全体回帰実行も同文書に明記し、最終差分の全体回帰は未実施。T-202のレビュー済みStatusをCodex側で更新せず、T-203として再レビュー依頼で停止する。
