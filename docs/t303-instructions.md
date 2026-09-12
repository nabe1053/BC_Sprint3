# T-303 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-303【FE】G3 SCR-03 Item List 確認 / SCR-04 根拠詳細**（memory §3・依存 T-302 DONE・**N-2（#24 の `rowMatch` 追補）の後に着手**）。
設計の正: 03-spec.md SCR-03（:164-243）・SCR-04（:245-298）・3 章、05-api-ipo.md #22〜#26・#29〜#33・FLOW-03・3.6・6 章、02 FUNC-06〜08・7 章、06 TEST-09/10、モック `#SCR-03`・`details()`。
前例: `docs/t103-instructions.md`・`docs/t204-handoff.md`。前提決定: AD-013 / AD-015 / AD-017 / AD-018 / AD-022 / CV-018 / CV-019 / LN-021 / LN-031 / LN-034〜036、**本書 §0（AD-024）**。

## 0. orchestrator 決定（AD-024・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| 1 | 行ごとの照合状態と `confirmationId` を返す API が無い | **案 A**: T-302 追補 **N-2** で `ItemCurrentResponse.rowMatch: {confirmationId, recordedBy, recordedAt} \| null`（未取消の一致確認）を追加（`list_items_with_edits` に select を足す読取拡張）。05 #24 書き戻し済み。**T-303 は N-2 の後に着手** |
| 2 | SCR-03 の primary | **置かない**（「担当者確認済みにする」は G5）。ドロワー内「訂正を記録」は contained 可（ダイアログと同扱い）。判断フォームの「記録」は outlined、照合はチェックボックス |
| 3 | 「案件を開く」の `latestVersionId===null` | ボタン非表示・操作列は「投入画面へ」のみ。**表示状態列は `progressStatus` から導出したラベル**（draft_review→作成案、staff_checked→担当者確認済み、review_checked→評価確認済み、intake→「—」）。確認者・日時（G5）は出さない。送付可否は「—」。`cases.list.versionNote` は「確認者・日時は承認画面で記録します」等に変更 |
| 4 | T-204 完了表示のリンク | `outcome=success` かつ `versionId` 正なら「Item List を確認する」リンク（`isComplete=false` でも出し一部完了注記は残す）。失敗・停止では出さない |
| 5 | 版の履歴パネル | **含める**（#22 最小・読取専用の版切替）。生成所要・出力・再実行・引き継ぎ警告は置かない |
| 6 | `range_class` と `length_*` の状態共有（TODO-025①） | UI 文言で吸収: 長さ列は「レンジ {rangeClass}／定尺長 {lengthValue lengthUnit}」併記・状態ラベル 1 つ |
| 7 | 数値の表示と入力 | **丸めない・文字列のまま**。原表記はドロワーで主表示。入力は 10 進文字列（分数不可。BE `exact_decimal` の受理形式を handoff に） |
| 8 | 「根拠の要約」列 | **`sourceNo`（原項番）列に置換**。根拠はドロワー |
| 9 | #25 の資料名解決 | `features/documents/index.ts` に `useDocuments` / `documentsQueryKey` を export し index 経由で使う |
| 10 | 判断欄（#33）の操作 | **行ごとの「記録」ボタン**（select 変更だけでは POST しない）。`latest` 無しは選択状態＋「未記録」ラベル |
| 11 | `item_ends`（TODO-024） | T-303 では出さない |
| 12 | 担当者名の保持 | メモリのみ |
| 13 | 数量訂正の「訂正 · 旧」 | `qty_value` と `qty_unit` の旧値をセル別に出す |
| 14 | 既存テスト 3 箇所（`CaseListPage.test.tsx:215-217`・`AgentRunPanel.test.tsx:140-150`・`case-routes.test.tsx`） | 「期待の更新」として置換（削除しない）。理由を handoff に |
| 15 | 対象案件セレクタ | 作らない（URL で選ぶ。AD-009 と同型） |

## 1. 範囲と範囲外

**範囲（FE のみ。`backend/` は触らない）**
- 新 feature `frontend/src/features/versions/`: `api.ts`（生成関数の `unwrapSuccess` wrap。`features/cases/api.ts` と同型）/ `hooks.ts` / `model.ts`（決定的関数: 状態→ラベルキー・トーン、フィルタ判定、「訂正 · 旧 ○○」組立、#29 要求組立とクライアント検査）/ `components/`（`ItemListPage`・`VersionSummary`・`ItemFilters`・`ItemTable`・`QuestionJudgementForm`・`EvidenceDrawer`（SCR-04）・`EditForm`・`EditHistory`・`VersionHistory`）/ `index.ts`（`ItemListPage` のみ公開）/ `__tests__/`
- ルート `src/app/(portal)/cases/[caseId]/versions/[versionId]/page.tsx`（薄い Server Component。ID 検証→`notFound()`）。`app/__tests__/case-routes.test.tsx` に正・不正 ID
- SCR-01 導線: `CaseListPage.tsx` 操作列に「案件を開く」（`latestVersionId` 非 null → `/cases/{caseId}/versions/{latestVersionId}`）、表示状態ラベル（§0 ③）
- T-204 導線: `RunProgress.tsx` の `agentRuns.resultNote` をリンクに置換（`RunProgress` に `caseId` を渡す）
- `shared/i18n/ja.json` に `versions.*` を **components 着手前に** 03-spec の UI 要素表と 1 対 1 で起こす（T-103 P2-6 の再発防止）

**範囲外**: SCR-05（G4。`coverageConfirmed` は文字表示のみ・リンクなし）、SCR-06・状態遷移・差し戻し・送付可否（G5）、.xlsx 出力・再実行・生成所要（G6）、`item_ends`、`due_raw`/`place_raw` 編集、`backend/**`、`shared/api/generated/**`、memory、commit。03-spec の注記更新は Claude。

## 2. 使う API（T-302 生成済み `shared/api/generated/ui.ts`。素の async 関数を `api.ts` で wrap する既存の型）

| # | 生成関数 | 応答 | unwrap |
|---|---|---|---|
| 22 | `listVersionsApiV1UiCasesCaseIdVersionsGet` | `VersionsResponse{versions}` | 200 |
| 23 | `getVersionApiV1UiVersionsVersionIdGet` | `VersionResponse{…, caseHeader\|null, counts, coverageConfirmed}` | 200 |
| 24 | `listItemsApiV1UiVersionsVersionIdItemsGet` | `ItemsResponse{items[]}`（`history[]` 取消済み含む・**N-2 後 `rowMatch`**） | 200 |
| 25 | `listEvidenceApiV1UiVersionsVersionIdItemsItemIdEvidenceGet` | `ItemEvidenceResponse` | 200 |
| 26 | `listQuestionsApiV1UiVersionsVersionIdQuestionsGet` | `QuestionsResponse`（`itemId\|null`・`latest\|null`） | 200 |
| 29 | `editItemApiV1UiVersionsVersionIdEditsPost` | `ItemEditRequest` → `EditsResponse` | **201** |
| 30 | `undoEditApiV1UiVersionsVersionIdEditsEditIdUndoPost` | `UndoRequest{recordedBy}` → `EditUndone` | **200** |
| 31 | `confirmApiV1UiVersionsVersionIdConfirmationsPost` | `ConfirmationRequest{recordedBy, kind, itemId?}` → `ConfirmationRecord` | **201** |
| 32 | `undoConfirmationApiV1UiVersionsVersionIdConfirmationsConfirmationIdUndoPost` | `UndoRequest` → `ConfirmationUndone` | **200** |
| 33 | `judgeApiV1UiVersionsVersionIdQuestionsQuestionIdJudgementsPost` | `JudgementRequest{recordedBy, status, resolution, note?}` → `JudgementRecord` | **201** |
| 4 | `listDocumentsApiV1UiCasesCaseIdDocumentsGet`（`features/documents` index 経由） | 資料名の解決 | 200 |

数値は **string | null**（丸めない）。状態語彙 `ValueState = stated|tba|not_stated|not_applicable`、`qtyState` は `numeric|tba|not_stated|not_applicable`、`currentState = draft|staff_checked|review_checked`。

## 3. 画面状態（03-spec SCR-03 の要素・操作・エラー表と 1 対 1）

- **案件メタ**: `caseHeader` の照会番号・客先・要求納期（`dueRaw`＋粒度/基準の補足）・納地・Incoterms・見積期限（TZ 不足はラベル）。`*State` が tba/not_stated/not_applicable なら空欄でなくラベル文字。null は「案件情報なし」
- **件数 7 種＋版の状態**: 明細 / 確認事項のある行 / 数量TBA / 択一グループ / 照合済み n/N（N=itemCount） / 訂正 `editCount`（補足に「訂正のある明細 `editedItemCount` 行」）/ 未解決 `unresolvedCount`。版の状態は文字ラベル
- **担当者名入力**: テーブル上に 1 つ（ラベル常時表示）。照合・取消・判断・訂正の `recordedBy` に共用。メモリのみ。網羅性確認は `coverageConfirmed` の文字（済／未）
- **絞り込み**: キーワード／品種／材質／接続／状態（全件・確認事項あり・数量TBA・択一候補・未照合のみ・訂正済みのみ・未解決のみ）／クリア／`n / N 行`。`model.ts` の純粋関数
- **テーブル**: 照合／行ID／品種／外径／単重／材質／接続／長さ／数量／単位／納期／選択グループ（＋候補区分）／状態／確認事項の要約／**原項番**／対応状況／解決状態／判断内容／詳細
  - 状態ラベル優先順: `qtyState=tba`→数量未確定 / `groupCode`→択一 / `isInheritCandidate`→継承候補 / questions あり→要確認 / それ以外「警告なし（原資料との照合は必要）」。付帯: 訂正あり・照合済み・未照合。**色は補助・ラベル文字が主**。`palette.info` 不可
  - セル: `tba`→「TBA」、`not_stated`→「記載なし」、`not_applicable`→「適用なし」（空欄と区別）。値は文字列のまま＋単位。未取消 `history` があれば「訂正 · 旧 {oldValue}」（取消済みは無視・数量は値と単位別）
  - 照合チェック: ON→#31 `{kind:"row_match", itemId, recordedBy}`、OFF→#32（`rowMatch.confirmationId`）。担当者名空なら**変えず**文言
  - 判断欄: 行の questions ごとに 対応状況・解決状態・note・**「記録」ボタン**。`latest` の `recordedBy/recordedAt` 表示。案件レベル（`itemId=null`）はテーブル下の枠
- **SCR-04 ドロワー**（右・`min(600px,94vw)`）: 見出し「行 {rowCode} · {kind}」（h2）／前後移動（絞り込み後の順・端 disabled）／原表記（`*Raw` blockquote・編集対象外）／項目ごとに採用値＋状態・出典（資料名は #4 で解決、未解決なら「資料名を取得できません」・`locator`）・`quote`・`appliedCondition`・`conversionNote`・`changeReason`＋`priorValue`。根拠が無い項目は「根拠なし」／継承候補注記／照合チェック（共用）／訂正フォーム／訂正履歴（全件・取消済みは `undoneBy/undoneAt`・未取消のみ「取り消す」→#30）／この行の確認事項＋判断フォーム
- **訂正フォーム（#29）**: 対象項目セレクタは 16 語彙のみ（日本語ラベル）。状態を持つ項目は「記載あり（値）／TBA／記載なし／適用なし」（数量は「数値（値＋単位）」）。送信規則: 記載あり→`newValue`＋`newState:"stated"`（数量系 `"numeric"`、`qty_value` は `qtyUnit` 必須）/ 状態のみ→`newState` のみ・`newValue` を送らない / `kind`・`usage_note`・`note` は `newValue` のみ。理由・修正者（初期値＝担当者名）必須。クライアントで先に止める（POST しない）が**判定の正はサーバ**（同 code で同文言）
- **3 状態**: ページ 404→「版が見つかりません」＋案件一覧へ / 明細空「この版に明細がありません」/ 絞り込み 0 件＋クリア / 確認事項空「確認事項はありません。原資料との照合は必要です」/ 根拠空「この行の根拠は登録されていません」/ 版履歴空「未生成。資料投入画面で案を作成してください」/ 各エラーは原因＋直し方＋再取得
- **記録系エラー 9 コード → 文言（`code` で分岐・生値を出さない・CV-019）**: `E_REASON_REQUIRED`（理由が空→入力）/ `E_RECORDER_REQUIRED`（記録者名が空→入力。AI は補完しない）/ `E_QTY_UNIT_REQUIRED` / `E_STATE_VALUE_CONFLICT` / `E_TARGET_INVALID`（一覧を再読み込み・items invalidate）/ `E_REQUEST_INVALID`（`details.errors` の入力値は表示しない）/ `E_FIELD_NOT_EDITABLE` / `E_ALREADY_UNDONE` 409（再読み込み）/ `E_ALREADY_CONFIRMED` 409（チェックを戻し最新化）/ `E_NOT_FOUND` 404 / 通信断・5xx「記録結果を確認できませんでした。一覧を再読み込みしてから再操作」・**自動再送しない**
- `recordedAt`/`undoneAt` は応答値のみ表示（要求に載せない・クライアント時刻を記録欄に出さない）

## 4. design-guidelines

contained は SCR-03 に置かない（ドロワー内「訂正を記録」のみ可）。h1 は 1 つ。状態はラベル文字。トーンは `tokens.colors.{ok,warn,danger}`（oklch は `muiColor()`）。罫線 `hair`/`divider`、Paper `outlined`。hex・インライン style 禁止（design-lint）。Never リスト。モック `#SCR-03` / `details()` と構成・トーン一致。

## 5. 実装順序と RED

1. `ja.json` `versions.*`（§3 と 1 対 1）
2. `api.ts` — RED `__tests__/api.test.ts`（実生成関数＋fetch モックの HTTP 境界: URL/メソッド/camelCase・201/200 の unwrap・非 2xx `ApiError(code)`・`recordedAt` 未送・数値を数値化しない）
3. `model.ts` — RED: ラベル/トーン表（優先順）・フィルタ 7 種・「訂正 · 旧」（取消済み無視・数量は別）・#29 要求組立・クライアント検査 5 種
4. `hooks.ts` — query key `["versions",caseId]` / `["version",vid]` / `["version",vid,"items"]` / `["version",vid,"questions"]` / `["version",vid,"items",itemId,"evidence"]`。mutation は `retry:false` 明示。invalidate: edit/undoEdit → items＋summary、confirm/undo → items＋summary、judge → questions＋summary（409/404 の onError でも同じ）。RED: **1 回の `renderHookWithProviders`**（LN-021）で再取得の有無を `getQueryData` で検証、本番 `Providers` で 400 の POST が 1 回（CV-018）
5. components — RED（hooks mock）: 3 状態・件数 7 種＋N・状態ラベル（色非依存）・TBA が 0/空にならない・択一合計を出さない・「訂正 · 旧」・担当者名空で POST 0 回・9 コード文言（生値の否定 assert）・判断済み∧未解決が残る・案件レベル枠・ドロワー前後の端 disabled・取消後も履歴が残る・`quote`/資料名の HTML/URL をリンク化しない
6. ルート＋導線 — RED: `case-routes.test.tsx`（正・不正 ID）、`CaseListPage.test.tsx`（`latestVersionId:1` でリンク、null で非表示、表示状態ラベル）、`AgentRunPanel.test.tsx`（リンク）。既存 3 箇所は置換
7. ブラウザ確認（T-204 と同手順。contained ≤1・h1=1・390px・pageerror 0。画像は `docs/test-results/`、ドライバはリポジトリに残さない）
8. 変異: `retry:false` を外す／クライアント検査を外す／取消済みを無視しない／`tba` 優先を外す／invalidate を 1 つ外す／状態のみ訂正で `newValue` を送る → 各テストが落ちる

## 6. 完了条件

`AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe` green（除外なし・FE 166＋新規）、`git status -- backend` 空、design-lint 0、`docs/t303-handoff.md`（触ったファイル / 実装表 / 既存テスト置換 3 箇所の理由 / 変異 / 実出力 / 画像 / 設計書の不足）→ 末尾見出し **`## 再レビュー依頼（T-303）`**。commit は Claude。
