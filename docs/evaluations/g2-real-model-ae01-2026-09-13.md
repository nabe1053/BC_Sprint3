# 実モデル評価 AE01（sample-06）— 2026-09-13

`AGENT_MODE=claude`・`MODEL_ID=claude-sonnet-5`・UI 名前空間 API 経由・開発 DB octg_db。

## 試行 1（run_id=3, case_id=4）— 失敗（環境要因・設計で対処）

| 観点 | 結果 |
|---|---|
| 終端 | `failed` / `stage_detail=draft_not_finalized`、34 秒、turns 0 |
| ツール呼出し | **0 回**。`guardrail_denied` 7 件（`E_TOOL_NOT_REGISTERED`・`deniedTool=unregistered`） |
| 原因 | Claude Code CLI 2.1.241 が MCP ツールを遅延ロードするため、モデルが `ToolSearch`（定義取得のメタツール）を呼ぶ → hook がツール一覧外として拒否 → 定義を得られず空回り（診断スクリプトで `TOOL_USE ToolSearch ['max_results','query']` → `HOOK ToolSearch -> E_TOOL_NOT_REGISTERED` を確認） |
| 良かった点 | ガードレールは設計どおり**構造的に効いた**（未登録ツールは一切実行されない）。拒否はトレースに管理イベントとして残り原文なし。資料本文はモデルに送られていない（ツールが呼ばれていないため） |
| 対処 | AD-019: `ToolSearch` を許可（業務ツール一覧は 13 のまま）。CLI が公開するハーネスツール群を `disallowed_tools` へ。Codex 短ラウンド L-3 |
| 副次の確認 | `permission_denials` のキーは `tool_name`/`tool_use_id`/`tool_input`（TODO-020 ②解消）。CLI は max_turns 後に exit 1 → `ProcessError`（`model_error` への丸め順を要確認） |

トレース: `backend/traces/3.jsonl`（git 管理外）。

## 試行 2（run_id=4, case_id=5、L-3 適用後）— 失敗（前進あり・2 欠陥を特定）

| 観点 | 結果 |
|---|---|
| ツール呼出し | **6 回成功**: `get_rules → list_case_documents → read_document p.1〜p.4`（15:10:36〜37、資料 1/1 読取。AD-019 の修正が効いた） |
| 終端 | 読取完了から **63 秒後**に `failed / stage_detail=process_interrupted`、`stopReason=failed`、**turns=0**（実際は 6 回呼んでいる） |
| 欠陥 A（設計・実装） | 生存信号が SDK メッセージ単位。モデルが 4 ページ分の明細（11 行）を **1 ターンで長く生成**する間はメッセージが来ず、60 秒で無応答判定。`include_partial_messages=True` で StreamEvent を生存信号にする必要 |
| 欠陥 B（実装） | 無応答発火時に `bounded()` が `LocalPolicyStop("inactivity_timeout")` を上げるはずが、SDK 側（anyio cancel scope）のキャンセルが worker タスクへ漏れ、`jobs._execute` の `except CancelledError` → `process_interrupted` に化けた。加えて `RunResult("failed", detail=...)` が turns を持たず、DB の turns を 0 で上書き |
| 漏洩・ガードレール | トレースに原文なし（grep 0）。`guardrail_denied` 0 件。`stage_detail` は読取中 `{"documentsRead":1,"documentsTotal":1}` で正しく進んだ |
| 対処 | Codex 短ラウンド L-4（CODEX-INSTRUCTIONS §7）。memory LN-045 |

トレース: `backend/traces/4.jsonl`。

## 試行 3（run_id=5, case_id=6、L-4 適用後）— 失敗（抽出は正しい・ツールエラーの扱いで停止）

| 観点 | 結果 |
|---|---|
| ツール呼出し | 9 回成功: `get_rules → list → read_document ×4 → record_case_header → propose_items(11 行)`。142 秒・turns 6（無応答誤判定は解消。L-4 A が効いた） |
| **抽出内容（AE01 の期待と一致）** | 11 行。No.4 は `ITEM4-CONN-ALT` グループで VAM TOP / VAM 21 の 2 行（各 260 本・合算なし）、No.5 も同様（各 380 本）、No.6 は `qty_state=tba`、No.7 は 5FT×6 / 10FT×6 の 2 行（`ITEM7-PUPJT-SPLIT`）、SM95TT を置換せず原表記保持、単位「本」「個」を原値のまま。**換算値なし** |
| 終端 | `record_source_inventory` が `E_REQUEST_INVALID`（引数がスキーマに合わない）→ runner が **1 回目のツールエラーで即 `failed / tool_rejected`** |
| 欠陥 C（設計と実装） | agent-plan 異常系 B「自分で直せる違反は再登録」・失敗条件②「同一違反 3 回」に対し、実装（T-203 節 :235 `tool_rejected` で即中断）はダミー方針時代の妥協。実モデルには**エラー内容を返して修正機会を与える**必要。加えてツール結果に返る情報が code のみだと何を直せばよいか分からない |
| 漏洩・ガードレール | トレースに原文なし（grep 0）。`guardrail_denied` 0 |
| 対処 | AD-020（ツールエラーは is_error のツール結果として返し継続。同一ツール×同一コードが連続 3 回で `failed/tool_rejected`）→ Codex 短ラウンド L-5 |

トレース: `backend/traces/5.jsonl`。
