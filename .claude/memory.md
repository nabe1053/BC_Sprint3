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
| T-205 | G2 実モデル接続（`claude_policy`・AGENT_MODE 切替・D05） | agent | T-203, C-2 | DONE | 5回目 RV-032: **DONE**（L-3〜L-6 全て DONE 可・AE01 合格）。コードは T-301 と同一コミットで入れる（`_has_records` 依存） | 2026-09-13 |
| T-301 | G3 明細の現在値算出・人の記録（BE） | web | T-201 | REVIEWING | 1回目（Codex 申告 518 passed・追加 46 件・変異 10/10、確認中） | 2026-09-13 |
| T-302 | G3 参照 #23-26 / 記録 #29-31,33（API） | web | T-301 | PLANNED | - | 2026-09-11 |
| T-303 | G3 SCR-03 Item List 確認 / SCR-04 根拠詳細（FE） | web | T-302 | PLANNED | - | 2026-09-11 |
| T-401 | G4 インベントリ・対応関係・照合集計（BE） | web | T-201 | PLANNED | - | 2026-09-11 |
| T-402 | G4 照合 API #19,27（API） | web | T-401 | PLANNED | - | 2026-09-11 |
| T-403 | G4 SCR-05 網羅性照合（FE） | web | T-402 | PLANNED | - | 2026-09-11 |
| T-501 | G5 状態遷移・差し戻し・送付可否の記録（BE） | web | T-301 | PLANNED | - | 2026-09-11 |
| T-502 | G5 承認・状態 API #22,28,34-37（API） | web | T-501 | PLANNED | - | 2026-09-11 |
| T-503 | G5 SCR-06 引合書承認（FE） | web | T-502 | PLANNED | - | 2026-09-11 |
| T-601 | G6 .xlsx 5シート生成（BE） | web | T-501 | PLANNED | - | 2026-09-11 |
| T-602 | G6 出力 API #38,39,40（API） | web | T-601 | PLANNED | - | 2026-09-11 |
| T-603 | G6 出力ボタン・版の履歴（FE・SCR-03 内） | web | T-602 | PLANNED | - | 2026-09-11 |

> **実施順（AD-011）**: T-201・T-202 クローズ → C-1 → **T-203 → T-204 → ミニ評価** →
> G3（T-301〜303）・G4（T-401〜403）は並行可 → G5 → G6。
> 並行してよいのは依存が独立でファイルが重ならない組（T-301 / T-401）のみ。規則は
> `docs/reviews/CODEX-INSTRUCTIONS.md` §5。

> **実モデル評価 AE01 合格・2026-09-13（run 8）**: `AGENT_MODE=claude` / `claude-sonnet-5` で sample-06 が `completed`・11 行（択一 2 組・分割 1 組・TBA・原表記保持・代替は確認事項）・
> 631 秒・14 ターン・漏洩 0。6 回の試行で L-3〜L-6 の欠陥 4 件を潰した。記録: `docs/evaluations/g2-real-model-ae01-2026-09-13.md`。

> **G2 ミニ評価（⑤）合格・2026-09-12**: UI API 経由で実ジョブを通し、正常系 `completed`（明細 3・確認事項 2・違反 0・トレース漏洩 0・換算なし）と
> 対応範囲外 `failed/local_dummy_unsupported`（捏造なし）を確認。記録: `docs/evaluations/g2-mini-eval-2026-09-12.md`。Phase 3 本評価は D05 承認後。

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
- [TODO-019] **T-501 の指示書に転記**: `review_checked` 版への訂正は `review_checked→staff_checked` の状態イベントを同一トランザクションで積む（05:438 / 04-db:775）。
  T-301 では未実装（G3 で到達不能。t301-instructions §0 ⑤）。
- [TODO-020] **T-205 の記録のみ P3（RV-031）**: ①拒否記録を PreToolUse deny 時点に寄せて時系列を揃える ②（解消: キーは tool_name/tool_use_id/tool_input）
  ③`cwd` テストを「リポジトリルート配下でない」「実行後に削除済み」の assert に ④`bounded()` の heartbeat 分岐を stream 専用ラッパへ。実評価の観察結果と合わせて次ラウンド。
- [TODO-021]（機構特定・L-7 で修正中）**run 4/6/9 の `process_interrupted` 化**: `begin_step` の DraftError が try 外で漏れ、runner `finally` の SDK 後始末 CancelledError が
  進行中例外を上書きし、jobs が worker のキャンセルを自分のキャンセルと誤読（`docs/evaluations/g2-real-model-ae01-2026-09-13.md` AE03 試行 1）。旧記述:（61 秒で停止。run 7 は 201 秒の間隔でも停止せず）。L-6 で無応答発火時の診断メタデータ（直近の生存信号からの
  秒数・受信数）を `job_interrupted` に残し、次の再発で「生存信号が来なかった」か「分類が崩れた」かを切り分ける。診断サーバ: scratchpad `diag_server.py`（jobs._execute をラップ）。
- [TODO-022] **Phase 3 判定の論点 2 件（研修者確認）**: ①外径 `13-3/8″` → `od_value=13.375 in` の分数→小数正規化は D03（換算禁止）に抵触するか。単位不変なので
  orchestrator は「表記の正規化」と判断。06 の採点式（数量は厳密一致・寸法は？）と突き合わせて確定する ②N06「初回案 10 分」に対し run 8 は 631 秒。思考時間が大半で
  ターン数は 14。許容か、モデル/プロンプトで詰めるか（D06 仮値の見直し材料）。
- [TODO-023] **T-205 L-5/L-6 の記録のみ P3（RV-032）**: ①`check_agent_mutations.py` に L-5 の 4 変異（エラー継続を 1 回停止に戻す / 成功時リセット除去 / 項目別情報の除去 /
  input 値の混入）と L-6 の「配列を単数へ戻す」を取り込み `make agent-mutations` 一本で再現 ②評価スクリプトに「`od_unit`/`weight_unit` 等が原表記の単位と異なれば換算」
  の機械チェック ③03-spec SCR-03/04・出力で寸法は原表記を主・数値を従とする方針の確認 ④大バッチ×恒常重複（`E_EVIDENCE_DUPLICATE`）の部分成功可否は再発時に設計判断。
  TODO-009 / TODO-017 / TODO-020 と合わせて C-3（`backend/app` を触る整理）で。
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
- [TODO-005] 05-api-ipo 0.2 に「エラーコード不要の 422（標準バリデーション扱い）」の指針が無い。
  T-102 では `fromSeq > toSeq` を 422（コードなし）とした。同種の入力検証が増えるなら明文化する。
- [TODO-003] `document_issues.issue_type` の語彙（特に `reference_missing` / `not_scanned`）の
  意味づけが 04-db.md に無い。T-101 では「付随情報の欠落（引用元の日付が解釈できない等）」に
  `reference_missing` を割り当てた。設計書に用語定義を追記するとよい。

- [T-201 引き継ぎ 2026-09-12] TODO-004の別セッションは本タスク（ユーザーがT-201の担当を指示し再開を指示済み）。T-201担当を継続。TODO-002/003の判定方針は04-db.md §3.3「T-201補足」に明文化・実装済み。77件の独立テストとPostgreSQL制約15件はPASS。全体回帰はユーザーの明示指示により保留。詳細は `docs/t201-handoff.md`。DONEにはしていない。

- [T-202 着手 2026-09-12] ユーザーがT-201の全体回帰保留を維持したままT-202への着手を明示指示。依存DONEの通常ルールに対する今回の指示としてT-202を開始。全体回帰・既存設定読込・別テストDB初期化は保留を継続。G1 FEの編集中ファイルを保全する。

- [T-202 引き継ぎ 2026-09-12] API #12-21（#20共通）と永続ジョブ管理を実装、独立レビュー済。T-203未接続のローカルworkerはagent_implementation_pendingとしてfailed終端する。通常設定読込・実DBへのmigration適用・現行規則設定・実案件起動・コミット/プッシュは未実施。全体回帰とG1側型エラーは保留。
