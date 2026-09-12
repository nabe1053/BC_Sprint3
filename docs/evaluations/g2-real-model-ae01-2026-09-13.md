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

## 試行 4（run_id=6、L-5 適用後）— 失敗（run 4 と同型・再現せず）

読取 4 ページ後 61 秒で `failed / process_interrupted`、turns=3（L-4 で turns 保持は効いた）。直後の試行 5 では 201 秒の生成間隔でも停止しなかったため、
生存信号が来ない条件（思考フェーズが StreamEvent として届かない可能性）は**未確定**。L-6 で無応答発火時の診断メタデータ（直近の生存信号からの秒数・受信数）を
`job_interrupted` の observation に残し、次の再発で切り分ける（TODO-021）。

## 試行 5（run_id=7、診断サーバ・無応答 20 秒）— `max_turns` で停止（大きな前進）

| 観点 | 結果 |
|---|---|
| 生存信号 | ターン間の最大間隔 **201.5 秒**（read 後の思考）でも無応答判定されず → StreamEvent の生存信号は機能 |
| 自己修復（AD-020） | `propose_items` 1 回目 `E_REQUEST_INVALID` → 2 回目成功（14 行）。ツールエラー継続が効いた |
| ターン消費 | 40 ターン中 `record_evidence` **26 回**・`record_question` 6 回（1 件ずつ登録）。`validate_draft` は違反 **125 件**（根拠未登録が大半と推定）を返し、その後も 1 件ずつ登録して上限到達。563 秒 |
| 抽出内容 | 11 行に加え **SM95TT の「API 5CT L80 相当（*1 代替候補）」を 2C/3C/8C の別行として作成**（14 行）。R03/R04 は「置換せず代替提案可を記録」＝確認事項に残すべきで、行にするのは誤り。run 5 は 11 行で正しく、非決定的 |
| 所要時間 | 40 ターンで 563 秒（約 14 秒/ターン）。1 件ずつの登録では N06（10 分）に収まらない |
| 対処 | AD-021: `record_evidence` / `record_question` を**配列で一括登録**可能に（ツール一覧は 13 本のまま・入力が配列になる）、`MAX_TURNS` 40→80（D06 仮値更新）、システムプロンプトに「代替候補は行にせず確認事項へ」「根拠・確認事項は一括で登録」を明記。Codex L-6 |

トレース: `backend/traces/6.jsonl` / `7.jsonl`。DB: version 7（items 14 / evidences 26 / questions 6 / inventory 28）。

## 試行 6（run_id=8, case_id=9、L-6 適用後）— **合格（AE01）**

| 観点 | 結果 |
|---|---|
| 終端 | `outcome=success` / `stopReason=completed` / `versionId=8` / `isComplete=true`、`versions.finalized_at` あり。**631 秒・14 ターン** |
| ツール列（13 本の範囲内・IPO 表 1〜10 と同順） | `get_rules → list → read ×4 → propose_items(E_REQUEST_INVALID → 再送 ok 11) → record_case_header → record_evidence(E_EVIDENCE_DUPLICATE → 再送 ok 101) → record_question(6) → record_source_inventory(24) → validate_draft(違反 26) → record_evidence(26) → validate_draft(違反 0) → finalize_draft`。自己修復 2 回・違反の一括修正 1 回（AD-020 / AD-021 が効いた） |
| **AE01 の期待** | **11 行**。No.4 は `G-ITEM4-ALT` で VAM TOP / VAM 21 の 2 行（各 260 本・合算なし）、No.5 も同様（各 380 本）、No.6 `qty_state=tba`、No.7 は 5FT×6 / 10FT×6（`G-ITEM7-SPLIT`）、SM95TT は置換せず原表記、**代替提案可は明細行にせず確認事項 3 件**（顧客に代替可否を確認）。単位「本」「個」は原値 |
| インベントリ | 明細 8 → 11 行（mapped 5 / split 3）、注記・提出要領・架空文書注記は excluded / unmapped、脚注 *1〜*3 は split（複数行に関わる根拠）。合計 24 要素 |
| 確認事項 | 6 件: 代替可否 ×3（*1）、接続の最終採用 ×2（*2）、希望納期の基準（出荷 / 到着）×1。捏造・補完なし |
| D03（換算しない） | 数量・単位は原値。質量・本数の換算なし。**気づき**: 外径 `13-3/8″` → `od_value=13.375, od_unit=in`（分数→小数の表記正規化。単位は不変）。換算ではないと判断するが、06 の採点との関係で要確認（TODO-022） |
| N02 / ガードレール | トレースに原文なし（grep 0）。`guardrail_denied` 0。`agent_runs.model=claude-sonnet-5`。一時 cwd の残骸 0 |
| N06（初回案 10 分） | **631 秒 = 10 分 31 秒**で僅かに超過。思考時間（read 後 170 秒、propose 前 59 秒 等）が大半。ターン数は 14 なので `MAX_TURNS=80` は十分。D06 仮値見直しの材料（TODO-022） |

**判定: AE01 合格**（完了条件①〜⑧の判定方法どおり `validate_draft` 違反 0 → `finalize_draft`）。トレース: `backend/traces/8.jsonl`。

## 6 回の試行で潰した欠陥（T-205 L-3〜L-6）

| # | 症状 | 原因 | 対処 |
|---|---|---|---|
| run 3 | ツール呼出し 0・拒否 7 | CLI の MCP 遅延ロード（`ToolSearch`）を hook が拒否 | AD-019: メタツール許可・ハーネスツール遮断 |
| run 4/6 | 読取後 60 秒で `process_interrupted` | 生存信号がメッセージ単位・分類崩れ（未再現） | L-4: StreamEvent 生存信号・後始末隔離・turns 保持。診断メタ（TODO-021） |
| run 5 | 11 行抽出後 `tool_rejected` | ツールエラー 1 回で即中断 | AD-020: エラーを返して継続・3 連続で中断 |
| run 7 | `max_turns`（40） | 根拠 1 件ずつ 26 回・代替候補を行に | AD-021: 一括登録・80 ターン・プロンプト補強 |

---

# Phase 3 AE03（sample-02 .xlsx・換算の抑止）— 2026-09-13

## 試行 1（run_id=9, case_id=10）— 抽出は合格・実行は `process_interrupted`（機構を特定）

| 観点 | 結果 |
|---|---|
| 抽出（AE03 の期待） | **6 行**。所要量は `qty_raw="118"` `qty_value=118` **`qty_unit=t`**（質量を保持し本数へ換算しない）、外径 `339.7 mm` 原単位、肉厚・材質原表記、小計 380 / 46・合計を明細にしない。**換算値なし → AE03 の主眼は合格** |
| 終端 | `propose_items` 成功（16:30:26）の 34 秒後に `failed / process_interrupted`（turns 6）。根拠・インベントリ未登録、版未確定 |
| 機構（run 4/6 と同一・TODO-021 の答え） | uvicorn ログ「Local agent operation failed (DraftError)」「Agent background task failed (DraftError)」。①`ToolExecutor.invoke` の `begin_step`（`locked()` の `require`）が **try の外**にあり、そこで上がった DraftError がツール結果に変換されず runner → worker へ伝播 ②runner `finally` の後始末中に SDK 由来の CancelledError が到達し、`deadline_stop=False` のため `raise` → **進行中の DraftError を CancelledError で上書き** → worker が「キャンセル」で終わる ③jobs `_execute` は `worker.result()` の CancelledError を「自分がキャンセルされた」と誤読し `process_interrupted`。DB に step 8 の begin_step 行が無いことと整合 |
| 対処 | Codex L-7: `begin_step` を含む全経路をツール結果へ変換 / 後始末の CancelledError が進行中の例外・結果を上書きしない / jobs は worker のキャンセルを `worker_failed` と区別 / 例外の**コード**（固定文字列）をログに出す |

トレース: `backend/traces/9.jsonl`。DB: version 9（items 6 / evidences 0）。

## 試行 2（run_id=10、L-7 適用後）— `process_interrupted` 再発（外部キャンセル・未特定）

read 後 38 秒で `failed / process_interrupted`、turns 3。L-7 後のこの分類は「`_execute` タスク自身が外部からキャンセルされた」ことを意味する（worker の例外・キャンセルは
`worker_failed` に分類されるようになったため）。誰がキャンセルしたかは未特定 → task factory で `cancel()` の呼び元スタックを記録する診断サーバ（scratchpad `diag_server2.py`）を常用。

## 試行 3（run_id=11、診断サーバ）— **合格（AE03）**

| 観点 | 結果 |
|---|---|
| 終端 | `completed` / `versionId=11` / `isComplete=true`。**192 秒・13 ターン**。キャンセルの記録 0 |
| 抽出（AE03 の期待） | **6 行**。`qty_value=118 … qty_unit=t`（質量を保持・**本数への換算なし**）、外径 `339.7 mm` 原単位、肉厚・材質・長さレンジ原表記 |
| インベントリ | 明細 6 → 6 行 mapped、**小計 380 / 46・合計 426 は `excluded`**（明細にしない）、見出し・注記も excluded。合計 14 要素 |
| 確認事項 | 4 件: 納入希望の基準（出荷/到着）、引合番号なし、Incoterms 未明示、**「本数換算は貴社にて実施」の注記に対し換算を実施していない旨**（換算条件不足を確認事項に登録＝AE03 の期待どおり） |
| 自己修復 | `propose_items` 1 回目 `E_REQUEST_INVALID` → 2 回目成功。`validate_draft` 違反 → 根拠追加 → 違反 0 |
| 漏洩 | トレースに原文なし（grep 0） |

**判定: AE03 合格**（換算値を 1 つも出力していない・06 TEST-06 の不合格条件に該当なし）。トレース: `backend/traces/11.jsonl`。

---

# `process_interrupted` の真因（TODO-021 解決・2026-09-13）

| 事実 | 内容 |
|---|---|
| 発生 | run 4 / 6 / 9 / 10 / 12 が `process_interrupted`。いずれも worker は正常に動いていた（run 12 は開始 0.4 秒で終了） |
| 診断 | task factory で `cancel()` の呼び元を記録する診断サーバでは **cancel() 呼出し 0**、`jobs._execute` は正常終了（`cancelling=0`）。`_execute` が `process_interrupted` を作れないことを微小再現で確認（worker の CancelledError は全て `worker_failed`） |
| 真因 | `process_interrupted` を書く唯一の他経路 `RunRepository.recover_interrupted()` が **`run_lifespan`（アプリ起動時）**で `outcome='running'` の全 run を終了させる。統合テストの `TestClient(app)` は lifespan を起動し、`run_lifespan` は `get_db()` を**直接**呼ぶため依存注入の override（テスト DB）が効かず、**開発 DB octg_db** の実行中 run を殺す。失敗 5 件の終了時刻は Codex / reviewer の pytest 実行時刻と一致（LN-017 が予告していた副作用） |
| 対処（AD-023） | ①起動時回収は「`started_at + outer_timeout_s` を過ぎた run」だけを対象にする（生きている別プロセスの run を殺さない）②`run_lifespan` はテストの `get_db` override を尊重し、テストが開発 DB に触れないことをテストで固定 ③評価は当面「pytest と同時に回さない」運用（LN-027 と同じ排他） |

これで run 5 / 7 / 8 / 11 が成功し 4 / 6 / 9 / 10 / 12 が失敗した「間欠性」は、同時刻の pytest の有無で完全に説明できる。エージェント本体の欠陥ではない。
