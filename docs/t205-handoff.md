## L-7 対応（run 9）

2026-09-13。§7 **06:20版**で着手し、**07:05版のpytest可**を確認して全体ゲートを実行。**BE535件 / FE166件、除外なしでPASS**。希望 Status: REVIEWING。T-301のファイル/hunkは変更していない。SDKは完全モック、実モデル呼出し・commitなし。

### レビュー対応

| 指摘番号 | 変更内容（file:line） | REDテスト・実行コマンド・件数 |
|---|---|---|
| L-7 1 入口例外 | `backend/app/agent/tools.py:89`。begin_step・request callback・operationを含むinvoke全体を捕捉。DomainErrorは元の固定code、ValidationErrorは従来のE_REQUEST_INVALID＋loc/msg、予期しない例外はE_INTERNAL。step未取得時はfail_stepを呼ばない。失敗記録が例外を上げても元のツールエラー応答を返し、CancelledErrorは再送出 | `test_begin_step_failure_becomes_safe_tool_reply`（3件）、`test_unexpected_operation_failure_returns_internal_even_if_recording_fails`（2件）、`test_request_callback_failure_is_converted_and_cancel_is_preserved`。下記model-boundary-testの初回REDに含む |
| L-7 2 防御境界 | `agent/runner.py:178`。executor.callまたは方針の想定外例外をfailed/worker_failedへ変換し、カウント済みturnsを保持 | `test_cleanup_cancel_preserves_worker_result_and_turns`のtool_error/policy_errorがRED→GREEN |
| L-7 3 後始末 | `agent/runner.py:69,181,194`。outcomeで戻り値確定を記録、sys.exc_infoで進行中例外を判別。後始末キャンセルで例外・戻り値・既知期限を上書きしない。元から進行中の外側キャンセルは保持 | 同テスト3件（正常完了も含む）と、追加の`test_cleanup_cancel_cannot_replace_pending_base_exception` / `test_running_worker_still_propagates_external_cancellation`。新変異で結果/進行中例外の4件がFAIL |
| L-7 4 ジョブ分類 | `agent/jobs.py:71`。worker.resultのCancelledErrorだけをworker_failedへ写す。await wait自体の中断はprocess_interruptedのまま | `test_jobs_distinguish_worker_cancellation_from_job_interruption`（2件）。worker側キャンセルの旧分類でRED→GREEN、job側の既存分類も保持 |
| L-7 5 固定診断 | `agent/runner.py:22` / `agent/jobs.py:32`。DomainError.code、無ければ例外型名だけをログに含める。本文を出さない | `test_task_diagnostic_logs_only_fixed_code_or_type`（4件）。DomainErrorの2件がRED→GREEN、private-sourceのcanaryがログに無いことも検査 |
| L-7 7 変異 | `scripts/check_agent_mutations.py:20,132`。begin_stepをtry外へ戻す変異、後始末CancelledError再送出へ戻す変異を追加 | `make agent-mutations`で新規2/2検出（6 FAIL / 4 FAIL）。既存6変異も期待どおり検出、全baselineはPASS |
| L-7 設計・既存追従 | agent-plan末尾へL-7契約、04-db:941へworker_failed/process_interruptedの分類を明記。`tests/integration/test_agent_tool_repository.py::test_terminated_run_rejects_new_tool`は例外期待から同codeのis_error応答へ変更 | 旧入口が例外を漏らす前提のテストだったため、指定契約に追従。関数名とassert1件は保持。全体ゲートで実DB経路もPASS |

### RED・限定GREEN・変異

```sh
cp docs/test-results/model-boundary-checks-2026-09-13.mk /tmp/model-boundary-checks.mk
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-boundary-checks.mk model-boundary-test
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-mutations
```

- [初回RED](test-results/model-boundary-red-2026-09-13.log): **12 failed / 90 passed**。
- [初期GREEN](test-results/model-boundary-green-2026-09-13.log): **102 passed**。
- [追加境界を含む限定GREEN・変異](test-results/model-boundary-verification-2026-09-13.log): **104 passed**。新規ファイルの17ケースを含む。DB fixtureを使わない限定テストのみを、T-301 reviewer稼働中に実行した。
- `boundary_begin_outside_try`: **6 failed / 11 passed**。`boundary_cleanup_reraise`: **4 failed / 13 passed**。変異は子プロセス内のみ、共有ソースを変更しない。

### 全体ゲート

07:05版でpytest/全体ゲートが許可された後に実行した。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

[実出力](test-results/model-boundary-regression-2026-09-13.log):

```text
535 passed, 124 warnings in 33.00s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.573 s
✅ check: all green
```

除外なし。両DB migration・実索引確認・ruff・OpenAPI/orval・型検査・lintもPASS。実AE03の再実行run 10はClaude担当。Codexは§7 07:05版の明示指示に従い、提出後にT-302へ進む。

`.claude/memory.md`は未編集、`.env`は閲覧・表示・編集せず、commitしていない。T-301レビュー対象を保全した。

再レビュー依頼

---

## L-6 対応（run 7）

2026-09-13。§7 **03:50版**・AD-021 / TODO-021に対応。**除外なしの全体ゲート BE518件 / FE166件、local_dummy評価14/14件がPASS**。希望 Status: REVIEWING。T-301は中断継続。実モデルを呼ばずSDKは完全モック。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| L-6 1 配列契約 | `backend/app/domain/agent_types.py:64,70` / `services/agent_tool_service.py:43`。evidences/questionsは1件以上の配列のみ。単数キー・空配列・単複併記を拒否。MCP schemaとdescriptionに反映。戻り値も全件のID配列 | `test_batch_sdk_reply_contains_every_saved_id`（4件）、`test_batch_arguments_reject_empty_and_legacy_keys`（6件）。既存4ケースも配列へ置換。下記model-batch-unitで初回14 failed / 47 passed → 61 passed |
| L-6 1 保存・count | `repositories/agent_tool_repository.py:279`。既存DraftService/Repositoryで同一トランザクションに全件を保存し、observation.countに配列件数を記録 | `test_batch_tool_persists_all_rows_and_exact_observation_count`（1件/3件×2ツール）、`test_invalid_later_batch_row_rolls_back_every_row`（2件）。後続要素の対象不正で全件未保存。model-batch-dbの初回REDに含む |
| L-6 1 ダミー追従 | `agent/local_policy.py:104,165,222`。根拠・確認事項を集め一括呼出し。unsupportedもquestions配列に変更。`scripts/evaluate_local_agent.py:209`は直接の旧単数呼出しを持たずlocal_dummy_policyを使用するため、呼出し回数・countの検査を追加 | make agent-evalの既存14ケースを全件PASS。正常系はrecord_evidence 1回・count=2。TBA/URL注記の確認事項も各1回。シナリオの削除・期待停止理由の変更なし |
| L-6 2 閾値SSOT | `agent/definition.py:36`。MAX_TURNS=80。他の期限は不変。`test_single_source_of_truth.py:81`でagent-planの承認値との一致・注入を追加検査 | `test_stop_thresholds_are_only_defined_in_definition` が40対80でRED → GREEN。既存の重複検出を残し、40へ戻す変異も検出 |
| L-6 3 プロンプト | `agent/definition.py:14` / `docs/requirements/agent-plan.md:47,103,104,217`。代替提案は対象行つき確認事項へ、根拠・確認事項の一括、違反の一括修正、propose_items全行1回を反映。資料が明示する択一・分割はR06/R07として区別 | 決定的な契約検査と14ケース評価がPASS。実モデルの行数・判断品質はClaudeのrun 8で確認する |
| L-6 4 無応答診断 | `domain/run_types.py:53` / `agent/runner.py:49,55,94,150`。受信済みPolicyHeartbeatの最後の時刻と実行全体の件数を保持し、停止判定時にRunResultへ固定。`repositories/agent_tool_repository.py:158`はjob_interruptedの既存observationへ数値2キーのみ追加 | `test_timeout_diagnostics_capture_last_heartbeat_and_run_total`（未受信 / ツールをまたぐ受信 / 内側期限の3件）と `test_interruption_diagnostics_reach_trace_and_http_stop_reason_once`（2件）がRED → GREEN。DBとJSONLの一致、再試行でも1イベント、既存HTTPの停止理由、本文非混入を検査 |
| L-6 4 設計 | `docs/requirements/04-db.md:942`。sinceLastHeartbeatS / heartbeatsを記載。未受信なら開始からの秒数。agent-planのL-6補足も内側期限を明記 | スキーマは既存JSONBの数値キー追加。新規migration/APIは不要 |

### 入出力の変更

```text
record_evidence({evidences: [EvidenceInput, ...]})
  → {evidences: [{evidence_id: n}, ...]}
record_question({questions: [QuestionInput, ...]})
  → {questions: [{question_id: n}, ...]}
```

1件も配列で渡す。旧evidence/questionキーはE_REQUEST_INVALID。ツール名・13本・各要素の検証規則・保存単位は従来のまま。入力値をtraceへ出さず、成功件数だけを記録する。

### RED → GREEN・既存テストの保全

```sh
cp docs/test-results/model-batch-checks-2026-09-13.mk /tmp/model-batch-checks.mk
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-batch-checks.mk model-batch-unit
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-batch-checks.mk model-batch-db
```

Makefileの追加ターゲットは単体3ファイル、DB統合1ファイルを実行する作業中の入口。再レビューの根拠は下記の除外なし全体ゲート。

- [単体RED](test-results/model-batch-red-2026-09-13.log): **14 failed / 47 passed**。
- [DB統合RED](test-results/model-batch-db-red-2026-09-13.log): **8 failed / 13 passed**。
- [GREEN](test-results/model-batch-green-2026-09-13.log): **単体61 passed / DB統合21 passed**。
- `test_agent_execution_tools.py`の既存入力4箇所を単数→配列に置換。AD-021で旧キーを受けないため必要な期待更新。既存テスト13関数は全件保持し、既存関数内のassertは**24→24**。新規2関数（10ケース）を追加。
- `test_runs.py`は承認済み閾値変更に追従し、起動時保存値の期待を40直書きから`default_run_limits().max_turns`へ変更。既存22関数・assert **42→42**、T-301/L-4の変更も保全。
- SSOT検査は設計値照合を追加。既存検査とAPIパス分離の検査を削除・弱体化していない。

### 変異検証

```sh
cp docs/test-results/model-batch-mutation-2026-09-13.txt /tmp/model-batch-mutation.py
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-batch-checks.mk model-batch-mutations
```

[6/6検出](test-results/model-batch-mutations-2026-09-13.log)。子プロセス内のモジュールだけを変異し、共有ソースは変更しない。

| 変異 | 検出 |
|---|---|
| 配列を先頭1件に切る | 2 FAIL |
| evidence/questionのcountを既定1へ戻す | 2 FAIL |
| 診断値をjob_interruptedへ渡さない | 2 FAIL |
| 各bounded呼出しで受信件数をリセット | 2 FAIL |
| 直近生存信号からの秒数を0に固定 | 3 FAIL |
| MAX_TURNSを40へ戻す | 1 FAIL |

### 全体ゲート・ミニ評価

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-eval
```

[全体ゲート](test-results/model-batch-regression-2026-09-13.log):

```text
518 passed, 124 warnings in 32.72s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.777 s
✅ check: all green
```

除外・deselectなし。make checkの両DB migration/実索引確認、ruff、OpenAPI/orval、型検査、lintもPASS。

[ミニ評価14/14 PASS](test-results/model-batch-evaluation-2026-09-13.log): normal / ae06_url_in_source / tba / not_applicable / email / unsupported / max_turns / repeated_call / validation_loop / inactivity / inner_timeout / outer_timeout / no_readable / guardrail。traceルートは `backend/traces/evaluations/4b3f08c970f8417393a0cbe2238fa35f/`（git管理外）。

停止診断の実トレース例（評価用の短い期限。既定期限は変更していない）:

```json
{"code":"inactivity_timeout","count":1,"status":"error","heartbeats":0,"sinceLastHeartbeatS":1.0002567380142864}
{"code":"inner_timeout","count":1,"status":"error","heartbeats":0,"sinceLastHeartbeatS":2.000349415000528}
```

L-4/L-5の実モデル確認と同様、run 4/6のprocess_interrupted化の原因は未確定。今回の診断は次回発火時の切り分け材料であり、未再現の原因を解消したとは主張しない。Claudeが提出後にrun 8を行う。

`.claude/memory.md`は未編集、`.env`は閲覧・表示・編集せず、実モデル呼出し・commitはしていない。§7の指示どおりT-301は中断継続。L-3〜L-5とT-301を同一コミット単位とする指示は確認済みで、T-301再開時に同handoff冒頭へ記録する。

再レビュー依頼

---

## L-5 対応（run 5）

2026-09-13。§7 **02:50版**・AD-020に対応。**除外なしの全体ゲート BE497件 / FE166件、local_dummyの既存ミニ評価14/14件がPASS**。希望 Status: REVIEWING。実モデルは呼んでいない。T-301は中断を継続。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| L-5 1 エラー継続 | `app/agent/runner.py:105`。同一ツール名×同一codeの連続回数を専用カウンタへ分離し、REPEATED_CALL_LIMIT到達でtool_rejected。それまではis_errorのToolReplyを方針へ返す。成功でリセット | `test_only_consecutive_same_tool_error_codes_stop_the_worker`（5ケース） / `test_different_tool_names_do_not_share_the_error_counter`。2回継続・3回停止、別コード・別ツールの区別、成功リセットを確認。初回REDに含む |
| L-5 1 完了・検証 | `runner.py:115,120`。エラーになったfinalizeを成功とせず、失敗したvalidateの応答にviolationsがあると仮定しない | 上記finalize/validateケースがRED → GREEN。既存のrepeated_call・validation_loop・期限カウンタは維持 |
| L-5 2 検証情報 | `app/agent/tools.py:147`。PydanticのE_REQUEST_INVALIDはSDK応答へ `errors=[{loc,msg}]` を追加。input・ctx・urlを除外。gatewayへは従来どおり固定codeだけを渡す | `test_invalid_inventory_reply_has_field_messages_but_never_input_values`（status不正 / excludedのbasis欠落）と `test_scope_failure_returns_only_fixed_code`。項目情報を返し、引数値のcanaryは含まれず、scope失敗はcodeだけ。初回REDに含む |
| L-5 3 inventory説明 | `app/domain/agent_types.py:72` / `tools.py:184`。InventoryArgumentsの説明をMCPのschema/descriptionへ反映。status4語彙・itemIds件数条件・excluded時のbasis・excerptの原文抜粋を明示 | `test_inventory_mcp_description_explains_status_basis_and_excerpt`。説明不足の旧実装でRED → GREEN。業務ツール13本・入力フィールド・バリデーション規則は変更なし |
| L-5 5 設計 | `docs/requirements/04-db.md:941` のtool_rejected説明を連続3回へ更新 | agent-plan:235はorchestratorのAD-020改定を参照し、重ねて変更していない |

### run 5の引数について

実引数はトレースに保存していないため、**正確な入力の復元はできない**。スキーマ照合により、`status` の語彙違い、`excluded` なのに `basis` が無い等を仮説として再現した。いずれも登録前にE_REQUEST_INVALIDとなり、修正箇所のloc/msgがモデルへ返る。トレースは入力値を含めない方針を維持した。

既存schemaにはstatusのenumがあったが、MCP descriptionはツール名だけだった。現在は `entries`、`documentId`、`position`、正整数`seq`、原項番`sourceNo`、`excerpt`の意味と、mapped=1行 / split=2行以上 / excluded・unmapped=対応行なしを説明する。説明文はInventoryArgumentsの1箇所からschemaとSDK descriptionに使用する。

### RED・変異・全体ゲート

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-tool-retry-checks.mk model-tool-retry-test
# recipe: cd $(BACKEND) && uv run pytest tests/unit/test_policy_tool_errors.py tests/unit/test_agent_execution_tools.py -q
```

[初回RED](test-results/model-tool-retry-red-2026-09-13.log): **8 failed / 34 passed** → [最終GREEN](test-results/model-tool-retry-green-2026-09-13.log): **44 passed**（basis欠落・scope固定コードを追加）。既存test_agent_execution_toolsの期待は削除せず、新規テストを追加した。検証対象は決定的な失敗応答とカウンタであり、LLMの判断品質ではない。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-tool-retry-checks.mk model-tool-retry-mutations
```

[変異4/4検出](test-results/model-tool-retry-mutations-2026-09-13.log): 1回目で停止へ戻す（6 FAIL）、成功時リセットを除去（1 FAIL）、項目別情報を除去（2 FAIL）、input値を応答へ混入（2 FAIL）。対象モジュールを子プロセス内だけで変異し、共有ソースは変更していない。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-eval
```

[全体ゲート](test-results/model-tool-retry-regression-2026-09-13.log):

```text
497 passed, 124 warnings in 30.12s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.554 s
✅ check: all green
```

[ミニ評価14/14 PASS](test-results/model-tool-retry-evaluation-2026-09-13.log): normal / ae06_url_in_source / tba / not_applicable / email / unsupported / max_turns / repeated_call / validation_loop / inactivity / inner_timeout / outer_timeout / no_readable / guardrail。`unsupported`も既存経路のままPASS。評価traceルートは `backend/traces/evaluations/5e419060bb8d4363af36fd977b0313f5/`（git管理外）。評価スクリプト・既定方針は変更していない。

`.claude/memory.md`・`.env`は編集せず、`.env`の閲覧/表示・実モデル呼出し・commitはしていない。中断中T-301とL-3/L-4の未コミット変更は保全した。§7更新まで待機する。

再レビュー依頼

---

## L-4 対応（run 4）

2026-09-13。§7 **02:20版**の最優先指示に対応。T-301を中断したままL-4を実施し、**除外なしの全体ゲート BE487件 / FE166件がPASS**。希望 Status: REVIEWING。実モデルは呼ばず、SDKは完全モック。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| L-4 A 部分出力 | `app/agent/claude_policy.py:94`。`include_partial_messages=True`。既存の全メッセージ共通経路がStreamEventも受信時刻つきPolicyHeartbeatとして送る | `test_sdk_message_activity_controls_only_inactivity_clock[4-False-True]`、既存SDK optionsテスト2件。20秒間隔のStreamEventが80秒続いても停止せず、ツール1回を実行。初回REDに含む |
| L-4 B キャンセル分類 | `app/agent/claude_policy.py:145`。SDK後始末を別タスクに置きshieldし、参照を完了まで保持。`app/agent/runner.py:125,142`。内側/無応答期限が確定した場合だけ、後始末からのキャンセルで結果を上書きさせない | `test_timeout_result_survives_cleanup_cancellation_and_keeps_turns`。後始末が呼出し側をcancelしてCancelledErrorを上げるmock policyで旧実装がRED → inactivity_timeout・6ターンを保持してGREEN。期限未確定のキャンセルは従来どおり伝播 |
| L-4 3 ターン数 | `app/domain/run_types.py:55`。`RunResult.turns` の未指定をNoneで表す。`app/repositories/run_repository.py` の `finish()` はNoneのときDBの既存ターン数を保持 | `test_finish_preserves_recorded_turns_when_job_result_omits_them`（outer_timeout / worker_failed / process_interruptedの3件）。旧実装は6→0でRED、修正後6を保持。`test_finish_respects_explicit_zero_turns` で明示0は保存されることも検査 |
| L-4 4/設計 | agent-plan T-205末尾へStreamEvent・後始末隔離・未指定ターン数の契約を追記。本handoffに手動確認手順を記載 | 閾値・SDK実呼出し・評価スクリプトの既定は変更なし |

開発用入口:

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-timeout-checks.mk model-timeout-test
# recipe: cd $(BACKEND) && uv run pytest tests/unit/test_claude_policy.py tests/unit/test_policy_activity.py tests/integration/test_runs.py -k "not carryover" -q
```

[RED](test-results/model-timeout-red-2026-09-13.log): **7 failed / 49 passed / 4 deselected** → [GREEN](test-results/model-timeout-green-2026-09-13.log): **56 passed / 4 deselected**。この絞込後に明示0の検査を追加し、以下の全体ゲートで確認した。既存テストは部分出力optionsのassertとfake-clockケース追加のみで、以前のメッセージ・無応答ケースとassertを保持した。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-timeout-checks.mk model-timeout-mutations
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-mutations
```

[L-4変異](test-results/model-timeout-boundary-mutations-2026-09-13.log): **3/3検出**。部分出力を無効へ戻す（1 FAIL）、期限確定後もキャンセルを再送出（1 FAIL）、未指定ターン数を無条件保存（3 FAIL）。子プロセス内だけで変異し、共有ソースは変更していない。[既存の変異ゲート](test-results/model-timeout-mutations-2026-09-13.log)も正常系2種類・故障6種類が期待どおり。

### 最終ゲート（除外なし）

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

[全出力](test-results/model-timeout-regression-2026-09-13.log):

```text
487 passed, 124 warnings in 29.76s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.579 s
✅ check: all green
```

§7が除外を許可したT-301のcarry-over4ケースはL-4への切替前にORM移行で解消済みだったため、**今回はdeselect/ignoreとも0件**。これら4件と中断中T-301のテストも含む。T-301自体の完了は別handoffで扱う。

### Claudeへ引き継ぐ実機停止系の確認手順

1. 既存のclaudeモード設定で、承認済みsample-06から新しいrunをUIの案作成操作で起動する。既存のrun 3/4は上書きしない。
2. #13の進捗と#14のstep一覧で、読取6呼出し後の生成が60秒を超えても、SDKの部分出力が続く間はrunningを保つことを確認する。トレースには本文を追加せず、ツール列・時刻・停止理由・ターン数で照合する。
3. メッセージ/StreamEventが実際に60秒途絶えた場合、終端が `inactivity_timeout` であり、SDKの後始末後も `process_interrupted` に変化せず、既存のツール呼出しターン数が残ることを確認する。外側期限で終了した場合もDBの記録済みターン数が残ることを確認する。
4. `INACTIVITY_TIMEOUT_S` はdefinition.pyの固定値で、環境変数によって一時短縮する設定口は現状存在しない。設計外の設定口は追加していない。短時間の決定的な再現は上記fake-clockテストで実施済み。実機での無応答は実際の60秒の観測対象とする。

`scripts/evaluate_local_agent.py` はlocal_dummyのまま。Codexは実評価・キー確認・`.env`の閲覧/表示を行っていない。

### 並行変更の保全

`.claude/memory.md`・`.env`は編集せず、commitしていない。**`run_repository.py` はT-301の `_has_records` ORM化と、L-4の `finish()` ターン数保持が同居している。`test_runs.py` もT-301のcarry-over移行とL-4の終端4ケースが同居している。**L-4だけをcommitする場合はこの差分を区別する必要がある。T-301のORM・migration・入力・Service/Repository・テストは未完タスクの変更として保全した。T-301は§7の「中断継続」に従い、新しい指示まで再開しない。

再レビュー依頼

---

## AD-019 対応（L-3）

2026-09-13。§7 **01:40版**の最優先指示に従い、T-301を8件GREENの区切りで中断して実施した。実モデル呼出しはなく、SDKは完全モック。希望 Status: REVIEWING。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| AD-019 1 | `app/agent/definition.py:54` に `RUNTIME_META_TOOLS=["ToolSearch"]`、`claude_policy.py:84` で13業務ツールと結合。`hooks.py` で定義取得用メタツールを許可し、その引数検査はしない | `test_runtime_tool_search_is_allowed_and_harness_tools_are_blocked`、既存SDK round-trip。下記RED **6 failed / 28 passed** → GREEN **34 passed**。業務ツール13本は不変 |
| AD-019 1 拒否名 | `claude_policy.py:32` のsafe_nameにruntimeメタツールを含める | `test_runtime_tool_name_is_preserved_in_denial_metadata`。ToolSearchをunregisteredへ潰す旧実装でRED → GREEN |
| AD-019 2 | `definition.py:55` の禁止8種へ指定のハーネス18種を追加（計26）。`claude_policy.py:85` に `tools=[]` | SDK round-tripでallowed_tools=13本＋ToolSearch、tools空、disallowed_tools26種の集合をassert。Task / SendMessageはhookで引き続き拒否 |
| AD-019 3 | `claude_policy.py:75,109,114`。結果受信済みフラグで終端理由を保持し、後続のProcessErrorによるmodel_error上書きを防止 | `test_terminal_result_takes_precedence_over_late_process_error`（max_turns / successの2ケース）。ResultMessage→ProcessError(exit 1)でRED → GREEN。結果前の例外は従来どおりmodel_error |
| AD-019 5 | `docs/requirements/agent-plan.md` 末尾へランタイムメタツール・ハーネス遮断・結果優先の契約を追記 | 設計と実装の語彙を一致させた。業務ツール一覧は変更なし |
| 変異検証の追従 | `scripts/check_agent_mutations.py` の例外本文変異を、結果優先分岐に合わせた置換位置へ更新 | `make agent-mutations`。正常系26件PASS、要求クリア漏れ2件FAIL、max_turns誤変換4件FAIL、例外本文漏出3件FAIL。既存hook変異3種類も検出 |

SDK根拠: インストール済み `backend/.venv/lib/python3.12/site-packages/claude_agent_sdk/types.py:1944` の `ClaudeAgentOptions.tools` は `list[str] | ToolsPreset | None`。同docstringに **空リストは組込ツールをすべて無効化する**と明記されているため、指示に従い `tools=[]` を優先し、disallowed_toolsを多重防御として残した。`allowed_tools` は別の許可設定。実際のCLIでのツール取得の再評価はClaude側へ引き継ぐ。

SDK `_errors.py` の `ProcessError` / `ResultError` と評価記録を確認した。SDKが結果フレームを返した後にCLIの非ゼロ終了を例外として通知する順序をモックで再現し、結果前の失敗と区別した。stderrや例外本文は保存していない。

開発用入口:

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-policy-checks.mk model-policy-test
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-mutations
```

[RED](test-results/model-runtime-red-2026-09-13.log)・[GREEN](test-results/model-runtime-green-2026-09-13.log)・[変異](test-results/model-runtime-mutations-2026-09-13.log)。既存テストは新しい許可/禁止集合へ期待値を更新した。SSOT・パス分離は維持。追加テスト6件。

### 最終ゲートと除外（CV-023）

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true PYTEST_ADDOPTS='--deselect=tests/integration/test_runs.py::test_carryover_checks_real_schema_and_does_not_copy' make check
```

T-301中断時点で失敗を実測した **carry-overの4パラメータケースだけ**を除外した。ファイル全体のignoreはせず、同ファイルの残り23件も実行している。新規human_recordsテーブルに旧テストのCREATE TABLEが衝突するためで、ORMへの移行はT-301再開時に行う。今回の結果を除外なしの回帰成功とは扱わない。

[全出力](test-results/model-runtime-regression-2026-09-13.log):

```text
463 passed, 4 deselected, 124 warnings in 25.52s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.89 s
✅ check: all green
```

L-3の変更対象はagentのdefinition/hooks/claude_policy、SDKモックテスト、変異スクリプト、agent-planと本handoff。中断中T-301の変更は保全し、ゲートのformatterによる整形以外は変更していない。`.claude/memory.md`・`.env`は編集せず、`.env`の閲覧/表示・commitは行っていない。L-3提出後に§7の許可に従いT-301を再開する。DBテストは他セッションのpytestと重ねない。

再レビュー依頼

---

## RV-030 対応（L-2）

2026-09-12。指示: CODEX-INSTRUCTIONS.md §7 **2026-09-13 00:40** 版。L-2の全項目を反映。最終 `make check` は **BE429件 / FE166件 PASS**。希望 Status: REVIEWING。SDKは完全モックで、実モデルの評価はClaudeへ引き継ぐ。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| RV-030 P2-3 | `app/agent/claude_policy.py:73`。`setting_sources=[]`、実行専用の一時ディレクトリcwdを指定 | `test_sdk_handler_round_trip_uses_existing_executor_and_records_once`。optionsの設定読込元をassert。下記開発用makeでRED **5 failed / 23 passed** のうち2件 → GREEN |
| RV-030 P2-2 | `app/domain/agent_types.py` の `PolicyHeartbeat`、`app/agent/claude_policy.py:94`、`app/agent/runner.py:60`。すべてのSDKメッセージを受信時刻つき生存通知へ変換し、bounded内で無応答時計だけを更新。ターン数・repeated_call・内側期限・閾値は維持 | `test_sdk_message_activity_controls_only_inactivity_clock`（2件、fake clock）。**20秒間隔の4メッセージ＝80秒を経てツール1回を実行**、**20秒時点の最後のメッセージから60秒停止＝80秒でinactivity_timeout・0ターン**。REDは旧実装がいずれも60秒で誤停止 → GREEN |
| RV-030 P2-1 | `app/agent/claude_policy.py:19`、`app/agent/tools.py` の `record_denial`、`app/repositories/agent_tool_repository.py:363`。permission_denialsを既存hookで固定コードに分類し、runの行ロック中に `guardrail_denied` を1件記録。原文・引数は保持しない。既知のツール名だけ `tool_use.deniedTool` へ残し、未知名は `unregistered` | `test_sdk_permission_denial_is_one_sanitized_management_event`（実PostgreSQL、SDKはモック）。未登録拒否・URL拒否の2件がRED **2 failed / 11 deselected**（イベント0件）→ GREEN **2 passed**。DB・JSONLに本文が無いこともassert |
| RV-030 P3-1 | `app/agent/claude_policy.py`。stderrコールバックを明示し破棄 | 既存round-tripテストへstderrコールバックの存在と呼出しを追加。全体ゲートPASS |
| RV-030 P3-3 | `app/core/config.py:30`。キーを `SecretStr` とし、policyへのpartialも秘匿型を保持。`get_secret_value()` は `ClaudeAgentOptions.env` 構築の1箇所だけ | `test_settings_and_partial_keep_api_key_secret` がRED（strのまま）→ GREEN。既存モード切替テストでもpartialのreprへキーが出ないことをassert |
| RV-030 P3-4 | `app/agent/definition.py` / `claude_policy.py`。指定された組込ツール8個をdisallowed_toolsへ追加。主防御のhookは維持 | round-tripテストに禁止8ツールの集合をassert。全体ゲートPASS |
| RV-030 P3-5 | `scripts/check_agent_mutations.py:23`。子プロセス内だけでClaude側3種類の変異を適用。共有ソースは変更しない | `make agent-mutations`。要求コールバックのクリア漏れ **2 failed**、max_turns写しの除去 **3 failed**、例外本文の流出 **1 failed**。正常系 **20 passed**。既存hook変異3種類も検出 |
| RV-030 P3-2・設計 | `docs/requirements/agent-plan.md` 末尾「T-205 RV-030補足」。設定読込元・cwd・禁止ツール・stderr・生存通知・拒否イベントの保存語彙を追記。`impl_version`はツール実装の版で、判断役はmodelで区別することを明記 | 設計の記録のみ。impl_versionの値は変更しない |

### 証跡

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-policy-checks.mk model-policy-test
# recipe: cd $(BACKEND) && uv run pytest tests/unit/test_claude_policy.py tests/unit/test_single_source_of_truth.py tests/unit/test_policy_activity.py -q
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/model-policy-checks.mk model-policy-denials
# recipe: cd $(BACKEND) && uv run pytest tests/integration/test_agent_tool_repository.py -k sdk_permission_denial -q
```

開発中の絞込証跡: [設定・時計RED](test-results/model-policy-review-red-2026-09-12.log)、[拒否記録RED](test-results/model-policy-denial-red-2026-09-12.log)、[GREEN（unit28件＋統合2件）](test-results/model-policy-review-green-2026-09-12.log)。一時makeターゲットは高速フィードバック用であり、完了根拠は以下の通常ゲート。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make agent-mutations
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

[変異の全結果](test-results/model-policy-review-mutations-2026-09-12.log)、[全体ゲートの全結果](test-results/model-policy-review-regression-2026-09-12.log):

```text
429 passed, 124 warnings in 19.37s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        5.918 s
✅ check: all green
```

既存テストの変更理由: SecretStrへの型変更に合わせてモック入力も秘匿型にした。直接policyを読むround-tripテストは生存通知を読み飛ばしてから終端を検査する。既存assertは保持し、SDK options・partialのrepr・executor.callが要求転送を解除することを追加で固定した。既存のSSOT・パス分離テストは変更していない。新規は秘匿型1件・fake clock2件・DB拒否イベント2件の計5件。

`.claude/memory.md`・`.env` は編集していない。`.env`の閲覧/表示・実API呼出し・commitはしていない。`frontend/tsconfig.tsbuildinfo` の既存変更を保全した。§7の明示に従い、このhandoff提出後はClaudeの実モデル評価と独立してタスクM（T-301）へ着手可能。

再レビュー依頼

---

# T-205 実モデル接続 handoff

2026-09-12。対象指示: CODEX-INSTRUCTIONS.md §7 タスク L（見出し更新時刻: 2026-09-13 00:05）。希望 Status: REVIEWING。

`AGENT_MODE` による方針選択と Claude SDK の接続を実装した。最終 `make check` は **BE 424 / FE 166 全件 PASS**。実モデルの呼出し・評価は行っていない。

## 実装と変更範囲

- `backend/app/core/config.py`: `AGENT_MODE` は `local_dummy | claude`、既定は `local_dummy`。
- `backend/app/agent/definition.py`: 実モデルIDを `MODEL_ID` に集約。既存の停止閾値・SYSTEM_PROMPT本文は変更なし。
- `backend/app/agent/claude_policy.py`: SDKの非同期入力と応答を、既存の `ToolCall` / `ToolReply` 方針インターフェースに接続。指定の model / prompt / MCP server / allowed tools / hooks / max turns / permission mode を渡す。キーは設定からSDKの環境へ渡す。
- `backend/app/agent/tools.py`: runのContextVar束縛を `bind()` に抽出。SDKタスクだけが継承する要求コールバックでrunnerへ戻し、runnerの `call()` では要求転送を解除して従来の `invoke()` 本体を実行する。**登録済みSDK handler → 同じrunのToolExecutor → runner → ToolExecutor.call → handler → ガード・スコープ検査・step/結果記録**を通る。SDK起動前に束縛とrun一致を検査する。
- `backend/app/agent/runner.py`: 方針タスク作成時にexecutorを束縛し、SDK停止の `max_turns` / `model_error` を既存 `RunResult` へ写す。ターン数・繰返し・完了判定・期限とジョブ境界は維持する。
- `backend/app/api/dependencies.py` / `backend/app/services/run_service.py`: モードからpolicyと保存モデルIDを注入。claudeでキーが未設定・空の場合、DB予約・ジョブ投入前に #12 が503 `E_EXTERNAL_SEND_NOT_APPROVED` / 「実モデルが構成されていません」を返す。
- `docs/requirements/04-db.md:940`: `model_error` の固定診断契約を追加。`05-api-ipo.md:283,605`: #12・§6の503文言を更新。
- テスト: `backend/tests/unit/test_claude_policy.py`（新規19件）、`test_single_source_of_truth.py`（既存5件を保持し実モデルID検査1件を追加）。

SDKの例外・エラー応答は固定コードのみを返し、本文をログ・トレースへ渡さない。正常なSDK終了だけでは版を完了扱いにせず、既存の `finalize_draft` 成功条件を維持する。SDK結果メッセージ後もiteratorを終端まで進め、通信の後始末を同じタスクで完了させる。中断時は応答待ちをcancelし、既存の `CANCEL_CLEANUP_S` まで後始末を待つ。

## レビュー対応

初回実装のためRV番号未発行。§7の指示項目を対応番号として記す。表中の絞込テストは開発中のRED/GREEN確認であり、完了根拠は後述の全体ゲート。

| 指摘番号 | 変更内容（ファイル:行） | REDを確認したテスト名・実行コマンド・件数 |
|---|---|---|
| L-1 設定・SSOT | `app/core/config.py:32`、`app/agent/definition.py:56`、`tests/unit/test_single_source_of_truth.py:73` | `test_agent_mode_is_explicit_and_defaults_to_local` / `test_real_model_id_is_only_defined_in_definition`。下記の初回REDは15 failed / 5 passed。既存SSOT検査は維持 |
| L-2 SDKの終了理由・例外 | `app/agent/claude_policy.py:46`、`app/agent/runner.py:112` | `test_sdk_terminal_maps_to_run_result_without_error_body`。初回REDに含む。SDK最大ターン数・一般エラー・例外・未確定終了をモックで確認 |
| L-2 ツール経路・束縛 | `app/agent/tools.py:51`、`app/agent/claude_policy.py:17` | `test_sdk_requires_bound_executor_before_query` / `test_sdk_handler_round_trip_uses_existing_executor_and_records_once` / `test_closing_policy_cancels_pending_sdk_handler`。初回REDに含む。後から追加したスコープ拒否・run不一致・並行束縛もPASS。記録欠落・run不一致検査除去の変異でFAIL |
| L-2 SDK通信終了 | `app/agent/claude_policy.py:64` | `test_sdk_terminal_drains_transport_cleanup`。同じ開発用make入口で追加RED **1 failed / 24 passed** → GREEN **25 passed**。結果直後のbreakを除去しSDKの残りの後始末を実行 |
| L-3 API・保存モデル | `app/api/dependencies.py:46`、`app/services/run_service.py:55` | `test_mode_selects_policy_and_persists_model_or_returns_http_503`。初回REDに含む。HTTP実応答202/503・コード・日本語文言・予約引数のmodel・予約/起動未実行を検査 |
| L-4 診断コード・API設計 | `docs/requirements/04-db.md:940`、`05-api-ipo.md:283,605` | 上記API・SDK終了理由の契約テストに対応。DB列・migrationの追加なし |
| L-5/6 モック検証・全体ゲート | `tests/unit/test_claude_policy.py`、本handoff | SDKはすべてモック。最終全体ゲート BE **424** / FE **166** PASS。実モデルを呼ぶテストは追加なし |

開発中の絞込入口（リポジトリのMakefileを読み、`/tmp` の一時ターゲットから実行）:

```sh
DEBUG=false CI=true make -f Makefile -f /tmp/model-policy-checks.mk model-policy-test
# recipe: cd $(BACKEND) && uv run pytest tests/unit/test_claude_policy.py tests/unit/test_single_source_of_truth.py -q
```

- [初回RED: 15 failed / 5 passed](test-results/model-policy-red-2026-09-12.log)
- [SDK後始末の追加RED: 1 failed / 24 passed](test-results/model-policy-cleanup-red-2026-09-12.log)
- [最終の絞込GREEN: 25 passed / 6 warnings](test-results/model-policy-green-2026-09-12.log)

変異は作業ツリーを変更せず、一時ディレクトリのコード複製に対してSDKモックのテストのみを実行した。規約ファイル・`.claude/`・`.env` は複製していない。

```sh
DEBUG=false CI=true make -f Makefile -f /tmp/model-policy-checks.mk model-policy-mutation
```

[変異の証跡](test-results/model-policy-mutation-2026-09-12.log): **7/7検出**。SDK最大ターン数をmodel_errorに誤変換（2件FAIL）、例外本文を返す（1件）、キー確認を除去（2件）、実モデルID保存をダミーへ変更（1件）、結果記録を除去（1件）、run一致確認を除去（1件）、モデルIDをpolicyへ直書き（1件）。これはSDK後始末テスト追加前の24件に対する結果。

既存テストの削除・弱体化はない。SSOTへの1件追加のみ。SDKの振る舞い・抽出精度を単体テストで保証したとは扱わない。

## 最終全体ゲート

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

回帰中の設定を明示して実モデルの自動起動を避けた。claudeへの切替そのものは、SDKをモックしたテスト内で設定を上書きして確認する。`make agent-eval` の既定・実装は変更していない。

[全出力](test-results/model-policy-regression-2026-09-12.log)（接続情報をマスク、作業ディレクトリを `<repo>` に置換）:

```text
424 passed, 124 warnings in 20.40s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        8.579 s
✅ check: all green
```

DB起動・既存migrationの両DB適用・索引検査・ruff・BE全体・OpenAPI/orval・型・lint・FE全体を通過。新しいmigrationはない。

## 引継ぎ・保全

- SDK接続の実評価（sample-06 / AE01）は§7どおりClaude側へ引き継ぐ。Codexはキーの実値確認・`.env` の閲覧/表示・実モデル呼出しを行っていない。
- `.claude/memory.md` は編集していない。開始時からの同ファイルと `frontend/tsconfig.tsbuildinfo` の未コミット変更を保全した。C-2が外部でcommit済みであることを確認し、T-205のみを編集した。
- commit・レビューの代行・設定規約の複製は行っていない。TODO-009等の整理やG3には着手していない。
- SDKのAPIはインストール済み `claude_agent_sdk/query.py`・`types.py`・内部clientの終了処理を確認し、[公式MCPサーバー例](https://github.com/anthropics/claude-agent-sdk-python/blob/main/examples/mcp_calculator.py)も参照した。キー投入後の実接続可否・抽出品質は今回のモック検証の範囲外。

再レビュー依頼
