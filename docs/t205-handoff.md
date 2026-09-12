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
