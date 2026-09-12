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
