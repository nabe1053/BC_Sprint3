# Project Memory  <!-- orchestrator 役（メインセッション）が唯一の編集責任者 -->

> 書式・ID 採番・Status 語彙・昇格ルールは `.claude/rules/memory-protocol.md` が正。
> 本プロジェクトは build-loop を使わず手動スライスループで実装する（CLAUDE.md 決定事項5）。

## 1. アーキテクチャ決定 (ADR-lite)

- [AD-001] build-loop（自律ループ）を使わず、手動スライスループで実装する。理由: スライスごとに
  内容を確認しながら進めたい / 影響範囲: memory の編集者は orchestrator 役（メインセッション）、
  レビューは reviewer サブエージェント必須（CLAUDE.md 憲法6）は維持。
- [AD-002] チケット単位は「機能グループ × 3層（BE / API / FE）」とし、**グループ内は BE → API → FE の順**で
  縦に貫く。理由: orval がバックエンドの openapi.json から生成されるため層を横断で先行させると
  手書き仮実装の作り直しが発生する / ビッグバン統合を避ける。
  影響範囲: FUNC-02〜07 は AGENT-01 1体・同一画面のため G2 に集約し、例外的に4枚（BE/API/AGENT/FE）。
- [AD-003] D02（入力上限）の**開発時仮値**を確定: 1案件あたり資料50件 / 1ファイル20MB /
  PDF 200ページ / .xlsx 50シート。理由: ②FUNC-01「上限は開発時に仮値を明示し、初版受入前に確定」。
  影響範囲: 上限は `app/core/config.py` の設定値1箇所で持ち、超過は**具体的な超過内容を返す**
  （`E_LIMIT_EXCEEDED`・X09）。**初版受入前に研修者が実値を確定すること**（§6 TODO-001）。
- [AD-004] 資料の読取ライブラリは pypdf（テキスト PDF）/ openpyxl（.xlsx・data_only）/
  標準ライブラリ email（.eml）。理由: 画像 PDF の OCR は範囲外（②FUNC-01）、マクロ・外部リンクは
  実行しない。影響範囲: openpyxl は `data_only=True` で読み、保存済み値が無いセルは
  読めた値として扱わず確認事項の材料にする。
- [AD-008] **SCR-02 は Build では実 API を使う**（03-spec の「受付表示のみで本文は読み取らない」「固定サンプルで
  案を作成」はモック段階の記述）。理由: T-102 で実際の投入・読取 API（#5・#4）が揃っており、
  ②FUNC-01 の受入基準（X01 読取不能が通知される・X03 二重投入が両方残る）は実読取でしか満たせない。
  影響範囲: T-103 は「ファイルを投入 → 実際の読取結果（5区分）を一覧表示」を作る。
  「固定サンプルで案を作成」ボタン＝エージェント起動は **T-204 の範囲**なので T-103 では作らない。
- [AD-009] 画面ルートは `/cases`（SCR-01）と `/cases/{caseId}/intake`（SCR-02）。
  ルート `/` は `/cases` へリダイレクトする。理由: 資料投入は案件スコープ配下の操作であり
  URL に案件が現れる方が API（`/cases/{caseId}/documents`）と対応が取れる。
  SCR-01 に**新規案件作成のダイアログ**を置く（#5 は caseId を要求するため、案件が無いと投入に進めない）。
- [AD-007] API の表現規約を確定（`05-api-ipo.md` 0.4 に追記済み）: JSON は camelCase /
  進捗ステータスは `intake`/`draft_review`/`staff_checked`/`review_checked` /
  #6 の範囲指定は `fromSeq`・`toSeq`（locator は形式ごとに表記が違うため範囲指定に使わない）/
  原本の保存先は `{STORAGE_ROOT}/{caseId}/{uuid4}{拡張子}`（元のファイル名を使わない・git 管理外）。
- [AD-005] 未対応形式は **投入の事実を記録したうえで 415 `E_UNSUPPORTED_FORMAT` を返す**
  （`details.documentId` に資料IDを入れる）。上限超過の 413 は記録を残さない。理由: ②FUNC-01 X01
  「未対応形式でも投入の事実を残す」と 05-api-ipo 5章#5 の 415 契約を両立させるため。
  影響範囲: `docs/requirements/05-api-ipo.md` 5章#5 と `04-db.md` 3.1（`documents.kind` の CHECK に
  `'unsupported'` を追加・migration 540727e02dcb）を更新済み。
- [AD-006] **S/MIME 暗号化 .eml は対象外**（`encrypted` 判定を実装しない。`unreadable` + issue のまま）。
  理由: sample-01〜10 に該当が無く、②FUNC-01 の対応形式にも無い。

- [AD-011] **G2 を縦に1本通すまで G3〜G6 に進まない**（バックログの順序変更）。理由: Sprint 3 の主題は
  エージェントだが、AGENT-01 は一度も動いていない（T-202 の worker は `agent_implementation_pending` で
  failed 終端する）。横幅（G4〜G6）を広げる前に T-203 → T-204 → ミニ評価でトレースを1本出し、
  設計の誤りを持ち越さない / 影響範囲: §3 の実施順を T-201・T-202 → C-1 → T-203 → T-204 →
  ミニ評価 → G3・G4（並行可）→ G5 → G6 とする。
- [AD-012] **実装は主に Codex セッションが担当し、Claude メインセッションは orchestrator に徹する**
  （指示・reviewer 起動・memory 転記・品質ゲート・commit）。理由: 研修者の決定（2026-09-12）/
  影響範囲: 恒久規約は `docs/reviews/CODEX-INSTRUCTIONS.md`。Claude は原則コードを書かない
  （レビュー指摘の修正も Codex に返す）。レビューは引き続き別エージェント（憲法6）。

- [AD-013] **SCR-01 の初版（T-103）は「表示状態・送付可否」を常に「—」＋注記とし、操作は「投入画面へ」（SCR-02）のみ**
  （2026-09-12 研修者決定）。理由: API #1 は `progressStatus` のみで、版と SCR-03 は G3 まで無い。ラベルと遷移先の
  不一致を作らない / 影響範囲: G3 で #1 を `versions` から拡張（T-302）し「案件を開く→SCR-03」を追加（T-303）。
  03-spec SCR-01 と 05-api-ipo #1 に暫定注記を書き戻し済み。TODO-008 は解消。

- [AD-014] **スライス区切りの研修者確認を省き、orchestrator が自律で回す**（2026-09-12 研修者決定）。自動で進める範囲:
  reviewer 起動 → 指摘の指示書化（CODEX-INSTRUCTIONS §7）→ 再レビュー → DONE 判定 → `make check` → commit → 次スライスの指示。
  **必ず確認する**: 設計判断（AD 級の仕様選択）・破壊的操作（削除 / reset / migration 巻き戻し）・外部 LLM 送信（D05）・スコープ変更・BLOCKED 化。
  Codex への伝達は**案 B（常駐ループ）**: Codex は `docs/reviews/CODEX-INSTRUCTIONS.md` §7 を読んでタスクを完了 → handoff に再レビュー依頼 →
  §7 の更新時刻が変わるまで待って再読、を繰り返す（指示文は同 §0）。Claude は handoff を監視して §7 を更新する。
  理由: 毎スライスで研修者の判断を仰ぐと実装が進まない / 影響範囲: CLAUDE.md 憲法7 を改定。

- [AD-015] **T-204 の完了表示は「案を作成しました」＋ versionId ＋「確認画面は次の段階で追加」の注記で止め、SCR-03 へのリンクを作らない**
  （2026-09-12 orchestrator 暫定・AD-013 と同型）。理由: SCR-03 は G3（T-303）まで無い。引き継ぎ警告の件数内訳は #22（G5）まで返らないため
  警告文＋明示確認のみ（件数を捏造しない）/ 影響範囲: T-303 でリンクを追加、T-502 で件数を追加。03-spec SCR-02 の注記⑦に対応。

- [AD-016] **D05 承認: 実モデル（Anthropic Claude API・`claude-agent-sdk`）へ接続する**（2026-09-12 研修者決定「実モデルに接続してください」）。
  送信先 / モデル `claude-sonnet-5`（`definition.MODEL_ID` 1 箇所）/ 送信対象 `references/sample-01〜10` 由来の案件のみ / 除外 / 保存条件（本文をトレース・DB に追加保存しない）は
  agent-plan.md「T-205 実モデル接続」に確定。切替は `AGENT_MODE=local_dummy|claude`（既定 local_dummy）。理由: Phase 3 の本評価はダミーでは意味を持たない（TODO-015）/
  影響範囲: T-205（判断役の差し替えのみ。ツール・hook・トレース・ジョブは不変）。**`ANTHROPIC_API_KEY` は `backend/.env` に未設定**（TODO-016・研修者作業）。

- [AD-017] **`item_edits` / `confirmations` に `undone_by`（取消者）列を追加**（2026-09-13 orchestrator 暫定。研修者確認: 朝の報告）。理由: 04-db は `undone_at` のみで
  取消操作の記録者が残らず、02:183「確認者名は実在の確認者の操作から記録する」・原則5（人の記録は記録者名必須・AI 補完なし）と整合しない /
  影響範囲: T-301 の migration と取消 API #30/#32 の入力（T-302）。04-db.md に書き戻し済み。
- [AD-018] **`item_edits.field` の語彙を確定**（2026-09-13 orchestrator）: `kind, usage_note, od_value/unit, wall_value/unit, weight_value/unit, grade, connection, range_class,
  length_value/unit, qty_value/unit, note`。`due_raw`/`place_raw` は原則4（`*_raw` 不変）を優先し初版は編集不可（03-spec SCR-04 は編集可としており齟齬 → TODO-018）。
  T-301 の未決 10 件の決定は `docs/t301-instructions.md` §0。

- [AD-019] **SDK ランタイムのメタツール `ToolSearch`（ツール定義の取得のみ・副作用なし）を allowed_tools と hook の許可対象に加える**（2026-09-13 orchestrator 決定）。
  理由: Claude Code CLI 2.1.241 は MCP ツールを遅延ロードし、モデルは `ToolSearch` で定義を取得しないと 13 ツールを呼べない。初回実評価（run 3）は
  `ToolSearch` を hook が `E_TOOL_NOT_REGISTERED` で 7 回拒否 → ツール呼出し 0・`draft_not_finalized` で失敗 / 影響範囲: `ToolSearch` は業務ツールではなく
  agent-plan のツール一覧（13 本）を増やさない。hook は `ToolSearch` の `query` が `mcp__app__` 以外のツール名を含んでも実行自体は個別 hook が止める（多重防御維持）。
  CLI が公開する他のハーネスツール（Task / SendMessage / Monitor / Cron* / Skill / Workflow 等）は `disallowed_tools` へ追加、可能なら SDK の組込みツール指定で全て無効化。

- [AD-020] **ツールエラーはモデルへ返して継続し、同一ツール×同一コードの連続 3 回で `failed/tool_rejected`**（2026-09-13 orchestrator 決定）。理由: 実評価 run 5 で
  実モデルが 11 行を正しく抽出（択一・分割・TBA・原表記保持）した直後、`record_source_inventory` の `E_REQUEST_INVALID` 1 回で runner が即中断した。
  agent-plan 異常系 B・失敗条件②（3 回）が正で、T-203 節の「1 回で中断」はダミー方針時代の妥協。ツール結果には項目別の検証メッセージ（自分の引数に対するもののみ）を返す /
  影響範囲: runner・ToolExecutor の error 経路、agent-plan:235 改定済み、L-5。

- [AD-021] **`record_evidence` / `record_question` を配列で一括登録可能にし、`MAX_TURNS` を 40 → 80 に**（2026-09-13 orchestrator 決定・D06 仮値更新）。理由: run 7 で
  実モデルが根拠 26 件・確認事項 6 件を 1 件ずつ登録し 40 ターンを使い切った（563 秒）。ツール一覧 13 本・保存単位・検証規則は不変。あわせてシステムプロンプトに
  「代替候補は行にせず確認事項へ（R03/R04）」「根拠・確認事項は一括登録」を明記（run 7 は SM95TT の代替候補を 2C/3C/8C の別行にして 14 行になった。run 5 は 11 行で正）/
  影響範囲: agent-plan ツール一覧・停止条件・T-205 L-6 補足、`definition.MAX_TURNS`、`EvidenceArguments` / `QuestionArguments`。

- [AD-022] **T-302 の未決 13 件を確定**（2026-09-13 orchestrator。`docs/t302-instructions.md` §0）: `E_FIELD_NOT_EDITABLE` は 422（`route_errors.invalid_request` が非構造違反でも
  `errors.py` の表を参照）/ #23 は `RecordService.summary` を読取専用に拡張して版の状態と案件メタを返す / AD-013 の #1 拡張（`progressStatus` 導出・`latestVersionId`）と
  **#22 最小版**（`GET /cases/{caseId}/versions`）を T-302 に含める / 訂正 n は `editCount`・`editedItemCount` の両方 / undo は 200 / #32 は `{confirmationId}` /
  数値は JSON 文字列 / 422 も code 付き（TODO-005 解消）。05-api-ipo 0.2・0.4・#32・3.6 に書き戻し済み。

- [AD-023] **起動時の run 回収は期限切れ（`started_at + outer_timeout_s` 経過）の run だけを対象にし、`run_lifespan` はテストの `get_db` override を尊重する**
  （2026-09-13 orchestrator 決定）。理由: `recover_interrupted()` が起動時に `running` 全件を `process_interrupted` にし、統合テストの `TestClient` lifespan が開発 DB に対して
  それを実行するため、pytest のたびに実評価中の run が殺されていた（run 4/6/9/10/12。TODO-021 の真因）/ 影響範囲: `run_lifespan`・`recover_interrupted`・
  `tests/integration/conftest.py`。L-8。実評価と pytest の同時実行は当面排他（LN-027）。

- [AD-024] **T-303 の未決 15 件を確定**（2026-09-13 orchestrator。`docs/t303-instructions.md` §0）: #24 に `rowMatch`（T-302 追補 N-2）/ SCR-03 に primary を置かない /
  「案件を開く」は `latestVersionId` 非 null のみ・表示状態は `progressStatus` 由来のラベル / T-204 のリンクは success∧versionId / 版履歴は #22 最小を含める /
  根拠要約列は原項番に置換 / 判断は行ごとの「記録」ボタン / 数値は丸めない / 担当者名はメモリのみ。05 #24 書き戻し済み。

- [AD-025] **T-401 の未決 10 件を確定**（2026-09-13 orchestrator。`docs/t401-instructions.md` §0）: 集計は 04-db:681 の構造定義で出し status との不一致は `inconsistent` /
  unmapped>0 は何も拒否しない / 原明細数 = status≠excluded / migration なし・版外 link は inconsistent / #27 に `coverage` / 並びは BE `(seq,id)`・強調は UI / 多重対応を含める /
  T-401 は照合集計のみ（保存は T-201・記録は T-301 済。tickets 訂正）。05 #27 に応答形を書き戻し済み。

- [AD-026] **T-402 の未決 11 件を確定**（2026-09-13 orchestrator。`docs/t402-instructions.md` §0）: `coverage` は `summary` 内 / 同パス異メソッドの越境は 405（本文の共通形は
  TODO-032）/ `UI_ONLY_SEGMENTS` に `inventory` を入れず `(method,path)` 検査で守る（05 0.3 追記）/ DTO の `position`/`excerpt` は `str` / `Literal` は domain から import /
  #27 は `documentFileName` を返す（一覧系で資料名が主表示なら API が返す）/ 未確定版は `E_NOT_FOUND`。tickets T-402 を「#27＋同パス整理」に訂正。

- [AD-027] **T-403 の未決 15 件を確定**（2026-09-13 orchestrator。`docs/t403-instructions.md` §0）: `features/versions/` に追加 / primary 0 / 「更新」は置かない（記録済みは取消のみ）/
  「元資料を開く」を含め `mutator.apiBaseUrl` を export / 集計は 9 件数＋各表下の 1 文 / 並びは `inconsistent`→`missing`→他・`hasSource=false` 先頭 / トーンは missing=warn・
  inconsistent=danger・excluded=中立 / 状態セルは保存 status と導出 judgement の 2 系統表示（CV-027）/ 説明文は数のみ / 確認者名は画面ごと / SCR-03 に「網羅性照合へ」導線 /
  `E_ALREADY_CONFIRMED` は網羅性用文言。
- [AD-028] **T-501 の未決 18 件を確定**（2026-09-13 orchestrator。`docs/t501-instructions.md` §0。04-db §3.4 / 05 3.7〜3.8・#35・6 章 / 03-spec SCR-03・SCR-06 に書き戻し済み）:
  `draft→staff_checked` は「未取消 row_match が全 items ∧ 未取消 coverage ≥1」の両方必須 / 検査順 recorder→draft 要求→順序→未照合(details に `coverageRecorded` 同乗)→網羅性 /
  同一状態への再遷移と #34 経由の review→staff も `E_STATE_ORDER` / `review_checked` からの差し戻しは `E_STATE_ORDER` / #36 は `recordedBy` のみで理由は未紐づけ行コメントを
  `"{row_code}: {comment}"` 改行連結 / `bounce_comments.bounce_id` の NULL→値 1 回 UPDATE を追記型の明示的例外に / #35・#37 は確定版なら任意状態で記録可 /
  `review_checked` 版の訂正のみ review→staff イベントを同一 Tx で積む（undo/confirm/judge は積まない・TODO-034）/ 評価確認の記録は消さず UI がイベント比較で「再確認要」を導出 /
  `from_state` に CHECK 2 本追加 / `current_state` の書込は `DraftRepository.complete` と `RecordRepository.save_state_event` の 2 箇所のみ（SSOT 検査）/ carryOver は #23 と同じ述語
  （`_has_records` は C-3 で一本化）/ `ApprovalService` 新設・Repository は `RecordRepository` 拡張 / `unresolved_count` は純粋関数を `summary` と共有 / 「差し戻し中」= 最新 bounce より後に
  review_checked イベントが無い間 / 行コメント空は新コード `E_COMMENT_REQUIRED` / `summary`(#23) は T-501 で拡張しない。理由: 設計書 4 点の一致を優先し、追記型の例外は列挙して閉じる。

- [AD-029] **T-502 の未決 18 件を確定**（2026-09-13 orchestrator。`docs/t502-instructions.md` §0。05 #1/#22/#28・03-spec SCR-03/06 に書き戻し済み）: #22 は既存 endpoint を拡張し
  `ApprovalService.list_versions_with_records` に切替 / `bounced`・`needsRecheck` は **API が導出**（純粋関数を `version_state.py` に追記。FE で 3 画面に複製しない）/ `bounced` の判定に
  最新 `review_checked` イベント時刻が要るため T-501 に追補（§7）/ #28 は 7 配列・`ConfirmationHistoryRecord` 新設で #31 応答は不変 / `errors.py` に 7 コード / #37 `reason` の `""`→None は DTO /
  **#1 に `latestSendoff` を含める**（SCR-01 の送付可否列）/ 生成所要は G6 T-603（TODO-037）/ `records` は `UI_ONLY_SEGMENTS` に足さない / `summary` 不変。
- [AD-030] **T-601 の未決 21 件を確定**（2026-09-13 orchestrator。`docs/t601-instructions.md` §0。04-db 6 章 / 05 3.10・#39 / 03-spec SCR-03 に書き戻し済み）: openpyxl（既存依存）/
  `SHEET_NAMES`・ラベル辞書は `app/domain/export_types.py` の 1 定数 / D03 は「写すだけ」を構造で固定（数値セル集合 ⊆ 保存 Decimal 集合・`float(`/`round(` 0 件の SSOT）/ 保存はディスク
  `storage/exports/{caseId}/{uuid}.xlsx`（`DocumentStorageGateway` 再利用）/ 版行 `FOR UPDATE` 下で snapshot＋exports INSERT を同一 Tx / 未確定版は `E_VERSION_NOT_FINALIZED`（`ExportRepository.lock_version`
  を別に持つ）/ ファイル名 `{case}_v{n}_{state}_{ts}.xlsx`（機械語彙・ASCII）/ 日時は `YYYY-MM-DD HH:MM:SS+09:00` 文字列（TODO-030 ⑥ 確定）/ `Decimal` をそのままセルへ / 全文字列 `write_text` で数式化防止 /
  変更・確認記録は 1 記録 1 行（judgements・bounce_comments 含む）/ 生成所要は案件情報シートに / 資料一覧は第 2 表 / `integrity` 3 値 / 記録者列は持たない（TODO-038）/
  #38 は 200 バイナリ＋`Content-Disposition`＋`X-Export-Id`。
- [AD-031] **T-503 の未決 25 件を確定**（2026-09-13 orchestrator。`docs/t503-instructions.md` §0。03-spec SCR-06 に Build 注記を追記済み）: SCR-06 新規＋SCR-03 の G5 追加（「担当者確認済みにする」
  primary・差し戻し中バナー・再確認が必要・導線）＋SCR-01 送付可否列を 1 スライス / `features/versions/` に追加 / 行コメントは明示「記録」ボタンで POST / `EvidenceDrawer` に `readOnly` /
  索引は MUI Drawer 2 モード・API 追加なし / 「変更採用」タグは出さない（TODO-039）/ review_checked 版では①両ボタン無効化 / 記録者名は確認者・判断者の 2 欄 / 要約「差し戻しコメント」=
  `unlinkedComments.length` / `useRecordMutation` に `resource:"approvals"`・`caseId?` を足し `versionsKey` も invalidate / 日時は応答値のまま（書式統一は C-3）/ SCR-01「差し戻しあり」は出さない（TODO-040）/
  SCR-04 の差し戻しコメント表示は後続（TODO-041）。理由: G5 の経路（draft→staff→review／差し戻し）を 1 スライスで閉じる。
- [AD-032] **2026-09-14 Codex 単独運用へ移行**（研修者決定。Claude のトークン枯渇）。Claude メインセッション（orchestrator）が持っていた 4 権限を Codex のフェーズへ移譲:
  **memory 編集＝転記フェーズ C のセッションのみ** / **レビュー＝実装の会話を引き継がない新しい Codex セッション**（憲法6 の「別エージェント」の解釈。同一セッションの続きで自分の差分を
  レビュー済みとしない）/ **品質ゲート `make check` と commit＝フェーズ C**（pathspec 限定・`git add -A` 禁止・LN-038/CV-023）/ **§7 は Codex 自身のキュー**（更新待ちをしない）。
  指示書が無いスライス（T-602・T-603 以降）は §0c の構成で**実装前に決定表つきで書く**。研修者に上げるのは設計判断・破壊的操作・D05・スコープ変更・BLOCKED 化・秘密情報の 6 つ（§0e）。
  影響範囲: CLAUDE.md 憲法1/6/7・決定事項6、`.claude/rules/memory-protocol.md`、`docs/reviews/CODEX-INSTRUCTIONS.md` §0〜§0e・§6b・§7。
- [AD-033] **T-603（G6 FE）の 15 決定**（指示書 `docs/t603-instructions.md` §0 が正）。要点: ①新 feature を作らず `features/versions/` に追加
  ③`Content-Disposition` の filename 取り出しは純粋関数 `parseExportFileName`（既定名へ落ちたことを `fromHeader` で区別）④Blob 保存は component 内（`shared/lib` は副作用なしのため置かない）
  ⑤`retry:false`＋実行中 disabled（**再 POST は別の出力レコードを作る**）⑥出力履歴 #39 は表示中の版のみ 1 クエリ・`integrity` はラベル文字・`storagePath`/`contentHash` は画面に出さない
  ⑦`#22` に `elapsedSec` を追加（材料は `agent_runs.elapsed_sec` を `version_id` で結線。版数に依らない 1 回の SELECT。未記録は `null`）⑨再実行は既存 `AgentRunPanel` を index 経由で再利用
  ⑩出力ボタンは outlined（primary は「担当者確認済みにする」1 つ）⑬`#40` は UI で未使用。影響範囲: `05-api-ipo.md` #22・`03-spec.md`:168 に書き戻し済み。
- [AD-034] **共有 `AgentRunPanel` に `emphasis?: "primary" | "secondary"` を追加**（既定 primary で SCR-02 は不変）。理由: 03-spec が版の履歴パネルに再実行ボタンを求める一方、
  そのまま置くと design-guidelines「primary（塗り）は 1 画面 1 つ」に反し、既存テストが実際に RED になった / 影響範囲: SCR-03 からは `emphasis="secondary"`。起動ロジック・ガードレール・二重起動防止は不変。
- [AD-035] **シナリオテスト TEST-01〜08 の Fail 修正で、研修者の就寝中に orchestrator（Claude メインセッション）が自律で決めた 5 点**（2026-09-24 研修者指示「判断は仰がずに進めてよい」。**朝の報告で研修者確認**）:
  ①#4 に `pageCount`・`unreadableLocators`（受付時の読取不能範囲）を追加 ②新 API #14a `GET /ui/cases/{caseId}/agent-runs/active`（TODO-013 の再接続を兼ねる。UI 専用）
  ③`validate_draft` に `missing_question`（期限の原文あり×TZ missing×案件レベル確認事項なし。04-db case_headers の既存規定の機械判定）・`unsplit_conflict`（数量の conflict 確認事項が選択グループ外の1行。X04）を追加
  ④SYSTEM_PROMPT とツール説明に ALT/CFL・priorValue/changeReason・根拠 field 語彙・インベントリ粒度の規則（TODO-028 を含む）⑤SDK を `--no-session-persistence` で起動（会話ログを残さない。LN-070 の調査手段は失われる）。
  影響範囲: 03-spec SCR-02・05-api-ipo #4/#14a/§3.4・agent-plan Part 1 と末尾補足に書き戻し済み。Codex 単独運用（AD-032）中だが、研修者が Claude に直接依頼したため Claude が orchestrator を兼ねた。

- [AD-036] **2026-09-24 研修者の画面確認による修正依頼（F-12〜F-17）で研修者が決めた 6 点**（2026-09-25 AskUserQuestion で確認済み）:
  ①資料の「削除」は**物理削除せず除外扱い**（`documents.excluded_at/excluded_by`・記録者名必須・取消は作らない。04-db「削除経路を作らない」を改訂）
  ②案件一覧に「最新の状態＋記録者・日時」「確認事項 残 n / 全 N」「行展開で版の記録一覧」を出す（#1 拡張。ダッシュボード＝案件一覧の列）
  ③SCR-03/05/06 に**案件切替プルダウン**を置く（AD-024/027/031 の「セレクタは作らず URL で選ぶ」を覆す）④左上の名称を「引合書整理エージェント」に変更
  ⑤画面の残骸（SCR-xx 眉・フッター・模擬期注記・Scope 2・内部 ID/ツール名/ms 表記・仮 dashboard）を消す。日時は JST・分まで ⑥読取時間の短縮は**対応不要**。
  Codex 単独運用（AD-032）中だが、研修者が Claude に直接依頼したため Claude メインセッションが orchestrator を兼ねる（AD-035 と同じ扱い）。計画: F-12〜F-17。

## 2. 確立した規約・パターン

- [CV-001] **reader（資料読取部品）の契約**: ①読取4区分は「読めた単位が1つ以上あるか」で決める
  （0 個なら `partial` ではなく `unreadable`）②例外を外へ投げず必ず `read_status` + `issues` で返す
  ③`unreadable`/`encrypted`/`unsupported`/空 のどの経路でも `ReadIssue` を1件以上残し `detail` を空にしない。
  「読めた単位」は pdf=ページ / xlsx=セル / eml=本文＋添付一覧 / text=本文（各 reader の docstring に明記）。
- [CV-002] **locator の表記体系**: `document_pages.locator` は PDF=`p.N` / xlsx=シート名 / text=`body:N`。
  **eml は `document_pages` を作らず、`email_parts` を `email:{part_role}:{seq}` で扱う**
  （2026-09-12 訂正。旧「eml 本文=`body:N`」は誤り。正は 04-db.md:686 と §3.3「T-201 補足」。
  T-203 のツールが `body:N` を出すと完了条件が永久に満たせなくなる）。
  **`document_issues.locator` を `document_pages.locator` と同値にしない**（xlsx のセル単位は `Sheet1!B1`、
  資料全体は `None`）。理由: 04-db.md の完了条件は両者を `(document_id, locator)` で差し引くため、
  同値だと範囲が丸ごと相殺され「1セルも読まずに完了」になる。
- [CV-003] **判定できない値は NULL。0 や既定値で埋めない**（`page_count` / `sent_at` / 数式セルの値）。
  「開けたか」で判定可否が決まる（開けたが中身が空、は判定できた扱い）。
- [CV-004] **入力上限は抽出の前に判定する**（形式ごとに軽量なメタデータ取得関数を用意する）。
- [CV-005] Service は ORM エンティティを生成して Repository に渡してよい。ただし
  `Session` / `select` / `commit` / SQLAlchemy の例外型を Service に持ち込まない。
- [CV-006] **Repository の例外翻訳は SQLSTATE（例 23505）か制約名で限定する。**無条件翻訳は
  誤ったエラーコードを画面に出す。
- [CV-007] 転送メールの注記（`forward_note`）は「※ で始まる行」に限って分離する。厳密な注記分離は
  FUNC-02 = AGENT-01 の責務であり reader では踏み込まない。
- [CV-008] **境界値の受入基準は「ちょうど通る」「+1 で落ちる」の2本セット**で書く（X09 型の基準）。
- [CV-009] **Presentation 層は入出力の変換と HTTP ステータスだけを持つ。**永続化（ファイル書き込み・
  パス生成）・閾値判定・データ事実の生成（`received_at` 等）は必ず Service 以下に置く。
- [CV-010] **DB の CHECK 制約で表現された語彙は、API スキーマ側にも `Literal` として二重に書く。**
  DB まで落として IntegrityError（500）にしない。応答 DTO の状態値も `str` でなく `Literal`。
- [CV-011] **`details` のキーも応答 JSON の一部。camelCase で統一する**（05-api-ipo 0.4）。
  例外ハンドラは `details` を DTO に通さず素通しするため、alias 変換が効かない点に注意。
- [CV-012] リクエスト DTO は `CamelRequestModel`（`validate_by_name=False`・camelCase のみ受理）、
  レスポンス DTO は `CamelModel`（snake_case kwargs で構築）。使い分けを崩さない。
- [CV-013] **統合ポイントの OpenAPI 出力先は `backend/openapi.json`**（`frontend/orval.config.ts` の
  target がここを読む）。別の場所へ出力すると orval が古いスキーマを読み、新規エンドポイントが
  1つもフック生成されないという気づきにくい失敗になる。

- [CV-014] 根拠の機械判定は数値だけでなく明示状態（TBA・適用なし）も対象にし、明細・案件情報・両端仕様を同じ観点で確認する。型が異なる範囲を1つだけ直して終えない。
- [CV-015] **「1箇所に集約する」と決めた資産（HTTP ステータス対応表 `api/errors.py`・保管パス検証 `document_storage.py`・停止閾値/モデル ID `agent/definition.py`）は import か注入で使い、新スライスで複製しない。**T-102 で指摘した二重化が T-202 で再発した（RV-015 P1-2/P2-3/P2-5）。

- [CV-016] **検証の単一入口は リポジトリ直下の `Makefile`**（`make check` / `check-be` / `check-fe`）。
  `--confcutdir` や専用 tsconfig で範囲を切った実行は作業中の高速フィードバック用であり、
  **「検証した」と呼ばない**。再レビュー依頼・DONE 判定の根拠は `make check` の出力とする。
  `make migrate` は**開発 DB とテスト DB の両方**に適用する（LN-013・LN-017）。
- [CV-017] **ファイル名にチケット ID を入れない**（`routes_t202.py` 型の命名を作らない）。
  チケットが閉じると意味を失い、次スライスの置き場が決まらなくなる。配置の正は
  `docs/reviews/CODEX-INSTRUCTIONS.md` §3 の表（agent/ui/common + `dependencies.py`）。

- [CV-018] **テスト用 Provider と本番 Provider で既定値が分岐する設定（retry・staleTime 等）は、本番 Provider を直接レンダリングするテストで固定する。**
  T-103 RV-019 P1-3（mutation retry）は「テスト用 QueryClient では原理的に検出できない欠陥」だった。
- [CV-019] **API 由来の内部識別子（`details.limit` 等）を画面にそのまま出さない。**i18n のラベル＋単位に写し、識別子が出ないことを否定 assert で固定する
  （T-103 RV-019 P1-2 とその変異テストが型）。未知値のときも API の `code` で分岐し、記録の有無（AD-005）と矛盾する案内を出さない（RV-024 P2-1）。

- [CV-020] **テスト用の隔離（`sys.modules` スタブ・`--confcutdir`・専用 tsconfig・隔離 exporter）は一時しのぎ。スライス完了時に必ず正規 conftest / 設定へ
  統合し、隔離を残したまま DONE にしない**（残すと後続がゲートの外側で緑になる。CV-016 の実装面。C-1 RV-026）。
- [CV-021] **テストモジュール同士を import しない。**共有ビルダ・fixture は `tests/fixtures/` に置く。integration → unit のテスト間依存はテストの層を壊す（RV-026 P3-4）。

- [CV-022] **規約ファイル（CLAUDE.md / `.claude/rules/`）を機械置換して別エージェント用の複製を作らない。**AGENTS.md 等は原典への参照 1 枚に留める。
  複製は原典と乖離し、「memory の編集者は誰か」のような単一真実源の根幹が静かに反転する（C-2 RV-029）。

- [CV-023] **同一ツリーで別スライスが進行中のときの commit とゲート**: ①commit は必ず pathspec で自スライスのファイルだけ（LN-038）②ゲートは進行中スライスの
  RED テストファイルを `--ignore` して実行し、その事実と件数を memory / commit メッセージに残す（範囲を切ったことを隠さない。CV-016 の例外条件）③pytest は同時に
  走らせない（LN-027）。Claude が pytest を回す時間帯は §7 に書く。T-205 DONE 判定時、T-301 の RED 3 ファイル＋同時 pytest で 4 failed / 1 error が出た（RV-031 後）。

- [CV-024] **並行制御（FOR UPDATE / 部分 UNIQUE / advisory lock）を主張するテストは、実 PostgreSQL の 2 セッションで「ブロックされたこと」を `pg_blocking_pids` 等で観測し、
  かつ「解放後の値」まで assert する**（LN-014 の具体化。T-301 の版ロックテストが型。no-lock 変異を検出できる）。

- [CV-025] **値と単位が同じ `*_state` を共有する列（外径・肉厚・単重・長さ・数量）は、状態ラベルを列につき 1 つだけ出す**（AD-024 ⑥の一般化。T-303 RV-039 P2-1）。
- [CV-026] **FE の整形（prettier）は品質ゲートに含める**: `make fe-lint` に `prettier --check "src/**/*.{ts,tsx}"` を足す。実装者は完了前に `prettier --write`。
  eslint だけでは 1 行詰めの未整形が通る（T-204・T-303 で 2 回 → 昇格）。

- [CV-027] **「保存値」と「導出値」を同じフィールドに載せない**（T-401: 保存 `status` と構造から導いた `judgement` を別項目）。推測の混入を防ぎ、不一致を検出可能にし、
  是正を別課題に切り離せる。外部キーで守れない参照整合性は「SQL で絞る＋純粋関数で再検査して inconsistent に落とす」の二重防御にし、混入しないことを集合の交差 0 で固定。

- [CV-028] **同パス異メソッドで名前空間を分ける設計は、`(method, path)` の存在・非存在に加えて「分離相手が在ること」を肯定形で 1 本固定する**（否定だけでは削除と分離を
  区別できない。T-402）。integration で DI を検証するときは override を `get_db` だけに絞る（Service 直差し替えは配線ミスを隠す）。

## 3. 実装バックログ（プラン状態＝ループの制御表）

| ID | スライス | 種別 | 依存 | Status | レビュー | 最終更新 |
|----|---------|------|------|--------|---------|---------|
| T-101 | G1 案件・資料の保存と読取処理（BE） | web | - | DONE | 3回+確認 | 2026-09-12 |
| T-102 | G1 案件・資料 API #1-10（API） | web | T-101 | DONE | 2回+確認 | 2026-09-12 |
| T-103 | G1 SCR-01 案件一覧 / SCR-02 資料投入（FE） | web | T-102 | DONE | 3回目 RV-025: **DONE**（新規指摘なし。P3-4/6 は記録のみ・TODO-011） | 2026-09-12 |
| T-201 | G2 成果物の保存＋完了条件の機械判定（BE） | web | T-101 | DONE | 7回目 RV-023: **DONE**（P3 4 は記録のみ・TODO-010） | 2026-09-12 |
| T-202 | G2 エージェント書込 API #15-21 / 起動・監視 #12-14（API・jobs 経由） | web | T-201 | DONE | 5回目 RV-018: **DONE 可**（P3 6 は記録のみ） | 2026-09-12 |
| C-1 | チケット名ファイルの正規配置への移動（振る舞い不変） | chore | T-202 | DONE | 1回目 RV-026: **DONE**（P3 8 は記録のみ・TODO-012） | 2026-09-12 |
| T-203 | G2 AGENT-01 本体（tools / ガードレール / runner） | agent | T-202, C-1 | DONE | 2回目 RV-022: **DONE**（P3 5 は記録のみ・TODO-009。C-1 は未完のまま） | 2026-09-12 |
| C-2 | 記録のみ P3 の整理 chore（TODO-010/012、backend/app 非接触分） | chore | C-1, T-204 | DONE | 2回目: RV-029 P2-1（`MAKEFLAGS=-j8`）を確認して DONE。残 P3 は TODO-012 ⑦・TODO-017 | 2026-09-12 |
| T-204 | G2 実行進捗のポーリング UI（FE） | agent | T-203 | DONE | 2回目 RV-028: **DONE**（P3 1 は記録のみ・TODO-012 へ） | 2026-09-12 |
| T-205 | G2 実モデル接続（`claude_policy`・AGENT_MODE 切替・D05） | agent | T-203, C-2 | DONE | 9回目 RV-038: L-8c **DONE**。L-3〜L-8c 全 DONE・AE01/02/03 合格。残 P3 は TODO-020/023/026 | 2026-09-13 |
| T-301 | G3 明細の現在値算出・人の記録（BE） | web | T-201 | DONE | 1回目 RV-033: **DONE**（P3 5 は記録のみ・TODO-025） | 2026-09-13 |
| T-302 | G3 参照 #23-26 / 記録 #29-33・#22 最小・#1 拡張（API） | web | T-301 | DONE | RV-036 DONE ＋ 追補 N-2（#24 `rowMatch`）RV-038 DONE | 2026-09-13 |
| T-303 | G3 SCR-03 Item List 確認 / SCR-04 根拠詳細（FE） | web | T-302 | DONE | 2回目 RV-041: **DONE**（P3 8 は記録のみ・TODO-030）。**G3 完了** | 2026-09-13 |
| T-401 | G4 照合集計（BE。保存は T-201・記録は T-301 済） | web | T-201 | DONE | 1回目 RV-040: **DONE**（P3 4 は記録のみ・TODO-031） | 2026-09-13 |
| T-402 | G4 照合 API #27（UI GET）＋#19 同パス整理（API） | web | T-401 | DONE | 1回目 RV-042: **DONE**（P3 4 は記録のみ・TODO-033） | 2026-09-13 |
| T-403 | G4 SCR-05 網羅性照合（FE） | web | T-402 | DONE | 2回目 RV-044: **DONE**（P3 5 は記録のみ・TODO-035）。**G4 完了** | 2026-09-13 |
| T-501 | G5 状態遷移・差し戻し・送付可否の記録（BE） | web | T-301 | DONE | Codex フレッシュセッションの独立レビューで P1/P2/P3 各 0・DONE 可（`docs/t501-handoff.md`） | 2026-09-13 |
| T-502 | G5 承認・状態 API #1,#22,28,34-37（API） | web | T-501 | DONE | 独立レビュー DONE 可（`docs/t502-handoff.md`）。AD-029 の 16 決定を反映 | 2026-09-13 |
| T-503 | G5 SCR-06 引合書承認＋SCR-03/01 の G5 追加（FE） | web | T-502 | DONE | 独立レビュー第3回で P1/P2/P3 各 0・DONE 可（`docs/t503-handoff.md`）。**G5 完了** | 2026-09-13 |
| T-601 | G6 .xlsx 5シート生成（BE） | web | T-501 | DONE | 独立レビュー DONE 可（`docs/t601-handoff.md`）。AD-030 の 21 決定を反映 | 2026-09-13 |
| T-602 | G6 出力 API #38,39,40（API） | web | T-601 | DONE | reviewer サブエージェント 1回目 RV-045: **P1 0・DONE 可**（P2-1 は並行作業由来・P3 3 は記録のみ・TODO-043） | 2026-09-13 |
| T-603 | G6 出力ボタン・版の履歴（FE・SCR-03 内）＋ #22 `elapsedSec` 追補 | web | T-602 | DONE | 3回目 RV-048: **DONE 可**（P1/P2 0・P3 2 は記録のみ・TODO-046）。**G6 完了 ＝ Phase 2 初版完成** | 2026-09-13 |
| F-1 | 改修: propose_items の引数契約とモデルの食い違い解消（数値 Schema・ツール説明・違反の全件返却・失敗内訳のトレース） | agent | T-203, T-205 | DONE | 2回目 RV-050: **DONE 可**（P1/P2 0・P3 は TODO-047）。指示書 `docs/f1-instructions.md`・`docs/f1-handoff.md` | 2026-09-24 |
| F-2 | 改修: 受付一覧のページ数・読取不能範囲（#4 拡張＋SCR-02）TEST-01 #2・TEST-02 #1 | web | T-103 | DONE | RV-051（P2 0 該当）→ DONE | 2026-09-24 |
| F-3 | 改修: 根拠ドロワーの項目対応を検証器の field 語彙に合わせる（evidenceKey 正規化・その他の根拠）TEST-04 #3・TEST-05 #2 | web | T-303 | DONE | RV-051 → DONE | 2026-09-24 |
| F-4 | 改修: 択一/矛盾/変更/根拠語彙/棚卸し粒度をプロンプト・ツール説明へ＋`missing_question`・`unsplit_conflict` の機械判定 TEST-04 #4・TEST-05 #5/#6 | agent | T-205 | DONE | RV-051 P2-2 修正 → DONE | 2026-09-24 |
| F-5 | 改修: 原明細一覧の列幅固定・折り返し（状態列が画面外）TEST-06 #3 | web | T-403 | DONE | RV-051 → DONE（jsdom 不可のためスクリーンショット検証） | 2026-09-24 |
| F-6 | 改修: 実行中 run への自動復帰（#14a）と3段階表示 TEST-04 #1 | agent | T-204 | DONE | RV-051 P2-1 修正（期限切れ run の回収）→ DONE | 2026-09-24 |
| F-7 | 改修: SDK 会話ログを残さない（`--no-session-persistence`）TEST-08 #3 | agent | T-205 | DONE | RV-051 → DONE（実測: 5 本実行で `~/.claude/projects` の run ディレクトリ増加 0） | 2026-09-24 |
| F-8 | 改修: 根拠ドロワーの各根拠に「原表記」「出典」「原文抜粋」の見出し TEST-09 #1 | web | T-303 | DONE | RV-052 → DONE | 2026-09-25 |
| F-9 | 改修: 記録者名が空の拒否を入力欄の error＋helperText で示す（網羅性確認・評価確認）TEST-11 #4・TEST-14 #1 | web | T-403, T-502 | DONE | RV-052 P3-1 修正 → DONE | 2026-09-25 |
| F-10 | 改修: SCR-02 の案作成ボタン直前に件数つきの引き継ぎ警告（#22 carryOver）TEST-16 #2 | web | T-204 | DONE | RV-052 P3-2/3 修正 → DONE | 2026-09-25 |
| F-11 | 改修: `CFL-n` の候補行を「択一」ではなく「矛盾候補（要判断）」と表示（状態列・タグ・絞り込み名・件数名）TEST-05 #6 | web | F-4 | DONE | RV-053 P2 修正 → DONE | 2026-09-25 |
| F-12 | 改修: 表示の整理（名称「引合書整理エージェント」・SCR 眉/フッター/模擬期注記/Scope 2/内部 ID の削除・日時 JST 分表示）AD-036 ④⑤ | web | - | DONE | 2回目 RV-054: **DONE 可**（P2 2 修正済み・P3 は TODO-055） | 2026-09-25 |
| F-13 | 改修: ItemList の操作性（担当者確認ボタンの位置固定・照合☑の見出し/記録者表示/左固定・要約と対応状況の折返し） | web | - | DONE | 2回目 RV-055: **DONE 可**（P1 1 修正済み・P3 は TODO-056） | 2026-09-25 |
| F-14 | 改修: レフトナビを最新版で開ける＋SCR-03/05/06 の案件切替プルダウン AD-036 ③ | web | F-12 | PLANNED | - | 2026-09-25 |
| F-15 | 改修: 案件一覧に最新状態・記録者/日時・確認事項の残数/母数・記録の展開（#1 拡張）AD-036 ② | web | F-12 | DONE | RV-056: P2 1 修正で **DONE 可**（P3 は TODO-057） | 2026-09-25 |
| F-16 | 改修: 資料投入のエラー強調・受付一覧の罫線・資料の除外（論理削除・ツールも除外）AD-036 ① | agent | F-12 | PLANNED | - | 2026-09-25 |
| F-17 | 改修: 画面を離れて戻っても直近の run の進捗/結果を表示（#14a を latest に拡張）・ポーリング再試行 | agent | F-6 | PLANNED | - | 2026-09-25 |

> **実施順（AD-011）**: T-201・T-202 クローズ → C-1 → **T-203 → T-204 → ミニ評価** →
> G3（T-301〜303）・G4（T-401〜403）は並行可 → G5 → G6。
> 並行してよいのは依存が独立でファイルが重ならない組（T-301 / T-401）のみ。規則は
> `docs/reviews/CODEX-INSTRUCTIONS.md` §5。

> **Phase 3 進捗（2026-09-13）**: **AE01・AE02・AE03 合格**（run 8 / 13 / 11）。AE02 は同時刻の pytest 下でも生存（L-8 実機確認）。AE04〜AE07 は未実施。記録: `docs/evaluations/g2-real-model-ae01-2026-09-13.md`。

> **実モデル評価 AE01 合格・2026-09-13（run 8）**: `AGENT_MODE=claude` / `claude-sonnet-5` で sample-06 が `completed`・11 行（択一 2 組・分割 1 組・TBA・原表記保持・代替は確認事項）・
> 631 秒・14 ターン・漏洩 0。6 回の試行で L-3〜L-6 の欠陥 4 件を潰した。記録: `docs/evaluations/g2-real-model-ae01-2026-09-13.md`。

> **G2 ミニ評価（⑤）合格・2026-09-12**: UI API 経由で実ジョブを通し、正常系 `completed`（明細 3・確認事項 2・違反 0・トレース漏洩 0・換算なし）と
> 対応範囲外 `failed/local_dummy_unsupported`（捏造なし）を確認。記録: `docs/evaluations/g2-mini-eval-2026-09-12.md`。Phase 3 本評価は D05 承認後。

> **Phase 2（初版）完成・2026-09-13**: G1〜G6 の全スライス（T-101〜T-603）が DONE。残りは C-3（記録のみ P3 のまとめ）と Phase 3 の AE04〜AE07。

> 人が読む説明版: `docs/tickets.md`（グループ・完了の目安つき）。本表が進捗の正。

## 4. レビュー指摘と対応履歴

- [RV-001] T-101 1回目: 重大2（未対応形式が `E_UNSUPPORTED_FORMAT` を返さない / 転送メールの引用ヘッダ
  Date・From を破棄）+ 中9 + 軽微5 → 全件修正。設計側は 05-api-ipo.md 5章#5 を orchestrator が更新（AD-005）。
- [RV-002] T-101 2回目: 中6 + 軽微7。別セッションの reviewer からも独立に 6件（暗号化 xlsx の区分欠落 /
  シートごとに毎回ブックを開く N+1 / 上限の判定順 / 未使用 BaseRepository / README のテスト DB 手順）
  → 統合して全件修正。読取契約の非対称が原因 → **CV-001・CV-002・CV-003・CV-004 へ昇格**。
- [RV-003] T-101 3回目: 中4（xlsx の issue locator がページ locator と同値で完了条件を相殺 /
  開けなかった xlsx の `page_count=0` / 空の `latest_body` パート / Service の .eml 分岐が無テスト）+ 軽微6
  → 全件修正。`IntegrityError` の無条件翻訳は **CV-006 へ昇格**。
- [RV-004] T-101 確認レビュー: **指摘なし（DONE 可）**。109 テスト PASS。
- [RV-005] T-102 1回目: 重大3（資料投入の上限判定・保存パス生成・ファイル書込が Presentation にある /
  空白のみ `caseCode` が 500 / 語彙外 `issueType` が DB まで到達して 500）+ 中8 + 軽微7 → 全件修正。
  層の責務漏れが3件同根 → **CV-009 へ昇格**。語彙の二重定義漏れ → **CV-010 へ昇格**。
- [RV-006] T-102 2回目: 中1（`details` が snake_case のまま漏れていた。implementer の「直っている」
  という報告が**誤り**で、実応答を見た reviewer が検出）+ 軽微3 → 全件修正。**CV-011 へ昇格**。
- [RV-007] T-102 確認レビュー: **指摘なし（DONE 可）**。167 テスト PASS。reviewer が
  `realpath`→`abspath` の変異検査まで行い、テストの強度を確認。

- [RV-008] T-201 1回目: P2 3件（不正Decimal入力の変換例外漏れ／TBA・両端仕様の出典検査漏れ／根拠重複エラーコード不一致）。再現テストでREDを確認し全件修正。
- [RV-009] T-201 2回目: P2 1件（案件情報の明示状態の出典検査漏れ）。due=tba・place/incoterms=not_applicableの3テストでREDを確認し修正。同種の見落としが2回あったためCV-014へ昇格。
- [RV-010] T-201 最終確認: 利用制限解除後に別reviewerが前回修正と76テストを独立確認し、残存コード指摘なし。G1 CV-011への追従としてdetailsのcamelCase回帰テストを追加、RED→GREENで77件PASS。追加差分も別reviewerが確認し9件のServiceテストPASS・指摘なし。全体回帰はユーザー指示で保留のためDONEにしない。

- [RV-011] T-202 1回目: P2 2件（DB commit失敗時のJSONL重複／evidenceの出典不足エラーコード不一致）。4件の再現テストでREDを確認。確定済みtrace_eventからJSONLを冪等再構築する方式と、エンドポイント別のエラー変換に修正。
- [RV-012] T-202 2回目: P2 1件（旧実行のJSONLを空または回収結果だけに置換）。旧failed/旧runningの2件でREDを確認し、開始イベントのない旧実行を再構築対象外として保全。
- [RV-013] T-202 最終確認: 別reviewerが62件を独立再実行しPASS・残存指摘なし。T-201 77件・Ruff・PostgreSQL追加migration制約・生成API単独型検査もPASS。全体回帰はユーザー指示で保留、全体FE型検査はG1並行作業の8件で保留。実装詳細とT-203接続点はdocs/t202-handoff.md。
- [RV-015] T-202 4回目（Codex 実装・Claude reviewer 独立。Codex 側 RV-013「残存指摘なし」の後に実施）: **DONE 不可**。P1 2（migration 未適用で全体回帰 44 ERROR / 停止閾値・モデル ID が definition.py 外に複製）+ P2 9（GET #13 が毎回 FOR UPDATE＋JSONL 全書換 / トレース書込失敗が GET 経由で実行中 run を failed に / エラー表・保管パス検証の二重化 / Pydantic メッセージ文字列からのコード復元 / #12 の 404 が契約外 / 新コードが 05 §6 に無い / ワーカー例外の握りつぶし / 外側 timeout で cancel を待たない）+ P3 9。詳細: `docs/reviews/g2-review-2026-09-12.md`。二重化3件同根 → **CV-015 へ昇格**。
- [RV-016] T-201 4回目（T-202 追随分の確認）: P1 0。T-202 によるテスト変更は改竄ではない。P2 4（走査済み/相殺の正常系テスト 0 本 / 明細の明示状態テストが 1 本 / 版行ロック直列化が SQLite で未検証 / 04-db.md:861 の索引未作成）+ P3 8。テスト追加で閉じられるため FIXING。

- [RV-017] T-201 5回目（Codex 修正 → Claude reviewer 独立確認・2026-09-12）: **DONE 不可**。P1 0 / P2 1 / P3 4。
  P2-1〜P2-3 は実体として閉じている（走査済み/相殺の正常系は他範囲が残ることまでアサート・明示状態は
  9項目×2状態を違反リスト完全一致で判定・SQLite の FOR UPDATE 限界は docstring と 04-db.md:942 に明記）。
  **残 P2: `ix_agent_run_steps_document_locator` が実 DB に無い。**`create_index` を**適用済みリビジョン
  `t201_artifacts` の中**に追記したため `upgrade head` で作成されず、orchestrator の実測では
  octg_db（今回まっさらから適用）には索引があり octg_test（既に t201_artifacts 適用済み）には無い、という
  **DB 間スキーマ分岐**が発生している。→ 新規リビジョン（down_revision = `t202_run_metadata`）で作成し、
  `t201_artifacts` 側の追記は取り消す。`test_scan_index_exists_in_model_and_migration` は migration の
  **ソース文字列**しか見ていないため false green（`tests/t201/conftest.py` が `create_all` でスキーマを作る
  構造上、原理的に適用差分を検出できない）。実スキーマ確認は `check_t201_postgres.py` 側に置く。
  P3: 残範囲を件数でなく集合一致で書く / `read_email`×非 `email:` locator の否定側テストが無い /
  CV-002 の eml 記述が 04-db と矛盾（→ orchestrator が訂正済み）/ `email_parts` の
  `UNIQUE(document_id, part_role, seq)` 未追加のまま `email:{part_role}:{seq}` を走査判定の一意キーに
  使っている（T-203 着手前の TODO として維持）。

- [RV-018] T-202 5回目（Codex 修正 → Claude reviewer 独立確認・2026-09-12）: **DONE 可**。P1 0 / P2 0 / P3 6。
  RV-015 の P1-1・P1-2・P2-1〜P2-9 を**行単位＋全体回帰＋変異検査で全件クローズ確認**（handoff の
  自己申告ではない）。退行なし（tracked テストの diff は `test_api_path_separation.py` に
  `"agent-runs"` を足す**検査強化のみ**。skip/xfail の新規導入なし）。実測 356 passed / 単一ヘッド /
  ruff 124 files unchanged。P3: ①`stage_detail` の `trace_write_failed` が既存 detail を上書き
  ②`recover_interrupted()` が起動のたびに全 run の JSONL を再構築（実行数に比例して起動が重い）
  ③`trace.sync()`（同期 I/O）を FOR UPDATE トランザクション内で実行（T-203 のツール step 単位
  export でロック保持が問題になる）④`routes_t202.py` に「フィールド名に `_` を含むか」の
  ヒューリスティックが残存（P2-4 で消したはずの名前推測の変種）⑤ruff F401（orchestrator 追加分・修正済み）
  ⑥`case_service.py` / `document_query_service.py` / `document_intake_service.py` が `app.models` を
  直接 import（T-101/T-102 由来・**別スライスの改修候補**）。

- [RV-019] T-103 1回目（Codex 実装途中 → Claude reviewer 独立・2026-09-12）: **途中段階レビュー**（components / pages 未作成、typecheck 9 エラー、jest 11/13）。
  P1 5（413 `details.limit` の値が BE 契約 `file_size|document_count|pdf_pages|xlsx_sheets` と違う `fileSizeMb` / `limitExceeded.detail` が内部識別子を表示 /
  本番 QueryClient `mutations.retry:1` が記録系 POST を再送 / #1 に表示状態・送付可否が無く「—」で回避（TODO-008）/ 「案件を開く」の遷移先が SCR-02（TODO-008））
  + P2 8（DEBUG console.log 残存 / 失敗2テストは多ルート renderHook が原因で hooks 実装は正 → LN-021 / ユニオン絞り込みを `unwrapSuccess()` に集約（CV-015）/ `ApiError` 偽装 /
  footnote に「送付承認ではない」が無い / SCR-02 i18n 不足 / `@types/jest` メジャー不一致 / `*.t202.*` が CV-017 抵触）+ P3 5。
  骨格（層配置・orval wrap・AD-005 反映）は正しく方針転換不要。詳細: `docs/reviews/g1-review-2026-09-12.md`。
  → **修正指示書: `docs/t103-instructions.md`**（orchestrator が 2026-09-12 に作成。P1〜P3 の具体的な直し方・
  未完成9件・完了条件を確定。CODEX-INSTRUCTIONS §7 タスク F から導線）。

- [RV-020] T-203 1回目（Codex 実装 → Claude reviewer 独立・2026-09-12。研修者指示で C-1 未完のまま着手）: **DONE 不可**。
  P1 1（`hooks.py:69` の URL 遮断が全引数を再帰走査し、原文に URL を含む `record_evidence.quote` / `record_question.reason` /
  `record_source_inventory.excerpt` まで deny → `runner.py:94` で実行全体が `failed`。agent-plan AE06「期待＝成功、確認事項として抽出」と矛盾。
  ダミー方針では発火せず**ミニ評価 13 ケースでは検出不能**）+ P2 5（`tool_rejected` 経路が設計に無い / 管理イベント `guardrail_denied` が
  設計書に無い / `stage_detail` が `資料 n/N` を作れず T-204 が困る / 旧 `TraceRecorder` dead code / 同一違反3回ループが既定方針で到達不能）
  + P3 6。**良い点**: TODO-006（hooks 未接続）解消、D03/D05 経路ゼロ、層配置・CV-015 遵守、ループ単体テスト無し、ミニ評価 normal は IPO 表 1〜10 と
  対応・停止系 9 語彙一致・トレース漏洩 grep ヒット 0。orchestrator 判断: P1 はコード修正（AE06 は不変）、P2-1/2 は設計書追記、
  P2-3 は T-203 で修正、P2-4 は削除承認、P2-5 は記録のみ。実測 392 passed / ruff 0。詳細: `docs/reviews/g2-review-2026-09-12-2.md`。
- [RV-021] T-201 6回目（Codex タスク A → Claude reviewer 独立・2026-09-12）: **DONE 可（条件付き）**。RV-017 残 P2 は実測で閉じた
  （両 DB `alembic current`=`add_run_step_locator_index`、`check-run-step-index` 両 PASS、`upgrade --sql` で `IF NOT EXISTS` 生成確認、
  適用済みリビジョン未編集）。P2 1（`check-run-step-index` が `check-be` の外にあり、`create_all` conftest では migration 差分を検出できず
  自動で守るものがゼロ → ゲートへ追加、Makefile 1行）+ P3 5（downgrade が常に RuntimeError / 同一索引の二重定義 / 接続先直書き 等）。
  条件の P2 を T-203 修正と同ラウンドで直した時点で DONE。tests/t201 104 passed。

- [RV-022] T-203 2回目（Codex 修正 → 同一 reviewer 独立確認・2026-09-12）: **DONE 可**。P1 0 / P2 0 / P3 5。RV-020 の P1・P2-1〜4・P3-1/2/3/5/6 を
  行単位で全件クローズ確認（P2-5・P3-4 は指示どおり記録のみ）。URL 検査は read 系5ツールの top-level スカラ引数に限定、保存先へ渡る原文の
  完全一致まで assert。`StopReason` 9 語彙不変、`tests/t202` の変更は DI モック1行のみ、`trace.py` 削除で参照 0。ミニ評価 14 ケース
  （新規 `ae06_url_in_source` = completed・原文逐語保存・外部取得ゼロ・トレース漏洩 grep 0）、既存 13 の stopReason は1回目と一致。
  変異試験 `make agent-mutations`（3変異全検出）を reviewer が再現。実測 404 passed / ruff 0 / format 139 unchanged。
  新規 P3: read 系ツール名集合が `hooks.py` と `tool_stage()` に分散 / `permissionDecisionReason` がコード文字列 / 進捗更新ごとに完全 `snapshot()`
  （N06 要確認）/ `test_agent_guardrails` の入力が Pydantic でも弾かれる `document_id` / ダミーの URL 注記対応は行頭形式限定（設計どおり）→ TODO-009。
- [RV-023] T-201 7回目（Codex 修正 → 同一 reviewer 独立確認・2026-09-12）: **DONE 可**。P1 0 / P2 0 / P3 4。RV-021 P2（`check-be: db migrate
  check-run-step-index be-lint be-test`、索引検査失敗で pytest に進まないことを `test_regression_gate.py` が実証）と P3-4（接続先を Makefile 変数から注入、
  パスワードは argv に出ない）をクローズ。P3-1（downgrade）見送りは LN-018 の趣旨からは不要だが実害ゼロで許容。新規 P3: `MAKEFLAGS=-j` 継承時に
  ゲート順序が崩れる（`.NOTPARALLEL:` 推奨）/ `INDEX_TEST_URL`（パスワード入り）がグローバル export / `export` が `TEST_DB :=` 定義より前 /
  script を make 外から叩くと KeyError → TODO-010。実測 404 passed。

- [RV-024] T-103 2回目（Codex 修正＋未完成9件実装 → 同一 reviewer 独立確認・2026-09-12）: **DONE 可（条件付き）**。P1 0 / P2 2 / P3 6。
  RV-019 の P1 5・P2 8・P3 5 を全件クローズ、未完成 9 件も実装済み。413 の 4 値を hooks / 実 HTTP 境界 / 画面の 3 層で固定、本番 Providers を
  直接レンダリングして retry=false と 415 の単発 POST を検証、AD-013 準拠（両列「—」・「投入画面へ」のみ・`openButton` 不在の否定テスト）。
  clean-architecture / design-guidelines のチェックリスト全項目 OK、モック #SCR-01/#SCR-02 と構成一致（スクリーンショット確認）。
  Codex が本番テーマの起動不具合（oklch の contrastText / divider の color-mix を MUI JS 演算に渡す）を自ら検出し `mui-color.ts` で同値変換
  （新しいデザイン判断ではない）。実測 typecheck 0 / lint 0 errors / jest 77 passed / design-lint 0。
  P2-1: 未知の `limit` 値のとき 413 でも汎用文言「一覧で記録を確認」を出し、記録が残らない AD-005 と矛盾 → **DONE 条件として修正**。
  P2-2: 上限の実数値が `ja.json` にハードコード（真実源は `config.py`）→ TODO-001 に併記。P3: 死にキー `caseCodeRequired` / `notAvailable` 二重定義 /
  利用者文言に「G3」露出 / `E_UNEXPECTED_RESPONSE` が 05 §6 外 / ノーアサート行 / 素の file input（英語 UI 露出）。
  03-spec SCR-02 にモック→実装の対応注記を orchestrator が書き戻し済み。

- [RV-025] T-103 3回目（Codex 短ラウンド → 同一 reviewer 独立確認・2026-09-12）: **DONE 可**。新規指摘なし。RV-024 P2-1（`E_LIMIT_EXCEEDED` の判定を
  details 解釈と分離、未知 `limit` でも見出し＋「記録は残っていない」hint、`unknown_kind` 非露出のテスト追加）と P3-1/2/3/5 をクローズ。
  既存テスト変更は文言更新1件・検査強化1件のみ、総件数 77→78 の純増。実測 typecheck 0 / lint 0 errors / jest 78 passed / design-lint 0。

- [RV-026] C-1 1回目（Codex → Claude reviewer 独立・2026-09-12）: **DONE 可**。P1 0 / P2 0 / P3 8。14 ファイルを `git mv`、import 行を除く旧新 diff 0
  （`test_review_fixes` の monkeypatch 文字列 2 行のみ）、テスト関数 291 / assert 611 が完全一致、旧 conftest の隔離ハック 3 種（`sys.modules` スタブ・
  動的 import・`sys.path` 挿入）を統合で除去、旧パス参照 0、`check_g2_mutations_isolated.py` 4 モード DETECTED を reviewer が再現。
  実測 BE 404 passed / FE 78 passed / lint warning 0（`orval.t202` 削除で解消）。P3: `check_t202_postgres.py` / `test_api_path_separation_t102.py` の
  チケット ID 残存 / SQLite `@compiles` がプロセス全体へ登録 / conftest 内 `TestConnection` 命名 / integration→unit のテスト間 import /
  `test_actual_application_path_separation_under_isolated_settings` の名前乖離と二重実行 / seeded の `case_code="T202"` / 空 dir 残骸 / §3 の C-1 指示残存 → TODO-012。

- [RV-027] T-204 1回目（Codex 実装 → Claude reviewer 独立・2026-09-12）: **DONE 不可**。P1 0 / P2 4 / P3 5。実行の型（202 → 2 秒ポーリング・終端/404/エラー停止・
  focus/reconnect で再開しない・二重 POST 防止）、完了判定 4 条件、413 decoder の #5 との分離、AD-015 / TODO-013 / AE05b、層配置、design（contained 1・h1 1）は全て OK。
  P2: ①03-spec SCR-02 注記⑦の「版の注記」未実装（§7 の実装範囲から落ちた）②作成後の「前版の記録は引き継がれていません」通知（X12）が無い
  ③`elapsedSec` を BE の Decimal のまま表示（小数が並ぶ）④起動結果不明で資料投入まで恒久無効化され画面内に復帰手段が無い。
  P3: 進行中 Promise を `useMemo` で保持 / 停止理由・段階の語彙が 2 ファイルに分散 / `stage=done` を未知扱い / 成功時の診断併記が未固定 /
  `docs/test-results/run-ui-checks.mk` が `/tmp` 参照の再実行不能な採取物。実測 typecheck 0 / lint 0 / jest 152 passed / design-lint 0 / BE 無変更。

- [RV-028] T-204 2回目（Codex 短ラウンド → 同一 reviewer 独立確認・2026-09-12）: **DONE 可**。P1 0 / P2 0 / P3 1。RV-027 の P2-1〜4・P3-1〜5 を行単位で全件クローズ
  （版の注記常時表示 / 明示確認した runId に紐付けた作成後通知で失敗 run・次 run へ漏れない / `Math.floor` ＋実 HTTP 境界テスト / `resetState` はネットワーク非依存で
  リセット後の再起動は 409 に落ちる / `useRef` の同一性確認 / 語彙集約と `done` の既知化 / 成功時の診断抑止）。既存 assert 削除なし、152→166 純増。
  実測 typecheck 0 / lint 0 / jest 166 passed / design-lint 0 / BE 無変更。P3-6: `agent-runs/components/__tests__/IntakeRecovery.test.tsx` が documents の
  IntakePage を描画し内部パスを mock（本番の依存方向は正）→ C-2 で置き場を整理（TODO-012 ⑧）。

- [RV-029] C-2 1回目（Codex → Claude reviewer 独立・2026-09-12）: **DONE 可（条件付き）**。P1 0 / P2 1 / P3 4。3 点証明を AST で再現（関数名 290→290・assert 611→611・
  変化した定義 6 個はすべて指示どおり）。TODO-010 全項目・TODO-012 ①〜⑥⑧クローズ。`.NOTPARALLEL:` の実効性をプローブで確認。
  P2-1: `test_regression_gate.py:28` が子 make の `MAKEFLAGS` を空にしたため `.NOTPARALLEL:` を消してもテストが通る（回帰ガード喪失）→ `"-j8"` を明示。
  P3: route-contract テストの置き場（unit が適切）/ TODO-012 ⑦未実施 / `endpoints_reference.py` docstring の旧名 / ログに絶対パス。
  未追跡 `AGENTS.md` `.agents/` `.codex/`（23:02 生成・handoff 未記載）は CLAUDE.md の機械置換で **memory 編集者が反転する等の致命的誤り** → orchestrator が
  AGENTS.md を参照 1 枚に置換し `.agents/` `.codex/` を .gitignore（CV-022）。

- [RV-030] T-205 1回目（Codex 実装 → T-203 と同一 reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 3 / P3 5。設計 7 項目（`AGENT_MODE` 既定 local / `MODEL_ID` SSOT /
  `ClaudeAgentOptions` 7 引数 / model 保存値 / 503 文言 / `model_error` 追記 / 新ツール・語彙・列ゼロ）すべて一致。**トレースを通らない経路なし**: `query()` は run 束縛タスク内のみ、
  SDK handler → `_policy_request` キュー → runner の `bind(request=None)` 配下で `ToolExecutor.call` が 1 回だけ DB・トレースに書く（contextvars コピーで構造保証、`begin_step` 1 回を
  テストで固定）。キーは `ClaudeAgentOptions.env` で子プロセスにだけ渡し `os.environ` 不変。例外は型名も残さず `model_error`。SDK 完全モック 19 件、実測 424 passed / ruff 0。
  P2: ①claude モードで hook 拒否が `guardrail_denied` に残らない（`ResultMessage.permission_denials` を捨てている）②無応答時計が「メッセージ間」でなく
  「ツール呼出し間」を測るため長い生成で偽 `inactivity_timeout` ③`setting_sources` 未指定で CLI 既定により `CLAUDE.md`/`.claude/settings.json` が文脈に入り得る（**D05 送信範囲の外**）。
  P3: SDK 子プロセス stderr が uvicorn へ直行 / `impl_version` が local のまま / キーが素の str（`SecretStr` 推奨）/ `disallowed_tools` 未使用 / 変異 7 種がリポジトリから再現不能。
  orchestrator 判断: **実評価の前に P2 3 件＋P3-1/3/4 を短ラウンド（L-2）で塞ぐ**。

- [RV-031] T-205 2回目（Codex L-2 → 同一 reviewer 独立確認・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 4。RV-030 の P2 3・P3 5 を全件クローズ: `setting_sources=[]`＋run ごとの
  一時 `cwd`（リポジトリ外・実行後削除を reviewer が実測）/ `PolicyHeartbeat` 型で無応答時計のみ更新（fake clock 両方向・2000 通で残タスク 0）/ `permission_denials` →
  hook 分類 → run 行ロック内で `guardrail_denied` を `add_step`（turns 不変・原文なし）/ `SecretStr` の復号は 1 箇所 / `disallowed_tools` 8 / stderr 破棄 /
  `check_agent_mutations.py` に claude 系 3 変異（`make agent-mutations` 8/8）。実測 429 passed / ruff 0 / format 144 unchanged。
  P3: 拒否記録が `ResultMessage` 到達時のみで seq が末尾に付く / CLI の拒否 dict キー名が実データ未確認 / `cwd` テストがリポジトリ外を直接 assert していない /
  `bounded()` の heartbeat 分岐が stream 決め打ち → TODO-020。

- [RV-032] T-205 3〜5回目（L-3 / L-4+L-5 / L-6・同一 reviewer 独立・2026-09-13）: いずれも **DONE 可**。L-3（AD-019）P2 1（設計追記→L-4 で解消）/ L-4+L-5 P2 1
  （`run_repository._has_records` の ORM 化が T-301 の `models/records.py` に依存 → 同一コミット単位と決定）/ L-6 P3 3（変異スクリプトへの取り込み漏れ / `od_value` 正規化の
  下流申し送り / 大バッチ×恒常重複の相互作用）。MAX_TURNS の SSOT テストが agent-plan 本文を正規表現で読んで照合する形になり、40 へ戻す変異で落ちることを reviewer が実測。
  実測 518 passed / ruff 0 / agent-mutations 8/8 / agent-eval 14/14。D03 意見: `13-3/8″ → 13.375 in` は単位不変・厳密可逆・原表記保持で**換算ではなく表記の正規化**。

- [RV-033] T-301 1回目（Codex → Claude reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 5。指示書 §0 ①〜⑩ 全反映。層配置（Service に ORM 参照 0・`_transaction`/`require` は
  import 共用・テスト間 import 0）、ORM/migration/実 DB `\d`/04-db の 4 箇所で CHECK・複合 FK・部分 UNIQUE・`undone_by` CHECK（`IS NOT NULL` 明示）が一致、`field` 16 語彙が
  `ItemInput.model_fields` に全て実在、版ロックは実 PostgreSQL 2 セッション＋`pg_blocking_pids` で検証、変異 10/10 を reviewer が再現、carry-over の 3 点証明。実測 518 passed。
  良い点: 訂正適用後の明細を `ItemInput` で再検証し items の対 CHECK を DB 前に守る。P3: `range_class` と `length_*` が状態列を共有（UI 文言 or 状態列分割の判断材料）/ `_undo` の
  4xx 順序が `edit` と逆 / `apply_edits` が expire 済み ORM で欠損する前提 / 型エイリアス名 / 到達しない `require`。

- [RV-034] T-205 6回目 L-7（Codex → 同一 reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 3。入口（`invoke` の try が関数先頭から・DomainError は元 code・
  予期外は `E_INTERNAL`・`fail_step` 失敗でも元応答）/ 境界（runner の想定外例外 → `worker_failed`・turns 保持）/ 後始末（`result_ready`＋`sys.exc_info()` で確定済みを判定し
  上書きしない・外側キャンセルは通す）/ 分類（jobs は `worker.result()` の CancelledError を `worker_failed`、`await wait` 自身の中断だけ `process_interrupted`）の 4 層。
  変異 2 種追加（run 9 の実障害そのものを再現）で 10/10。実測 535 passed / agent-eval 14/14。P3: 04-db の observation.code 一覧に `E_INTERNAL` 未追記 /
  `worker_failed` と `process_interrupted` の書き分けが 04-db に無い / `worker_failed` が例外とキャンセルを畳む → TODO-023 へ追記。

- [RV-035] T-205 7回目 L-8（Codex → 同一 reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 1 / P3 2。`recover_interrupted` が `outerTimeoutS` 超過の running のみ回収
  （境界 -1/0/+1 秒を凍結クロック＋実 DB で固定）、lifespan が `dependency_overrides` を通り、conftest の guard（開発 DB `AsyncSessionLocal` 生成で fail）で構造保証。
  reviewer が 02:09〜02:12 に pytest / 変異を回している間、私の AE02 run が生存（実機確認）。実測 567 passed。P2: しきい値が `recover_expired` の `limit+16`（終端保存の猶予）と
  食い違い、外側期限発火〜16 秒の窓で別プロセス起動が `process_interrupted` を先に確定し得る → L-8b で統一（述語 1 つに集約）。P3: `trace_write_failed` の JSONL 自動復旧経路が
  消えた（手動手順か再構築スクリプトを Env フェーズで）/ `limits` 不正の running run はどの回収にも掛からない（ログ 1 行）。

- [RV-036] T-302 1回目（Codex → Claude reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 5。AD-022 の 13 決定を 13/13 反映（実 HTTP で 422/400 の線引き・undo 200・
  `{confirmationId}`・数値 JSON 文字列・`note` 正規化・422 も code 付きを確認）。`route_errors` の表参照化の影響が「入力コード 12 種 × 非 400 エントリ 17 種の交差 =
  `{E_FIELD_NOT_EDITABLE: 422}` のみ」であることを reviewer が独立に再計算。OpenAPI に 10 パス、`/agent/*` に記録 API 0、model 85→137 消失 0、FE は fixture 2 行のみ。
  実測 567 passed（1 回目の 4 ERROR は並行 TRUNCATE、排他後に解消・LN-027）/ FE 166。P3: `test_api_path_separation_live.py` の basename が unit/integration で重複（orchestrator の
  命名揺れ）/ 交差集合を固定する検査が無い / `VersionCounts(**data)` が余分キーを黙って捨てる / `record_response` の属性名一致前提 / items 列追加時の #24 漏れ検知。

- [RV-037] T-205 8回目 L-8b（unit・静的確認のみ）: **DONE 可**。P2 1（`run_repository` が `app.agent.definition` を import＝Data Access → Business Logic の逆流。定数を
  `app/domain/run_types.py` へ移し definition が再公開する案 a → L-8c）/ P3 1（`RECOVERY_GRACE_S=16` と jobs の猶予 15.3 秒の結び付きを assert する 1 行）。unit 379 passed。

- [RV-038] L-8c / N-2（Codex → Claude reviewer 独立・2026-09-13）: 両方 **DONE 可**。P1 0 / P2 0 / P3 3。L-8c: `RECOVERY_GRACE_S` の定義元を domain へ、`app/repositories` →
  `app.agent` の import 0、AST 逆流検査（3 形式）と猶予算定 assert を追加。SSOT 検査は除外の付け替えで範囲拡大。N-2: `rowMatch` を版単位 1 クエリで一括取得、書込・ORM・
  migration 不変、応答 3 項目のみ（ダミー属性混入で検査）、coverage 確認では null のまま、orval model 137→138（消失 0）。実測 579 passed / tsc 0。P3: 再公開 import の
  コメント / 関数内 import をトップへ / 部分 UNIQUE 前提のコメント → TODO-027 へ追記。

- [RV-039] T-303 1回目（Codex → T-204 担当 reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 2 / P3 6。AD-024 の 15 決定を 15/15 反映（`rowMatch` で照合 ON/OFF・
  ページに contained 0・`latestVersionId` リンク・T-204 リンク・版履歴最小・レンジ/定尺長併記・丸めない・原項番列・documents index 経由・記録ボタン・担当者名メモリ・
  数量旧値別セル・既存テスト 3 箇所は置換）。BE の `consistent()` と FE の `buildEditRequest` が同条件・同 code で二重管理なし。HTML/URL/巨大 10 進をテストデータに仕込み
  否定 assert。実測 FE 261 passed / design-lint 0。P2: ①外径・単重セルで値と単位に同じ `*State` を渡し「記載なし 記載なし」の二重表示 ②prettier 未適用 6 ファイル
  （`make check-fe` は eslint のみで検出しない・T-204 でも 1 件 → 2 回目）。P3: groupCode と candidateLabel の連結 / 原表記 blockquote に項目名なし / i18next 予約 `count` /
  判断 3 列の colSpan / ドロワー開時 contained≤1 の assert なし / キーワード検索が内部識別子にヒット。

- [RV-040] T-401 1回目（Codex → Claude reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 4。AD-025 10/10 反映、04-db:681 の 3 定義と一致、保存 status と導出
  `judgement` を別フィールド、純粋関数は SQLAlchemy/datetime/HTTP を import せず版外・不明 link を例外にせず inconsistent、Repository は書込 0・固定 5 クエリ・
  `RecordRepository.version`/`active_confirmation` 借用、版分離を双方向の集合演算で固定、変異 9/9 を reviewer が再現、既存 backend の変更 0・migration 0。実測 598 passed。
  指示書 §2 と dataclass が summary 10 / entries 13 / items 8 で完全一致（T-402 の DTO 化にそのまま使える）。P3: 不明 entry link で `hasSource=True` かつ
  `sourceEntries=()`（Repository 経由では起きない）/ 版外 link が split と inconsistent の両方に入る / Service メソッド名がモジュール関数と同名 /
  `inconsistentEntryIds` は entries の部分集合とは限らない → T-402 DTO 注記 or TODO-031。

- [RV-041] T-303 2回目 O-2（Codex → 同一 reviewer 独立・2026-09-13）: **DONE 可**。P2 2 件クローズ（`DimensionValue` で共有状態の列は状態ラベル 1 回・値/単位の旧値は別々。
  実一覧のセル位置でも検査 / `fe-lint` に `prettier --check` を追加し frontend 全体 126 ファイルを整形。追加ゲートが orval の死んだオプション `prettier: true` まで露見させ
  `formatter: 'prettier'` に修正）。整形差分に機能変更なし（`git diff -w` で確認）。実測 FE 266 passed / prettier green / design-lint 0。P3: prettier のキャレット版 /
  `src/**` glob が生成物を含む（対処は `npm run orval` 再実行、と 1 行残す）→ TODO-030 に追記。

- [RV-042] T-402 1回目（Codex → Claude reviewer 独立・2026-09-13）: **DONE 可**。P1 0 / P2 0 / P3 4。AD-026 11/11。DTO は T-401 実型と 1 対 1（10/13/8/2/4）、
  ID 配列は validator 1 箇所で昇順・重複除去、`RowMatchResponse` 再利用、Literal は domain import。越境は 405 かつ `reconcile` 未呼出し、`(method,path)` 検査は
  「AGENT に GET なし・UI に POST なし・AGENT POST #19 在り」の 3 点。integration は `get_db` のみ override して正規 DI を通し、summary を dict 全体の等値比較。
  `private`/`version_id` を 7 階層に注入する非露出テスト。OpenAPI 34→35、orval model 138→146（消失 0）。実測 625 passed / ruff 0 / tsc 0。
  P3: `model_validate(from_attributes)` の再帰依存のコメント / `inconsistentEntryIds` は entries の部分集合とは限らない注記（T-403 指示書へ）/ basename 重複（C-3）/
  handoff に「次スライスへ渡す契約」節を置く運用。

- [RV-043] T-403 1回目（Codex → Claude reviewer 独立・2026-09-13）: **P2 1 / P3 4 / P1 0**。AD-027 15/15 反映、`make check-fe` 24 suites / 326 PASS・design-lint 0・prettier green・
  `backend` 無変更・generated 手編集なし・変異 9 種全検出を reviewer が再現。P2-1: `ja.json` `versions.inventory.notice` が N03 注記の**見出し句だけ**で、03-spec SCR-05:318 と
  `mockup.html:410` にある理由（抽出処理が読まなかった範囲は表に現れない）と行動（全ページ・別紙・追加明細を元資料で確認）が欠落 → §7 タスク R-2 で修正。
  P3: ①`notice/requiredNote/undoNote` の文体（常体）②同名資料の「元資料を開く」`aria-label` が重複・`key={index}` ③範囲一覧が entries 由来で要素 0 の資料が出ない（AD-027 ⑩どおり。#4 で補完は G5 以降）
  ④fixtures のインライン `import()` 型 → TODO-035。

- [RV-044] T-403 R-2（同一 reviewer 独立・2026-09-13）: RV-043 **P2-1 / P3-1 をクローズ**（notice をモック原文どおり lead＋body の 2 文に復元・強調は `tokens.typography.weight.bold` のみ・
  文体を敬体に統一）。既存 assert は削除せず期待更新、`make check-fe` 24 suites / **327 PASS**・design-lint 0 を再現。**DONE**。新規 P3-5（追加ケースのみ `test(`＋英語名。他は `it(`＋日本語）→ TODO-035 ⑤。


- [RV-045] T-602（reviewer サブエージェント・独立・2026-09-13）: **P1 0 件 → DONE 可**。現物確認: endpoint→Service→Repository の一方向（Repository 直叩き・生 SQL なし）/
  #38 は `ExportResult.content` をそのまま返す（再読込・再生成なし）/ 非空 body は Service 未呼出しで 400 / `E_VERSION_NOT_FINALIZED`→409 は `errors.py` の表 1 箇所 /
  パス境界（AGENT POST `/evidence` あり・UI GET `/evidence` あり・逆経路なし・`/agent/**/exports` なし）/ mutator の JSON 経路は変更前と等価 / 生成物に手編集なし。
  P2-1 は**同一ツリーで T-603 を並行実装していたため `make check` が再現できない**という手続き上の指摘（T-602 のコード起因ではない。T-603 完了後に再現して解消）。
  P3: ①非空 body を全量バッファしてから 400（ヘッダ先読みで弾ける）②同一ファイル内に射影イディオム 2 種（`model_validate` と `record_response`）③`Content-Disposition` の
  ASCII 安全性が T-601 のドメイン関数にしか無く API 層に境界テストが無い → TODO-043。


- [RV-046] T-603（reviewer サブエージェント・独立・1回目・2026-09-13）: **P1 0 / P2 7 / P3 7**。裏取り済み: `elapsedSec` は N+1 なし（SELECT 数一定テストを実行）・Decimal 非丸め・
  `emphasis` 既定 primary で SCR-02 不変・design-lint 0。対応: P2-1（未解決注記の未実装）→実装 / P2-4（二重出力が `isPending` 依存・同一版のボタン 2 つ）→版ごとの `mutationKey`＋`useIsMutating`＋ref ロック /
  P2-5（履歴読取の失敗に POST 用文言）→専用キー / P2-6（`retry:false` が既定に隠れて変異検知できない）→既定 retry 有効のクライアントで検証 / P2-7（見出し右ボタンが未固定）→画面テスト追加 /
  P2-8（03-spec:199 の送付可否併記が欠落）→併記。**P2-3 は事実誤認**（当該テストは T-503 で既に単体描画。T-603 の差分は mock 追加のみ）。
  **P2-2（未生成 ⑪ が `loadError` に畳まれる）は未対応** — 03-spec:237 と T-503 の既存契約が両立せず設計判断のため TODO-044。P3 は 5 件対応・2 件記録（TODO-045）。


- [RV-047] T-603（reviewer サブエージェント・独立・2回目・2026-09-13）: **P1 0 / P2 1 / P3 5**。1 回目の対応はすべて妥当と確認（レビュアーが `retry:false` と `mutationKey` の**変異を実際に試して**効いていることを検証）。
  P2-3 を「事実誤認」として据え置いた判断・P2-2 を TODO-044 へ上げた判断も妥当と追認。
  残 P2 = **二重出力の防止機構にテストが無い**（`../hooks` を丸ごと mock していて `mutationKey`/`useIsMutating`/`lock` が一度も実行されていなかった）→ `export-wiring.test.tsx` を新設し変異検知まで確認。
  P3 5 件（`notGenerated` の到達不能・`unresolvedAtExport` 未使用・版一覧行の列ラベル・`revokeObjectURL` の同期実行・`elapsed_sec` の重複行仮定）はすべて対応。


- [RV-048] T-603（reviewer サブエージェント・独立・3回目・2026-09-13）: **P1 0 / P2 0 → DONE 可**。レビュアーが `mutationKey` の変異を自分で実行して `export-wiring.test.tsx` が落ちることを確認（復元も byte 一致で検証）。
  P3 対応 5 件・退行なし（既存テストの削除行は T-501/502/503 由来、BE 側はむしろ強化）・`make check` BE 817 / FE 446・35 suites を再現・design-lint 0・03-spec SCR-03 の要素（:178・:193-:201・:215-:217）を全て実装済みと確認。
  新規 P3 2 件: ①`export-wiring.test.tsx` の 2 本目（別版の分離）は変異で落ちない弱い検査 ②`useExports` が `<details>` の開閉と無関係に初回描画で発火する（TODO-045 の直接原因）→ TODO-046。
- [RV-049] F-1 1回目（reviewer サブエージェント）: P2 1。状態と値のヒント文とツール説明が「stated なら値が必要」の片方向だけで、`dueState=tba`＋`dueRaw` を渡すと LLM を stated へ誘導する → 両方向の文に修正し、逆方向のテストを追加。P3 5（「全件返す」が不正確 → 修正。残りは TODO-047）
- [RV-050] F-1 2回目: P1/P2 0・**DONE 可**。新しい P3 1（ヒント文が単位に触れない。実装も拒否しないので誤りではない → TODO-047）
- [RV-051] F-2〜F-7 1回目（reviewer サブエージェント・独立）: P1 0 / P2 2 / P3 3。P2-1 自動復帰が期限切れの running（再起動で取り残された run）に戻り、起動ボタンが「準備中」のまま解除経路を失う
  → `RunService.active_run` で `recover_expired` を先に通す（統合テストで RED→GREEN）。P2-2 プロンプト規則を agent-plan 末尾補足だけに書き Part 1 の写しを更新していない → Part 1 に同文を追加。
  P3: 全角コロンの JSX 直書き → i18n 化／xlsx のセル単位 locator が長く並ぶ → 先頭3件＋「他 n 件」（どちらも対応済み）／F-5 は jsdom で検証不能・`useActiveRun` 単体テストなし・「その他の根拠」は field 名を出さない（記録のみ・TODO-050）。

- [RV-052] F-8〜F-10 1回目（reviewer サブエージェント・独立）: P1/P2 0・**DONE 可**。P3 4: ①評価確認の欄のエラーが名前を入れても次の操作まで残る → `onName` で E_RECORDER_REQUIRED だけ解除（修正）②引き継ぎ件数の取得失敗に role・再取得が無い → role=alert＋再取得（修正）③文言「判断 n件」が 03-spec「確認事項の判断 n件」と不一致 → 仕様にそろえた（修正）④TEST-13 #5 は再現せず未修正 → TODO-053。
- [RV-053] F-11 1回目（reviewer サブエージェント）: P1 0 / P2 1 / P3 4・DONE 可。P2 件数「択一グループ」が CFL も数える → 表示名を「択一・矛盾グループ」に（BE・API は不変・03-spec 追随。件数を2つに分けるのはスコープ変更なので見送り）。P3: 表示・絞り込みのテストが無い → 3件追加（修正）／モック mockup.html が「択一候補」のまま・色判定の正規表現に「矛盾候補」が無い → TODO-054／承認画面の表のグループ列に種別ラベルが無い（ID 接頭辞で読める・仕様違反なし）→ TODO-054。
- [RV-054] F-12（reviewer サブエージェント 2 回）: 1回目 P2-1 ブランド名が 232px 幅で 1 字折り返す恐れ → fs3＋nowrap（実ブラウザで 1 行を確認）／
  P2-2 資料 ID を消しただけで「どの資料か」が失われた → `AgentRunPanel.documentNames` でファイル名に置換／P3 は 0.1 秒未満表記・`job_interrupted` ラベル・`i18n.exists` で一元化・D02 表記の言い換え＋検出を修正。2回目 **DONE 可**（残 P3 は TODO-055）。

- [RV-055] F-13（reviewer サブエージェント 2 回）: 1回目 P1 左固定のセレクタ `td:first-of-type, th:first-of-type` が行 ID の `th scope=row` にも当たり、横スクロール時に☑を隠す → 専用 class `sticky`＋DOM テスト。
  P3 は 03-spec 書き戻し・要約列に確認事項番号（判断欄と対応づけ）を修正。2回目 **DONE 可**（残 P3 は TODO-056）。

- [RV-056] F-15（reviewer サブエージェント 1 回＋修正）: P2 記録展開の 3 状態のうち空・読込中のテストが無く、テスト名が「失敗・空」を名乗っていた → 空・読込中を個別に検証し改名。
  P3 のうち `version_summaries` の型注釈を修正。#1 の SELECT 回数予算は 2→5（案件数に依らず一定・`test_api_approvals`）。**DONE 可**（残 P3 は TODO-057）。

## 5. 学び・ハマりどころ（再発防止）

- [LN-001] **reader を1つ直したら、残り3つを同じ観点で必ず見る。**3ラウンド連続で「1つだけ直して他が非対称」
  が発生した。修正時は 4 reader × 5区分の表を毎回埋めて差分を確認する。
- [LN-002] **テストの件数は層の保証にならない。**95件 PASS の時点で Service の `.eml` 分岐は1度も
  実行されていなかった。形式 × 正常/異常の分岐カバレッジを明示的に数える。
- [LN-003] サブエージェントにレビューを依頼する前に、**必ず `uv run pytest tests/ -q` の結果を添える**。
  テストと実装がずれた状態でレビューに回ると、指摘が実態と噛み合わない。
- [LN-004] Python の `cp932` は不正バイトでも私用領域にマッピングして「デコード成功」しがち。
  「どの文字コードでも読めない」テストデータには `\x81\x00` のような不正マルチバイト先頭バイトを使う。
- [LN-005] 「記録は残したうえでエラーを返す」設計（415）と「受付自体を拒否する」設計（413）は非対称。
  API 層はこの2つを別々に扱う必要がある。
- [LN-006] **「直した」という自己申告を信じない。**T-102 で implementer が「details は camelCase で出ている」
  と報告したが、片側のコードしか見ておらず実際は snake_case で漏れていた。**実応答（HTTP レスポンス）を
  アサートするテストが無い箇所は、直っていないと疑う。**
- [LN-007] Pydantic の `min_length=1` は**空白のみの文字列を通す**。必須文字列は
  `StringConstraints(strip_whitespace=True, min_length=1)` とセットで使う。
- [LN-008] **ファイルを書く統合テストは `STORAGE_ROOT` を `tmp_path` に差し替える。**DB は TRUNCATE
  されてもディスクは残り、実行のたびに孤児ファイルが溜まる。
- [LN-010] **orval の `mutator` は `output.override.mutator` に書く。**`output` 直下に書くと orval は
  黙って無視し、生成コードが素の `fetch`（baseURL が効かない・非 2xx を投げない）になる。
  Foundation から T-102 まで気づかれず、画面を作る T-103 で発覚した。
  **生成物が `customInstance` を呼んでいるか**を統合ポイントで確認する。
- [LN-011] `@types/jest` が devDependencies に無く、最初のテストを書いた時点で `npm run typecheck` が
  壊れた。テストが1本も無い状態では気づけないギャップ。
- [LN-009] パス検証のテストは「変異させたら落ちるか」で強度を測る（`realpath`→`abspath` に戻したら
  落ちること）。通るだけのテストは退行を検知しない。

- [LN-012] DBとファイルを同じ結果として扱う処理は、commit失敗・再試行・プロセス中断・旧記録を含めて検証する。再構築は開始時からの確定イベントがある場合だけ行い、不完全な記録で既存ファイルを置換しない。
- [LN-013] **ORM に列を足したら同じ手順の中で migration をテスト DB へ適用する。**`tests/conftest.py` が `Base.metadata` で TRUNCATE するため、モデルだけ先行すると無関係な既存統合テストが全滅する（T-202）。
- [LN-014] **SQLite インメモリのテストは `with_for_update()` を検証しない**（SQLAlchemy の SQLite 方言は FOR UPDATE を出力しない）。「行ロックで直列化した」は PostgreSQL 2セッション確認か docstring 明記なしに DONE にしない。
- [LN-015] **レビュー対象はスナップショットで固定する。**別セッション（Codex）が並行編集中で、レビュー中にテスト数が 55→60 に変わった。handoff の自己申告数値は着手時点で古い前提で扱う。
- [LN-016] 業務エラーコードは例外側（`PydanticCustomError(code)`）で持ち、Presentation でメッセージ文字列やフィールド名から復元しない。GET（安全メソッド）に永続化・行ロック・ファイル書込を持たせない。

- [LN-017] **統合テストは開発 DB（octg_db）のスキーマにも依存する。**`tests/integration/conftest.py` は
  `get_db` を override してテスト DB を使わせるが、`TestClient(app)` の lifespan で走る起動処理
  （T-202 の残存 running 回収）は**アプリ本体のエンジン（`settings.DATABASE_URL`）**を使う。
  テスト DB にだけ migration を当てても `tests/integration` は全滅したままになる。
  `make migrate` が両方に適用する理由がこれ。（将来的には lifespan 側も override 可能にするのが正）

- [LN-018] **適用済みの Alembic リビジョンを後から編集しても `upgrade head` では反映されない。**
  スキーマ変更の「完了」は migration のソース検査ではなく、**実 DB（`\d {table}`）で確認する**。
  `Base.metadata.create_all()` でスキーマを作るテストは、migration の適用差分を原理的に検出できない
  （T-201 の索引が「モデルと migration にはあるがテスト DB には無い」状態で緑になっていた）。

- [LN-019] **副作用禁止（GET は書かない）の検証は、mock の「呼ばれないこと」で終わらせない。**
  `session.execute` を包んで `_for_update_arg is None` と `commit` 禁止をアサートすると、
  実装を書き換えても検出力が落ちない（T-202 P2-1 の閉じ方）。
- [LN-020] **同種のレビュー指摘が2度出たら、直すのではなく規約自体をテストで固定する。**
  「1箇所に集約」の指摘は T-102 → T-202 で2度出た。`test_single_source_of_truth.py` /
  `test_api_path_separation.py` の形（ソースを機械検査する単体テスト）にすると再発が止まる。

- [LN-021] **TanStack Query の hooks テストで `renderHook` を2回呼ばない**（React ルートが2つになり、
  別ルートの `result.current` に invalidate 結果が届かず「再取得されない」と誤診する）。list と mutation は
  1回の `renderHook(() => ({ list, mutate }))` で取るか、`queryClient.getQueryData()` で検証する（T-103 RV-019 P2-2）。

- [LN-022] **ガードレールは「禁止する対象（取得・送信の意図を持つ引数）」と「記録する対象（原文 quote / excerpt / reason）」を分けて設計する。**
  引数全体の再帰走査で URL を弾くと、原表記を保存する記録系ツールと衝突し別のガードレール（原表記の保存）を壊す（T-203 RV-020 P1）。
- [LN-023] **評価シナリオで発火しないガードレールは評価で検出できない。**ダミー方針が禁止パターンに到達しないと 13 ケース全 PASS でも設計乖離が残る。
  ガードレールごとに「発火する入力」を1本ずつミニ評価に持つ（AE06 は追加が必要）。
- [LN-024] **管理イベント名・`stage_detail` の固定コードを追加したら、同じ変更で agent-plan / 04-db §3.2 の一覧へ追記する。**
  一覧が閉じている前提の機械検査は評価スクリプト側にしか無く、設計書が先に更新されないと乖離が静かに増える（RV-020 P2-1/2）。
- [LN-025] **適用済みリビジョンを編集してしまった後の収束は「旧リビジョンを書き戻さず、新リビジョン + `if_not_exists=True`」で行う。**
  alembic 1.13 / SA 2.0 で `CREATE INDEX IF NOT EXISTS` が出ることは `alembic upgrade <prev>:head --sql`（DB に触らない）で事前確認できる。
  結果として同一索引の定義が2リビジョンに分かれる（t201_artifacts と add_run_step_locator_index）ことは記録しておく。
- [LN-026] **`create_all` ベースの conftest は migration 由来のスキーマ差分を原理的に検出できない。**スキーマ契約の回帰検出は実 DB を読む検査に置き、
  かつ `make check-be` の内側（pytest か Makefile の依存）に入れないと守られない（RV-021 P2）。

- [LN-027] **`octg_test` への pytest 同時実行はデッドロック／大量 fail する。**conftest の `TRUNCATE … CASCADE` と `FOR UPDATE` 行ロックが待ち行列を
  作り両方止まる（reviewer 2体が独立に遭遇: 21 failed/113s → 直列で 404 passed/22s）。Codex 実装 × Claude レビューの並行運用では全体回帰の
  実行タイミングを排他するか、レビュー用にテスト DB を分ける。「落ちた」と報告する前に `pg_stat_activity` で他の実行を確認する。
- [LN-028] **ガードレールの修正には「過剰遮断へ戻す」「検査を外す」の両方向の変異試験を付ける。**片方向だけでは固定できていない。
  T-203 で `scripts/check_agent_mutations.py`（子プロセス内でメモリ上だけ差し替え、作業ツリーを汚さない）として常設化（`make agent-mutations`）。
- [LN-029] **LN-018 の適用範囲は「revision ID / down_revision / upgrade の内容」。**未実行の `downgrade()` の訂正は適用済み DB との整合を壊さないので対象外。
- [LN-030] **設計書への追記は「実装の語彙一覧」（管理イベント名・stage_detail 固定コード・observation.code）と1対1で列挙する。**レビューが grep 照合で済む。

- [LN-031] **MUI v5 の `palette` に渡す色は JS 色演算の対象になる。**`oklch()` / `color-mix()` をそのまま渡すと起動時例外。CSS で使うトークン値と
  MUI の JS に渡す値の変換境界を 1 関数（`shared/theme/mui-color.ts`）に閉じ、同値性をテストで固定する（T-103）。

- [LN-032] **「振る舞い不変」の chore は 3 点で機械的に証明する**: import 行を除いた旧新 diff・テスト関数名の集合・assert 総数。reviewer が同じ 3 点を
  再現すれば P1 の有無が 1 ラウンドで確定する（C-1）。

- [LN-033] **完了合図の監視は表記に依存させない。**Codex の「希望Status: T-204 REVIEWING」を期待したが実際は「希望StatusはREVIEW」で、
  監視が 1 時間以上検知できなかった。合図は指示書側で固定文字列（例: レビュー番号 `RV-0xx 対応`）を指定し、監視はそれだけを見る。
- [LN-034] **03-spec の Build 実装対応注記で後続スライスへ送った UI 要素は、そのスライスの指示書に 1 行ずつ転記する。**注記⑦の 3 項目のうち
  「版の注記」だけが §7 タスク I から落ち、そのまま未実装になった（RV-027 P2-1）。
- [LN-035] **BE が Decimal で返す秒・所要時間は FE が表示前に丸める。**テストが整数固定値しか通さないと露見しない（RV-027 P2-3）。
- [LN-036] **busy を親フォーム全体へ伝播させるときは、解除経路が画面内に必ずあることを確認する**（RV-027 P2-4 の行き止まり）。
  可変状態（進行中 Promise・ロック）は `useMemo` でなく `useRef` に持つ（P3-1）。

- [LN-037] **「行き止まり状態」を作る UI は、解除操作をネットワーク非依存のローカルリセットとして置き、リセット後の再操作がサーバー判定（409 等）に
  落ちることまでテストで固定する**（T-204 `resetState`）。派生表示（作成後通知）は「直前の操作」でなく**対象 run の id に紐付けて**保持する。

- [LN-038] **commit 前に `git diff --cached --stat` を見る。**Codex が `git mv` した rename は index に入るため、orchestrator が docs だけを `git add` して commit しても
  混入する（`5e132f1` に C-2 の rename 3 件が入った）。並行セッションがある間は、commit 直前に index の内容を必ず確認する。

- [LN-039] **テストを決定的にするための環境変数の中和は、守りたい故障モードを消していないか確認する。**`MAKEFLAGS=""` は決定性を得た代わりに
  `.NOTPARALLEL:` の回帰ガードを失った。中和でなく固定（`-j8` を明示）が正解（RV-029 P2-1）。

- [LN-040] **判断役を差し替えるときは「ツール実行の権威」を 1 箇所に固定する。**SDK handler を実行経路にせず runner の `ToolExecutor.call` だけが DB・トレースに書く形にすると、
  記録の一回性と hook の必通過が構造で保証される（T-205）。
- [LN-041] **外部 SDK の既定値に安全性を預けない。**`setting_sources` のように未指定で外部ツールの既定（プロジェクト設定・CLAUDE.md 読込）に委ねられる項目は、送信範囲の承認（D05）を
  実質的に外へ出す。**明示的に空を渡す**（RV-030 P2-3）。
- [LN-042] **タイムアウトは「何と何の間を測るか」を設計書に書き、判断役を替えたら再確認する。**無応答時計がメッセージ間からツール呼出し間へ静かに変わった（RV-030 P2-2）。
- [LN-043] **外部 SDK のデータクラスのフィールド名は実クラスを import して確認するテストを置く**（`ResultMessage.terminal_reason` が無ければ `AttributeError` → `model_error` に化けて
  `max_turns` を取りこぼす。バージョン差で静かに壊れる）。

- [LN-044] **Claude Code CLI は MCP ツールを遅延ロードする（`ToolSearch` メタツール）。**allowed_tools を業務ツールだけに絞ると、モデルは定義を取得できず
  1 度もツールを呼べない。SDK 完全モックの単体テストではこの種の「ランタイムの前提」は検出できない → 実モデルの最初の 1 本は必ず「ツールが 1 回でも呼ばれたか」を見る。
  `permission_denials` の実キーは `tool_name` / `tool_use_id` / `tool_input`（TODO-020 ② 解消）。CLI は max_turns 終了後に exit 1 を返し `ProcessError` になる
  （`model_error` に丸められるので `max_turns` の写しが先に効くか要確認）。

- [LN-045] **実モデルの 1 ターンは数十秒〜数分の「メッセージなし」を含む。**生存信号を SDK メッセージ単位にすると、長い生成中に無応答判定が誤発火する
  （run 4: 4 ページ読取後 63 秒で停止）。`include_partial_messages=True` で StreamEvent を生存信号にする。さらに**期限発火時のキャンセルが SDK の anyio cancel scope
  から worker へ漏れ、`inactivity_timeout` が `process_interrupted` に化け turns も 0 に上書き**された。停止理由の分類はモックでは壊れず実機で壊れた → 実機の停止系
  （無応答を意図的に起こす）を評価シナリオに 1 本持つ。

- [LN-046] **実モデルの初回評価は「型の欠陥」を 1 本ずつ剥がす反復になる。**run 3〜8 で ①ランタイムのメタツール拒否 ②生存信号の粒度 ③ツールエラー即中断
  ④ターン予算と 1 件ずつの登録、が順に露出した。いずれも SDK 完全モックの単体テストでは検出不能。**実モデルの評価ループ（起動 → トレース → 1 欠陥 → 短ラウンド → 再実行）を
  Codex 常駐ループと組み合わせると 1 欠陥あたり約 30 分**で回る。評価スクリプト（scratchpad `real-eval-ae01.sh`）は Phase 5 の skill 化候補。

- [LN-047] **設計書の数値は、テストが設計書ファイルから読んで照合する**（`MAX_TURNS` を agent-plan 本文から正規表現で読み取り `definition` と比較）。「片方だけ変えない」を
  初めて機械的に担保した。閾値・モデル ID など「写し」の値はこの形に寄せる。
- [LN-048] **ターン数はツールの粒度で決まる。**1 項目 1 呼出しの API のままモデルを走らせると根拠 127 件＝127 ターンで上限に当たる。配列一括は性能最適化ではなく
  停止条件を成立させるための設計。閾値を上げる前に呼出し粒度を疑う。
- [LN-049] **「換算」と「表記の正規化」は単位が変わるかで線を引く。**同一単位内の厳密・可逆な変換（分数→小数）は原表記を保持する限り D03 の禁止対象ではない。
  単位が変わったらどれだけ正確でも承認が要る。評価スクリプトに「`*_unit` が原表記の単位と異なれば換算」の機械チェックを置く（TODO-023）。

- [LN-050] **`finally` の後始末で CancelledError を再送出すると、進行中の例外・戻り値を上書きする。**runner の後始末（SDK close）由来のキャンセルが DraftError を消し、
  worker が「キャンセル」で終わり、jobs が `process_interrupted` と誤分類した（run 4/6/9）。規則: 後始末由来のキャンセルは**決して**実行結果にしない。
  進行中の例外があれば優先し、無ければ明示の停止理由を返す。jobs は「worker task が cancelled」と「自分が cancelled」を区別する。
- [LN-051] **例外を変換する try の範囲は「DB に触る最初の呼出し」から。**`begin_step` を try の外に置いたため、ロック取得や `require` の失敗がツール結果にならず worker を落とした。
  ツール実行の入口関数は、入った瞬間から出るまで全経路を `ToolReply` に写す。

- [LN-052] **語彙（Literal / CHECK IN）は 4 箇所一致だけでなく「対応先モデルのフィールドに実在するか」を実行時に照合する**（T-301: 16/16・9/9）。綴り違い・存在しない項目の混入を一撃で検出。
- [LN-053] **表レベル不変条件（値と状態が対）は項目ごとの分岐でなく、既存の入力スキーマで適用後スナップショットを再検証する形に畳む**（T-301 `record_service` が `ItemInput` で再検証）。

- [LN-054] **異常の分類は「起きた場所」でなく「最初に捕まえた場所」が決める。**各層が自分の責任範囲の失敗を固定コードに変換して返さない限り、最外層の分類が
  すべてを上書きする。後始末（cleanup）は結果を決める権利を持たない（`result_ready`・`sys.exc_info()` で確定済みを判定し、外から来たキャンセルだけ通す）。
  実評価で見つけた不具合は、修正と同時に「直したバグの逆」を変異ケースにする（`boundary_begin_outside_try`）。

- [LN-055] **アプリ起動時の「回収」処理は、別プロセスが生きている可能性を前提に書く。**「起動前に worker は生きていない」という単一プロセスの仮定は、テストの
  `TestClient(app)` が同じ DB に対して起動した瞬間に崩れる。回収は期限（外側タイムアウト）で判定し、lifespan の DB アクセスもテストの override を通す。
  「間欠的な失敗」は、まず**同時刻に何が動いていたか**（pytest・別サーバ）を疑う（LN-027 の一般化）。

- [LN-056] **同じ判断を 2 箇所で書くとしきい値は必ずズレる。**`recover_expired`（`limit+16`）と `recover_interrupted`（`limit`）は「回収してよいか」という同一判断。
  述語 1 つ（`is_recoverable(run, now)`）に集約する。能力を削る変更は「その能力が何を救っていたか」を確認する（全 run JSONL 再構築は書込障害からの唯一の自動復旧だった）。

- [LN-057] **共有ハンドラ（route class・例外変換）を変更するスライスは「影響が及ぶ集合 × 挙動が変わる集合」の交差を計算して handoff に書く**（T-302: 交差 1 件）。
  応答 DTO のホワイトリストは、存在しないダミー列名を禁止集合に混ぜて assert すると「絞っていること」自体を検査できる。

- [LN-058] **FE の共有 fixture を `__tests__/` に置くと jest が suite として収集して「テスト 0 件」で落ちる。**`features/*/testing/` か `shared/testing/` に置く（CV-021 の FE 版）。
  i18next の `count` は複数形の予約キーなので件数の補間名に使わない。

- [LN-059] **「空であるべき集合」は `== set()` で明示的に assert する。**件数 0 の assert を省くと検出ロジックを丸ごと無効化する変異が素通りする（T-401 の unmapped / orphan 変異）。

- [LN-060] **チェックを足すと設定の腐敗が見つかる。**prettier --check をゲートに載せた途端、未整形 126 ファイルと orval の読まれないオプション（`prettier: true`）が芋づるで露見した。
  「人の規律」に頼っていた領域にゲートを足すときは、周辺設定の不備も同時に出ることを見込む。


- [LN-061] **契約に必須フィールドを 1 つ足すと、unit・integration・FE fixture の 4 箇所が同時に RED になる。**これは契約が効いている証拠であり、
  optional に弱めて回避しない（T-603 の `elapsedSec`。T-502 の `latestSendoff` と同型の事象）。
- [LN-062] **画面に読取を 1 本足すと、実 fetch をスタブする結合テストが「Unexpected request」で落ちる。**スタブの網羅は画面の読取一覧と対応させる
  （T-603 で `approval-refresh.test.tsx` が `/versions/9/exports` で落ちた）。
- [LN-063] **jest の既定 5000ms に依存しない。**単独では 2 秒台のテストが全体並列実行では 13 秒かかって落ちる。重い結合コンポーネントテストは明示 timeout を持たせる
  （T-602 レビューの P3 指摘 → T-603 で `approval-refresh.test.tsx` に 30000 を付与）。
- [LN-064] **同一ツリーでスライスを並行させると、レビュアーが `make check` を再現できない。**実行のたびにテスト収集対象が変わる。
  memory-protocol の「転記中は他スライスを走らせない」は**レビュー中も同じ**（RV-045 P2-1 の昇格候補）。


- [LN-065] **テスト用 QueryClient の既定が、本番コードのオプションを覆い隠す。**`createTestQueryClient` が `mutations.retry:false` を既定にしているため、
  `useMutation({retry:false})` を消しても検知できなかった（RV-046 P2-6）。既定と重なるオプションは、**既定を変えたクライアント**で検証する。
- [LN-066] **同じ操作のボタンを画面に 2 つ置くと、コンポーネント内 state だけでは二重実行を防げない。**`isPending` はインスタンスごとに別物。
  対象 ID をキーにした `mutationKey` ＋ `useIsMutating` で**進行中を共有**する（T-603 の出力ボタン）。
- [LN-067] **レビュー指摘は現物で裏を取ってから直す。**RV-046 P2-3「既存テストが弱まった」は `git diff` で見ると T-503 由来で、T-603 の差分ではなかった。
  指摘どおりに「直す」と、無関係な既存契約を壊す。


- [LN-068] **hooks を丸ごと mock した component テストは、hooks 側の防御機構の検査にならない。**`mutationKey` / `useIsMutating` / `retry` は mock に潰され、外しても green のまま通る。
  防御機構を入れたら「mock を外した配線テスト」を 1 本添え、**変異で落ちること**まで確認する（RV-046 P2-6 と RV-047 P2 で 2 回連続 → §2 昇格候補）。
- [LN-069] **i18n にキーを足したら使用箇所も同時に固定する。**未使用キー（dead key）が 3 回出た。未使用キー検出は Env フェーズ（`/r2b-env-sprint3`）の候補。
- [LN-070] 実モデル実行の失敗原因は、トレース（引数ハッシュのみ）では追えない。SDK のセッション記録 `~/.claude/projects/-tmp-agent-run-<id>/*.jsonl` に、実際の tool_use 引数とツールの応答が残る（F-1 はここから特定した）。F-1 以降、検証失敗の path と type はトレースの observation.errors に残る
- [LN-071] ツールの JSON Schema は LLM への契約そのもの。バリデータが拒否する形（例: Decimal に対する JSON number）を Schema が許すと、LLM は何度でも踏む。state と値の規則は両方向で書く（F-1・RV-049）
- [LN-072] **「画面に出ない」Fail の多くは、生成側と表示側の語彙のずれだった。**エージェントは検証器が要求する `qty`/`od` で根拠を登録し、ドロワーは列名 `qty_value` で探していた（TEST-04 #3・TEST-05 #2）。
  データは正しく DB にあるので API テストもツールテストも緑のまま。**生成側の語彙の SSOT（ここでは `draft_validation.py`）を表示側がどこで写しているか**を、スライスをまたいで照合する。
- [LN-073] **jsdom はレイアウトを計算しないので「列が画面外」は単体テストで検出できない。**原因は親から継承した `white-space: nowrap` で、Playwright で `getComputedStyle` を取って初めて分かった。
  表を足す／狭いパネルに置く UI は、実画面のスクリーンショット（scratchpad の `shot.py`：キャッシュ済み chromium を `executable_path` 指定）で確認する。
- [LN-074] **LLM の出力の「揃い方」はプロンプトの規則だけでは安定しない。**同じ S10 で run 28 は期限の案件レベル確認事項を立て、run 36 は立てなかった。設計書に既に「〜なら確認事項が立つ」と書かれている完了要件は、`validate_draft` の違反種別にして自己修復ループに乗せる（F-4 `missing_question`）。
- [LN-075] **`--no-session-persistence` は SDK のストリーム入力モードでも効く**（`--print` 限定と help にあるが実測で保存 0）。SDK は `extra_args` で CLI フラグを渡せる。以後、失敗解析に SDK 会話ログ（LN-070）は使えない → トレースの observation を厚くする方向で補う。

- [LN-076] **「記録できてしまう」「戻らない」Fail の一部は、拒否は効いていて拒否の表示が見えていなかった。**記録者名が空の拒否を地の文＋データ不整合向けの「再取得」で出し、直上には前回の記録行が残っていたため、研修者は「記録された／取消されない」と読んだ（TEST-11 #4・TEST-14 #1）。DB の記録（取消・状態遷移の有無）を先に見て、「処理の不具合」か「表示の不具合」かを切り分ける。入力の拒否は欄自体の `error`＋`helperText`（TextField に id）で示し、入力で解除する。同種がもう一度出たら §2 へ昇格。
- [LN-077] 画面で引き継ぎ警告を出すときの「記録あり」の条件は、サーバーの起動拒否（`run_repository._has_records`）と #22 carryOver の定義の両方と突き合わせる（F-10 は一致）。起動 409 後の定型文だけでは件数が出ず、03-spec SCR-02 を満たさなかった。
- [LN-078] **研修者の Fail 判定は、判定に使った版が修正より前か後かを先に確かめる。**TEST-05 #6 の Fail は F-4 以前に作った版（case 25 / v29・1行）での判定で、修正後の再評価（case 34 / v37）は CFL-2 の2行だった。ただし再確認の過程で、画面が CFL 行を「択一」と表示し ALT/CFL の区別（04-db group_code）を失っている別の欠陥が見つかった（F-11）。区分を足したら、状態列・タグ・絞り込み・件数・出力・モックまで同じ語彙の使われ方を横断検索してそろえる。
- [LN-079] 利用者向け表示から内部 ID を消すときは、**特定に必要な情報（ファイル名等）への置換とセット**で設計する。消すだけだと情報が落ちる（RV-054 P2-2）。
- [LN-080] composition root（`app/api/dependencies.py`）を通すテストは `settings.AGENT_MODE` 等の実行モードを明示固定する。`backend/.env` が `AGENT_MODE=claude` のとき `test_definition_defaults_reach_reserved_run` が落ちていた（F-12 で固定）。
- [LN-081] 固定幅（左ナビ 232px）の文言は jsdom で検証できない。「字数×サイズ×(1+letterSpacing)＋付随要素」で見積もり、`nowrap` と実ブラウザのスクリーンショット（`~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome --headless=new --screenshot`）で確認する。

- [LN-082] 表の特定列だけにスタイルを当てるときは `:first-of-type`・`:nth-child` を使わず専用 class で指し、「どのセルに有り・無いか」を DOM テストする。MUI の `TableCell component="th" scope="row"` が行の途中に `th` を入れるため（RV-055 P1）。位置系の不具合は横スクロールした状態もスクリーンショットで確認する（`scratchpad` の playwright スクリプトで `scrollLeft` を設定）。

- [LN-083] 3 状態（読込中・エラー・空）の UI テストは状態ごとに別々に検証する。テスト名が検証内容より広いと欠けに気づけない（RV-056 P2）。
- [LN-084] 2026-09-25、同じ PC で他の Claude セッションが動いていると FE の既存テスト（ItemList の 1.5〜3.4 秒級）が jest 既定 5 秒を超えて `make check-fe` が時間切れで落ちることがある。F-12 時点のコミットでも同じ所要（53 秒/スイート）で、コード起因ではない。単独実行・`npx jest --maxWorkers=2` では全件緑。

## 6. 未解決 / BLOCKED / TODO

- [TODO-008]（解消: AD-013 で暫定案どおり決定）T-103 SCR-01 の設計判断2件: ①05-api-ipo #1 は「表示状態・送付可否つき」だが
  実装済み `CaseListItem` は `progressStatus` のみ。暫定: T-103 は両列「—」＋注記、G3（T-302）で #1 拡張。
  ②03-spec SCR-01「案件を開く→SCR-03」は未実装。暫定: 「投入画面へ」のみ表示し `openButton` は G3 で追加。
  確定したら orchestrator が 03-spec / 05-api-ipo に書き戻す（RV-019 P1-4 / P1-5）。
- [TODO-009] **T-203 の記録のみ P3（RV-020/022）**: ①read 系ツール名集合を `agent_types.py` に1箇所定義し `hooks.py` と `tool_stage()` が参照
  ②`permissionDecisionReason` は説明文にしコードは別キー（実モデル接続時に必須）③進捗更新ごとの完全 `snapshot()` を軽量化（S05 実測時に N06 と突き合わせ）
  ④`test_agent_guardrails` の URL 拒否テストを `search_documents.query` に寄せる ⑤既定ダミーでは同一違反3回の自己修復ループが未稼働
  （実モデル接続時に方針側で実装）⑥`read_email` の `email:*` 全走査は「返した」と「解釈した」を区別しない。改修スライスとして積む時期は T-204 後。
- [TODO-010]（解消: C-2 RV-029 で全項目クローズ）**T-201 の記録のみ P3（RV-023）**: Makefile に `.NOTPARALLEL:`（`-j` 継承でゲート順序が崩れる）/ `INDEX_TEST_URL` を target-specific export に /
  `export` 行を `TEST_DB :=` の後ろへ / `check_t201_postgres.py` を make 外から叩いたときの KeyError を案内メッセージに / 同一索引の定義が
  t201_artifacts と add_run_step_locator_index の2リビジョンにある事実（意図的・LN-025）。C-1 と同時に整理。
- [TODO-011] **T-103 の記録のみ P3（RV-024）**: ①`shared/api/unwrap.ts` の `E_UNEXPECTED_RESPONSE` は 05-api-ipo §6 のコード一覧外（クライアント合成コード）。
  05 §6 に「クライアント合成コード」節を設けるか接頭辞で区別する（orchestrator 判断）②SCR-02 のファイル選択が素の `<input type="file">` で
  ブラウザ既定の英語 UI が出る → T-204 の SCR-02 改修と同時に `Button component="label"` 化。
- [TODO-012]（①〜⑥⑧解消: C-2 RV-029。⑦は残）**C-1 の記録のみ P3（RV-026）**: ①`scripts/check_t202_postgres.py` → `check_run_metadata.py`、`tests/integration/test_api_path_separation_t102.py` →
  `..._live.py`（CV-017 残存）②SQLite `@compiles` と共有 metadata 書換を `tests/fixtures/sqlite_support.py` へ切り出しコメント明示 ③conftest の
  `TestConnection` / `test_connection` を `SyncConnectionAdapter` / `_connection` に ④integration→unit のテスト間 import を `tests/fixtures/` のビルダへ（CV-021）
  ⑤`test_actual_application_path_separation_under_isolated_settings` の改名と `runpy` 二重実行の解消 ⑥seeded の `case_code="T202"` → `"SEED-CASE"`
  ⑦`tests/t201` `tests/t202` の空 dir（`__pycache__` のみ・git 管理外）のローカル削除 ⑧`features/agent-runs/components/__tests__/IntakeRecovery.test.tsx` を
  `features/documents/` 側か FE 統合テスト置き場へ（RV-028 P3-6）。次の整理 chore（C-2）で。
- [TODO-013] **起動結果不明（POST 応答喪失）からの runId 再接続は API 不足で実現不能**（`docs/t204-handoff.md` §2）。案件に属する実行一覧
  （例 `GET /cases/{caseId}/agent-runs`）が無い。T-204 は「一覧を再読み込みしてください」で止める。API 追加は 05-api-ipo に積んでから。
- [TODO-014] 数量 TBA の確認事項 `questions.category` が `unknown`（G2 ミニ評価）。04-db.md の語彙と照合し適切な区分があれば `local_policy.py` で割り当てる。
- [TODO-015]（解消: AD-016 で D05 承認・T-205 を起票）**Phase 3 の本評価（sample-01〜10・AE01〜AE07）は実モデル接続（D05 承認）が前提。**ローカルダミーは 1 行明細形式のみ対応。
  D05 の承認（送信先・送信範囲・保存条件）を研修者が判断するまで、Phase 3 は「型の確認」（ミニ評価）に留まる。**研修者判断待ち**。
- [TODO-016]（解消: 2026-09-12 23:20 研修者が有効化。Claude は行が非コメント・`sk-ant-` 接頭辞であることのみ確認、値は未表示）**`ANTHROPIC_API_KEY` を `backend/.env` に投入する。**
  投入後に Claude が sample-06（AE01）を 1 本通す（AD-016）。
- [TODO-017] **C-2 の記録のみ P3（RV-029）**: `test_run_endpoints_are_in_ui_only_route_contract` を `tests/unit/` へ / `app/api/common/endpoints_reference.py:6` docstring の
  旧テスト名 → `test_api_path_separation_live.py` / ログの絶対パス。TODO-009 と同じ「`backend/app` を触る整理」ラウンドで。
- [TODO-018] **要求納期・納地（`items.due_raw`/`place_raw`）を人が訂正できるか**（研修者判断）。03-spec SCR-04 は編集可、04-db 原則4 は `*_raw` 不変。
  初版は編集不可（AD-018）。編集可にするなら `due`/`place` の値列（非 raw）を items に足す設計変更が要る。
- [TODO-019]（転記済み: AD-028 ⑨・`docs/t501-instructions.md` §0）**T-501 の指示書に転記**: `review_checked` 版への訂正は `review_checked→staff_checked` の状態イベントを同一トランザクションで積む（05:438 / 04-db:775）。
  T-301 では未実装（G3 で到達不能。t301-instructions §0 ⑤）。
- [TODO-035] **T-403 の記録のみ P3（RV-043）**: ①`versions.inventory.{notice,requiredNote,undoNote}` の文体を敬体に ②`InventoryScopePanel` 同名資料の `aria-label` に識別子・`key` を documentId に
  ③「照合する範囲」を #4 資料一覧で補完するか（要素 0 の資料）④`testing/fixtures.ts:77` のインライン `import()` 型 ⑤`inventory-components.test.tsx:302` を `it(`＋日本語名に（RV-044）。①②④⑤は C-3（FE 分）、③は G5 以降の判断材料。
- [TODO-037] **05 #22「生成所要」の API 露出が未実装**（AD-029 ⑭。DB 上は `agent_runs.version_id` UNIQUE FK で結線済み・T-601 は案件情報シートに `elapsed_sec` を書く）。#22/#23 への露出は G6 T-603 で。
- [TODO-042] **T-602 / T-603 の指示書が未作成**（AD-032 で Codex が §0c の手順で書く）。T-602 の論点: #38 のバイナリ応答（AD-030 ㉑ 確定済み）・orval のバイナリ扱い・`route_contract.py` への
  `exports`/`evidence` 登録要否・`E_VERSION_NOT_FINALIZED` の `errors.py` 追加。T-603 の論点: blob 保存の導線・版の履歴パネル（#39 `integrity`）・`VersionListItem.elapsedSec`（AD-029 ⑭）。
- [TODO-041] **SCR-04（根拠詳細）の「上司の差し戻しコメント」表示が未実装**（03-spec SCR-04・AD-031 ③）。`EvidenceDrawer` に #28 由来の `bounceComments` prop を渡す小改修。G5 完了後の改修スライス。
- [TODO-040] **SCR-01 の「差し戻しあり」補足**（03-spec SCR-01）は #1 に `bounced` が無く未実装（AD-031 ㉔）。#1 拡張は G6 か C-3 で。
- [TODO-039] **SCR-06 索引の「変更採用（P.S./Rev.）」タグ**は #24/#26 に判別項目が無く初版では出さない（AD-031 ⑯）。`evidences.change_reason` を行単位に集約して #24 に `hasAdoptedChange` を足すか、
  索引から外すかは研修者判断。
- [TODO-038] **`exports` に記録者列（`exported_by`）を持つか**（研修者判断・AD-030 ⑥）。04-db §3.5 は無し。E 層は写しの保全記録で D 層の「人の記録」ではないため初版は持たないが、
  06 の採点手順で「誰が初回出力を保全したか」が要るなら 04-db を改定して T-601 改修スライスへ。
- [TODO-036] **TODO-027 ② の式**（`field_error_codes` × 非 400 == {E_FIELD_NOT_EDITABLE}）は T-502 で `E_STATE_ROLLBACK_FORBIDDEN`（422）が加わり 2 要素になる。C-3 実装時に式を更新（AD-029 ⑩）。
- [TODO-034] **`review_checked` 版で undo（訂正取消）・確認・判断をしても状態を `staff_checked` へ戻さない**（AD-028 ⑨。設計書は「訂正」のみ）。undo は表示値が変わるため
  戻すべきかは設計判断（研修者）。戻すなら 05 3.6 注記と 04-db `version_state_events` 注記を「訂正・取消」に改定して T-501 改修スライスへ。
- [TODO-020] **T-205 の記録のみ P3（RV-031）**: ①拒否記録を PreToolUse deny 時点に寄せて時系列を揃える ②（解消: キーは tool_name/tool_use_id/tool_input）
  ③`cwd` テストを「リポジトリルート配下でない」「実行後に削除済み」の assert に ④`bounded()` の heartbeat 分岐を stream 専用ラッパへ。実評価の観察結果と合わせて次ラウンド。
- [TODO-021]（**真因確定・AD-023 / L-8**: 統合テストの lifespan `recover_interrupted` が開発 DB の実行中 run を殺していた。L-7 の分類崩れも別途修正済み）**run 4/6/9 の `process_interrupted` 化**: `begin_step` の DraftError が try 外で漏れ、runner `finally` の SDK 後始末 CancelledError が
  進行中例外を上書きし、jobs が worker のキャンセルを自分のキャンセルと誤読（`docs/evaluations/g2-real-model-ae01-2026-09-13.md` AE03 試行 1）。旧記述:（61 秒で停止。run 7 は 201 秒の間隔でも停止せず）。L-6 で無応答発火時の診断メタデータ（直近の生存信号からの
  秒数・受信数）を `job_interrupted` に残し、次の再発で「生存信号が来なかった」か「分類が崩れた」かを切り分ける。診断サーバ: scratchpad `diag_server.py`（jobs._execute をラップ）。
- [TODO-022] **Phase 3 判定の論点 2 件（研修者確認）**: ①外径 `13-3/8″` → `od_value=13.375 in` の分数→小数正規化は D03（換算禁止）に抵触するか。単位不変なので
  orchestrator は「表記の正規化」と判断。06 の採点式（数量は厳密一致・寸法は？）と突き合わせて確定する ②N06「初回案 10 分」に対し run 8 は 631 秒。思考時間が大半で
  ターン数は 14。許容か、モデル/プロンプトで詰めるか（D06 仮値の見直し材料）。
- [TODO-028] **実モデルのインベントリ status の使い方をプロンプトで是正**: run 8 は脚注 *1〜*3 を `split`、注記を `unmapped` にした（AE01 期待「除外 4・対応なし 0」と構造集計が
  ずれる）。脚注・注記は `excluded`＋basis（複数行に関わる根拠は excerpt に）へ寄せる指示を `SYSTEM_PROMPT` と `record_source_inventory` の description に（T-205 追補 L-9）。
- [TODO-029] **`inventory_links` に `version_id`・複合 FK `(version_id, item_id)` が無い**（04-db:670-681）。版外 item への link は書込時検査のみ。複合 FK 追加は 04-db 変更＝設計判断（研修者）。
- [TODO-033] **T-402 の記録のみ P3（RV-042）**: ①`endpoints/inventory.py:18` の `from_attributes` 再帰依存を 1 行コメント ②handoff に「次スライスへ渡す契約」節を
  置く運用（CODEX-INSTRUCTIONS §6 に 1 行）。③TODO-027 ① の basename 重複は C-3。
- [TODO-032] **405（同パス異メソッド）の本文が Starlette 既定 `{"detail": …}` で 05 0.2 の `{code,message,details}` 形でない。**`main.py` に `HTTPException` ハンドラを足すか許容するか（共有ファイル・C-3 で）。
- [TODO-031] **T-401 の記録のみ P3（RV-040）**: ⑤domain `EntryView.position/excerpt` を DB NOT NULL に合わせ `str` に（AD-026 ④）。 ①不明 entry link のとき `has_source=bool(source_entries)` に揃える ②版外 link が split と inconsistent の両方に入る意図をコメント
  ③`InventoryService.reconcile` とモジュール関数 `reconcile` の同名（`reconcile_inventory` に改名）④T-402 の DTO 注記「`inconsistentEntryIds` は entries の部分集合とは限らない」。C-3 で。
- [TODO-030] **T-303 の記録のみ P3（RV-039）**: ①`groupCode`+`candidateLabel` の区切り ②原表記 blockquote に項目名 ③i18next `count` → 非予約名 ④判断 3 列の見出しとセルの対応
  ⑤ドロワー開時 contained≤1 の assert ⑥キーワード検索の対象を表示値に限定・日時の書式（G5 で決める）⑦prettier の版固定（`~` or 厳密）⑧`fe-lint` の glob が
  `generated/` を含む → 落ちたら `npm run orval` 再実行、を Makefile コメントに（RV-041）。C-3（FE 分）で。
- [TODO-027] **T-302 の記録のみ P3（RV-036）**: ①`tests/unit/test_api_path_separation_live.py` → `test_ui_route_presence.py` に改名（integration 側と basename 重複）
  ②`test_single_source_of_truth.py` に「`field_error_codes` 全コード × 表の非 400 エントリの交差 == {E_FIELD_NOT_EDITABLE}」の検査 ③`VersionCounts` は明示コピー
  ④`record_response` の属性名一致前提を docstring に ⑤`Item.__table__.columns` と `ItemCurrentResponse` の差分 = 意図的除外リストの検査 ⑥`definition.py` の再公開 import にコメント ⑦`record_repository` の関数内 import をトップへ
  ⑧`rowMatch` dict 構築に部分 UNIQUE 前提のコメント（RV-038）。C-3 で。
- [TODO-026] **L-8 の記録のみ P3（RV-035）**: ①`trace_write_failed` の JSONL を DB の trace_event から再構築する手動手順 or `scripts/rebuild_trace.py`（Env フェーズの素材）
  ②`limits.outerTimeoutS` 不正の running run はどの回収にも掛からない → ログ 1 行（run_id）。
- [TODO-023] **T-205 L-5/L-6 の記録のみ P3（RV-032）**: ①`check_agent_mutations.py` に L-5 の 4 変異（エラー継続を 1 回停止に戻す / 成功時リセット除去 / 項目別情報の除去 /
  input 値の混入）と L-6 の「配列を単数へ戻す」を取り込み `make agent-mutations` 一本で再現 ②評価スクリプトに「`od_unit`/`weight_unit` 等が原表記の単位と異なれば換算」
  の機械チェック ③03-spec SCR-03/04・出力で寸法は原表記を主・数値を従とする方針の確認 ④大バッチ×恒常重複（`E_EVIDENCE_DUPLICATE`）の部分成功可否は再発時に設計判断。
  ⑤04-db:940 の observation.code 一覧に `E_INTERNAL`、:941 に `worker_failed`（worker の例外・キャンセル）/ `process_interrupted`（ジョブ境界自身の中断）の書き分け（RV-034 P3）。
  TODO-009 / TODO-017 / TODO-020 と合わせて C-3（`backend/app` を触る整理）で。
- [TODO-024] **`item_ends`（両端仕様）が #24 の応答に無い。**SCR-04 で必要なら T-303 前に T-301 側へ取得追加（t302-instructions §0 ⑨）。
- [TODO-025] **T-301 の記録のみ P3（RV-033）**: ①`range_class` と `length_value/unit` が `length_state` を共有 → SCR-04 の UI 文言か 04-db の状態列分割（研修者判断） ②`_undo` の
  4xx 順序（状態→入力）を 05 §6 に一言 ③`apply_edits` の docstring に expire 前提 ④型エイリアス `Recorder` → `Nonblank` ⑤到達しない `require` にコメント。C-3 で。
- [TODO-005]（解消: 05 0.2 に「422 も code 付き」を明文化・AD-022）
- [TODO-001] D02（入力上限）は AD-003 の**仮値**。初版受入（X09 の上限試験）の前に研修者が実値を確定する。
  **確定時は `backend/app/core/config.py` と `frontend/src/shared/i18n/ja.json` の上限注記の両方を直す**（RV-024 P2-2。API が上限を返さないため画面側に複製がある）。
- [TODO-002] **eml には `document_pages` が無い**ため、04-db.md の完了条件の機械判定
  （`document_pages` − `document_issues` を `(document_id, locator)` で差し引く）が eml に適用できない。
  `email_parts` の `part_role`/`seq` 単位で判定するのか、設計側の方針を **T-201（完了条件の機械判定）の前に**決める。
- [AD-010 相当・2026-09-12 研修者決定] **memory.md の編集者は Claude メインセッションのみ。Codex は読むだけ**で、修正結果は `docs/t{ID}-handoff.md` に書き、Claude が転記する（指示書: `docs/reviews/CODEX-INSTRUCTIONS.md`）。TODO-004 はこれで解消。
- [TODO-004] **別セッションが T-201 を並行実装している**（`backend/tests/t201/`・`app/services/draft_*`・
  `alembic/versions/t201_*`）。memory §3 のバックログと二重進行になっており、memory の編集者を1つに
  限る取り決めとも衝突する。**どちらが T-201 を持つか研修者が決める必要がある**（2026-09-12 時点で未解決）。
- [TODO-006]（解消: T-203 で hook を呼出し境界に必須化。RV-020 で確認）**ガードレールが未接続**。`app/agent/hooks.py` は `tests/unit/test_agent_guardrails.py`
  からしか呼ばれておらず、`app/agent/runner.py` / `trace.py` はどこからも import されていない
  （新 `RunTraceStore` と2系統が同居）。現状はループ自体が `local_worker_unavailable` で即 failed
  するため実害はないが、**T-203 で `RunDispatcher` に差し込むまで「hooks で強制」は成立していない**
  （agent-development.md §5）。T-203 の着手前に「旧 runner/trace/hooks と新系統のどちらを正にするか」
  を決める（設計課題は `agent-plan.md` 末尾「T-202 ジョブ境界の補足（RV-015）」に記載済み）。
- [TODO-007] `email_parts` に `UNIQUE(document_id, part_role, seq)` が無いまま、
  `email:{part_role}:{seq}` を完了条件の走査判定の一意キーとして使っている（04-db.md:944 の残件）。
  重複パーツが入ると走査済み集合が壊れる。**T-203 着手前に制約を足すか、判定側で重複を弾く**。
- [TODO-005]（上記で解消）05-api-ipo 0.2 に「エラーコード不要の 422（標準バリデーション扱い）」の指針が無い。
  T-102 では `fromSeq > toSeq` を 422（コードなし）とした。同種の入力検証が増えるなら明文化する。
- [TODO-003] `document_issues.issue_type` の語彙（特に `reference_missing` / `not_scanned`）の
  意味づけが 04-db.md に無い。T-101 では「付随情報の欠落（引用元の日付が解釈できない等）」に
  `reference_missing` を割り当てた。設計書に用語定義を追記するとよい。

- [T-201 引き継ぎ 2026-09-12] TODO-004の別セッションは本タスク（ユーザーがT-201の担当を指示し再開を指示済み）。T-201担当を継続。TODO-002/003の判定方針は04-db.md §3.3「T-201補足」に明文化・実装済み。77件の独立テストとPostgreSQL制約15件はPASS。全体回帰はユーザーの明示指示により保留。詳細は `docs/t201-handoff.md`。DONEにはしていない。

- [T-202 着手 2026-09-12] ユーザーがT-201の全体回帰保留を維持したままT-202への着手を明示指示。依存DONEの通常ルールに対する今回の指示としてT-202を開始。全体回帰・既存設定読込・別テストDB初期化は保留を継続。G1 FEの編集中ファイルを保全する。

- [T-202 引き継ぎ 2026-09-12] API #12-21（#20共通）と永続ジョブ管理を実装、独立レビュー済。T-203未接続のローカルworkerはagent_implementation_pendingとしてfailed終端する。通常設定読込・実DBへのmigration適用・現行規則設定・実案件起動・コミット/プッシュは未実施。全体回帰とG1側型エラーは保留。

- [TODO-043] RV-045（T-602）P3 3 件は記録のみ: ①非空 body の全量バッファ ②射影イディオムの二重化 ③`Content-Disposition` の ASCII 安全性の境界テスト不足。C-3 でまとめて判断する。

- [TODO-044] **研修者判断**: 03-spec:237「未生成は出力ボタンを無効化し版の履歴に『未生成。…』」と、T-503 の既存契約「版一覧に現在版が無い場合は**取得失敗**として操作を出さない」が両立しない
  （SCR-03 のルートは AD-024 ① で `versionId` を含むため、確定版 0 件の状態は実質 404 に畳まれる）。どちらを正とするか。T-603 は T-503 の契約を優先し表示を変えていない（RV-046 P2-2 未対応）。
- [TODO-045] RV-046 の記録のみ P3 2 件: ①`approval-refresh.test.tsx` の `timeout 30000` は遅さのマスク（原因は画面の読取本数増。LN-063 と同根）②`integrityLabelKey(integrity: string)` を生成 union 型で受ける。C-3 で判断。

- [TODO-046] RV-048 の記録のみ P3 2 件: ①`export-wiring.test.tsx` 2 本目（別版の分離）を変異で落ちる形にする ②`useExports` を `<details>` の開閉に連動させる（TODO-045 の遅さの直接原因）。C-3 で判断。

- [TODO-047] F-1 の記録のみ P3（RV-049/050）: ①trace の path に extra_forbidden の未知キー名が入り得る（伏せるか 04-db に許容と明記）②20 件で切ったことが残らない（`errorsTotal`）③UI API の `details.errors[].path` が `rows.0` から `rows.0.qtyState` 等に変わったが API テストで固定していない（code は不変）④B のテストは語句の有無だけを見ている ⑤ヒント文が単位に触れない。C-3 で判断。
- [TODO-048] **研修者判断**: 3 回規則（`REPEATED_CALL_LIMIT`）を `(ツール名, code)` の単位で数えるため、中身の違う E_REQUEST_INVALID でも 3 回で `tool_rejected` になる（agent-plan.md:243「同一ツール×同一エラーコード」どおり）。エラーの中身まで比較するかは設計変更（F-1 決定 E）。
- [TODO-049] **研修者判断**: `backend/.env` が `AGENT_MODE=claude` のままだと `test_run_regressions.py::test_definition_defaults_reach_reserved_run` が落ち、`make check` が赤になる（テストが .env に依存）。F-1 のゲートは `AGENT_MODE=local_dummy make check` で実行した。あわせて sample-10（AE02）の実モデル再評価も、外部送信の確認待ち。
- [TODO-050] RV-051 の記録のみ P3: F-5 の表レイアウトは jsdom で検証不能（スクリーンショットのみ）／`useActiveRun` hook 単体テストなし・`setRunId(current ?? activeRunId)` の既存値保持分岐が未テスト／「その他の根拠」で `end_a.od` と `end_b.od` が引用と位置でしか区別できない（CV-019 で field 名は出さない）。C-3 で判断。
- [TODO-051] **研修者判断**: TEST-04 #4 の期待値「除外4」の数え方が設計書から導けない。F-4 後の run 35/42（S06）は「明細8 → 出力11行（分割3）／対応なし0」は一致、除外は種別ごとに全要素を棚卸しして 20 件超（表題・案件情報・共通条件・見出し行・注記・脚注・提出要領・免責）。
  ②5章は「小計・合計・共通条件・変更指示・注記・脚注・署名など」全要素の棚卸しを求めており、4 件にするには「どの要素を数えるか」の定義が要る（06 は正解データ未承認）。定義が決まればプロンプトの粒度規則を合わせる。
- [TODO-052] **研修者作業**: Anthropic API のクレジット残高不足で実モデル run 40〜42（`missing_question`・`unsplit_conflict` 追加後の S10/X04/S06 確認）が `model_error` で未実施。補充後に再実行し、
  あわせて `~/.claude/projects/-tmp-agent-run-*`（F-7 以前の 28 件・資料本文を含む）と `-tmp-persist-probe-osjh4t08`（F-7 の実測で作成。削除は権限で拒否された）を削除する。記録: `docs/evaluations/scenario-fix-2026-09-24.md`。
- （解消）TODO-013 は F-6 の #14a で解消。TODO-028 は F-4 のプロンプト規則で解消（run 35/38 で脚注・注記・小計は excluded＋種別ラベル）。
- [TODO-053] **研修者確認**: TEST-13 #5（案件レベルの未解決の注記）は再現しなかった。S10 の担当者確認済み版（case 24 / v28・案件レベルの未解決 1 件）で行をクリックすると「行に紐づかない案件レベルの未解決 1 件があります」が出る。実施した案件・版を確認し、案件レベルの確認事項の無い版だった場合は、F-4 `missing_question` 入りの実モデル再評価（TODO-052）で S10 に期限の確認事項が立つかを見る。記録: `docs/evaluations/scenario-fix-2026-09-25.md`。
- [TODO-054] F-11 の残り（RV-053 P3）: ①`docs/requirements/mocks/mockup.html` の絞り込み名・changeTags・noChanges 文言・状態列・`data-tone` 正規表現に「矛盾候補」が無い（`/design-spec` で更新）②SCR-06 の表のグループ列に種別ラベルを添えるか（任意）③件数を「択一グループ」「矛盾グループ」に分けるか（API 変更を伴う・研修者判断）。あわせて TEST-05 #6 は研修者の案件 v29 が修正前の版なので、実モデルで X04 を再実行して判定し直す（TODO-052 のクレジット補充が前提）。
- [TODO-055] RV-054 の記録のみ P3: IntakePage→AgentRunPanel の `documentNames` 受け渡しの結合テストなし／BounceBanner・EditHistory・EvidenceDrawer rowMatch の JST 表示の画面テストなし／`mocks/mockup.html` に旧名称・SCR 眉・フッター・Scope 2 が残る（次の `/design-spec` で反映）。
- [TODO-056] RV-055 の記録のみ P3: `ItemTable` の class 名 `sticky` が汎用的（表内に別部品を入れるなら改名）／`StaffCheckAction.tsx` のファイル名と export（`useStaffCheck`・`StaffCheckButton`・`StaffCheckNotice`）の不一致。
- [TODO-057] RV-056 の記録のみ P3: 案件一覧の記録展開で判断・訂正・照合がどの確認事項／行かを示さない（#28 に確認事項番号が無い）／`CaseListEntry.latest_state_event: Any` の型を Protocol 化／最新判断の組み立てが 3 リポジトリに重複（次に出たら共通化して CV へ）／`useCaseRecords` の `enabled` 引数は常に true。
- [TODO-058] LN-084 の対策（jest の `testTimeout` 引き上げか `--maxWorkers` 指定を Makefile に入れるか）を研修者と決める。
