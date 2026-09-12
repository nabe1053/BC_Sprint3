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
