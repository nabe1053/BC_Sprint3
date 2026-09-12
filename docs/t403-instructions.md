# T-403 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-403【FE】G4 SCR-05 網羅性照合**（memory §3・依存 T-402 DONE `1d5eab7`）。
設計の正: 03-spec.md SCR-05（:304-365）・3 章、05 #27（AD-025）・#31/#32・FLOW-04・6 章、04-db §3.3（:664-681）・§3.4 `confirmations`、02 FUNC-03/06/08、06 TEST-11、モック `mockup.html:410`。
前例: `docs/t303-instructions.md` / `docs/t303-handoff.md` / `frontend/src/features/versions/**`。前提決定: AD-024〜AD-026、CV-018/019/025/026/027、LN-021/031/058/060、TODO-030 ③（`count` を補間名に使わない）。

## 0. orchestrator 決定（AD-027・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| 1 | feature の置き場 | **`features/versions/` に追加**（#31/#32・`useRecordMutation`・`versionKey`・担当者名ガードを再利用。新 feature にすると API 関数の複製＝CV-015 違反）。`index.ts` に `InventoryPage` を公開 |
| 2 | primary | **0**。「記録」「取消」「元資料を開く」「再取得」は outlined / text（モック一致・AD-024 ② と同型） |
| 3 | 「更新」ボタン | **置かない**（未取消 coverage は版に 1 件・部分 UNIQUE）。記録済みなら「記録」非表示・「取消」のみ |
| 4 | 「元資料を開く」（#10） | **含める**。`shared/api/mutator.ts` に `apiBaseUrl` を export（1 行・共有ファイル→handoff に明記）し、資料ごとに `<a target="_blank" rel="noopener noreferrer">` |
| 5 | 集計の見せ方 | **両方**: 見出し直下に 9 件数（総要素・原明細・出力行・分割・除外・対応なし・余分・多重対応・不整合。件数は `*Ids.length`）＋各表の下に 03-spec の 1 文。`shared/ui` 抽出はしない（2 箇所目） |
| 6 | 並べ替え | 資料側 `inconsistent` → `missing` → 他 `(seq, entryId)`。明細側 `hasSource=false` → 他。**純粋関数**で UI 側 |
| 7 | トーン | `missing`=warn / `inconsistent`=danger / `mapped`・`split`=ok / `excluded`=中立（色なし） |
| 8 | 状態セル | 2 系統を常に表示（CV-027）: 1 行目 `judgement` ラベル（トーン）、2 行目 caption「記録: {statusDetail ?? statusLabel}」＋「根拠: {basis}」 |
| 9 | 見出しの説明文 | 数のみ「元資料 {sourceItemCount} 項目 → Item List {outputRowCount} 行（分割 n・除外 n・対応なし n）」。分割理由の内訳は出さない |
| 10 | 「照合する範囲」 | 資料名一覧（distinct・null は「資料名を取得できません」）＋固定注記。ページ構成の文は出さない |
| 11 | 確認者名 | 画面ごとに入力（SCR-03 と共有しない）。メモリのみ。記録済みなら入力欄は取消者名に共用 |
| 12 | 対象案件セレクタ | 作らない（URL） |
| 13 | SCR-03 の導線 | `ItemListPage.tsx:150-160` の `versions.coverage` 表示の隣に「網羅性照合へ」（済・未どちらでも）。SCR-05 側に「Item List へ」 |
| 14 | 既存テスト | 期待の更新として置換（削除しない・理由を handoff に） |
| 15 | `E_ALREADY_CONFIRMED` 文言 | 網羅性用に `versions.inventory.errors.E_ALREADY_CONFIRMED`「網羅性確認は既に記録されています。最新の記録を表示します」。`inventoryErrorKey()` が上書き→`recordErrorKey` へフォールバック |

## 1. 範囲と範囲外

**範囲（FE のみ）**: `features/versions/` に `api.getInventory`・`hooks`（`inventoryKey=["version",vid,"inventory"]`・`useInventory`・`useCoverageMutations`。既存 `useRecordMutation` の `resource` を `"items"|"questions"|"inventory"` に拡張）・`model`（`sortEntries`/`sortItems`/ラベル決定/`inventoryCounts`/`documentNames`/`buildCoverageRequest`/`inventoryErrorKey`）・components（`InventoryPage`・`InventoryScopePanel`・`CoverageRecordPanel`・`InventoryEntriesTable`・`InventoryItemsTable`）・`testing/fixtures.ts` 追記・tests。ルート `src/app/(portal)/cases/[caseId]/versions/[versionId]/inventory/page.tsx`（薄い Server Component）。SCR-03 導線。`shared/api/mutator.ts` `apiBaseUrl`。`ja.json` `versions.inventory.*`（components 着手前に 03-spec の表と 1 対 1）。
**範囲外**: G5（担当者確認済み・`E_COVERAGE_NOT_RECORDED`・SCR-06）、G6、`backend/**`、`generated/**`（編集禁止。再生成は `make check-fe`）、memory、commit、03-spec 注記（Claude）。

## 2. 使う API（`shared/api/generated/ui.ts`。T-402 commit 後の再生成で名前を確認して handoff に）

| # | 生成関数 | 応答/要求 | unwrap |
|---|---|---|---|
| 27 | `getInventoryApiV1UiVersionsVersionIdInventoryGet` | `InventoryResponse{summary, entries[], items[]}` | 200 |
| 31 | 既存 `api.confirm` | `{recordedBy, kind:"coverage"}`（`itemId` を載せない） | 201 |
| 32 | 既存 `api.undoConfirmation` | `{recordedBy}`・path `summary.coverage.confirmationId` | 200 |
| 23 | 既存 `useVersion` | 版の状態ラベル | 200 |
| 10 | `getGetFileApiV1UiDocumentsDocumentIdFileGetUrl(documentId)` ＋ `apiBaseUrl` | `<a>` で別タブ | — |

DTO: `InventorySummaryResponse`（3 件数・6 ID 配列（BE で昇順）・`coverage: RowMatchResponse|null`）、`InventoryEntryResponse`（`entryId, documentId, documentFileName|null, position, sourceNo|null, seq, excerpt, status(4), statusDetail|null, basis|null, linkedItems[{itemId,rowCode}], linkCount, judgement(5)`）、`InventoryItemResponse`（`itemId, rowCode, sourceNo, seq, groupCode|null, candidateLabel|null, sourceEntries[{entryId,documentId,position,sourceNo}], hasSource`）。**注記**: `inconsistentEntryIds` は `entries[]` の部分集合とは限らない → 件数は配列長、行の強調は `entry.judgement` で決める（ID 照合に依存しない）。

## 3. 画面状態（03-spec SCR-05 の要素表・状態表・操作表・エラー表と 1 対 1）

- **見出し**（h1）「網羅性照合」＋説明文（§0 ⑨）＋「Item List へ」。版番号・状態は `useVersion` の文字ラベル
- **前提の注記**（N03）: 「対応なし 0 件は網羅性の保証ではない」（モック冒頭の文を i18n に）。**unmapped=0 でも必ず表示**
- **件数 9 種**（`dl`・`VersionSummary` 同型・補間名に `count` 不可）
- **照合する範囲**: 資料名 distinct（初出順・null→未解決文言）＋「元資料を開く」（§0 ④）＋固定注記「全ページ・全シート・本文と、追加・別紙・脚注の有無を確認します。この対応表に抽出漏れ検出機能はありません」
- **網羅性確認の記録**: 確認者名 `TextField`（ラベル常時・必須・helper「AI は補完しません」・メモリのみ）。未記録→「記録」（outlined）→ #31。空なら **POST せず** `E_RECORDER_REQUIRED` 文言。記録済み→「記録済み：{recordedBy} / {recordedAt}（応答値）」＋「取消」→ #32（取消者名必須）。二重送信ロック（`useRef`）。補足文（未記録「担当者確認済みにするには本記録が必要」/ 記録済み「取り消すと前提は未達に戻る」）
- **原明細一覧（資料側）**: 位置 / 原項番（null→—）/ 原文抜粋（文字のまま・リンク化しない）/ 対応（`linkedItems[].rowCode` を「, 」結合・0 件→—）/ 状態（§0 ⑧ 2 系統）。`judgement` ラベル: 対応済み / 分割 / 除外 / 対応なし（欠落の可能性）/ 不整合（記録された状態と対応関係が一致しません）。並びは §0 ⑥。表下 1 文「明細 n 件 → 出力 n 行（うち分割 n 件）／除外 n 件／対応なし n 件。対応なし（欠落の可能性）は先頭に表示されます」
- **Item List 対応表（明細側）**: 行ID / 原項番 / 候補（`groupCode` があれば「{groupCode} · {candidateLabel}」）/ 対応元（`{position}（原項番 {sourceNo}）` 列挙・0 件→—）/ 状態（対応あり ／ 対応なし（余分の可能性）warn）。`multiMappedItemIds` の行は付帯「多重対応（n 要素）」。並び `hasSource=false` 先頭。表下 1 文「元資料に対応元がない出力行 n 件。対応なしは、除外の根拠があれば意図した除外、なければ欠落として扱います」
- **3 状態**: loading `common.loading` / 404「版が見つかりません。案件一覧から版を選び直してください」＋案件一覧・Item List へ / 取得失敗「照合データを取得できませんでした。接続を確認して再取得してください」＋再取得 / 空「この版にはインベントリがありません。資料投入画面で案を作成してください」＋リンク。片側のみ空は各表に「該当なし」
- **記録系エラー（code で分岐・生値非表示・CV-019）**: `E_RECORDER_REQUIRED` 400 / `E_ALREADY_CONFIRMED` 409（§0 ⑮・inventory＋version を invalidate）/ `E_ALREADY_UNDONE` 409（invalidate）/ `E_NOT_FOUND` 404 / `E_TARGET_INVALID` 400 / 通信断・5xx「記録結果を確認できませんでした。再読み込みしてから再操作してください」・**自動再送しない**
- `recordedAt` は要求に載せない・表示は応答値のみ。入力初期値は空

## 4. design-guidelines

primary 0。h1 1（パネル見出しは h2）。状態はラベル文字が主・トーンは `tokens.colors.{ok,warn,danger}`（`muiColor()`）。`palette.info` 不可・5 色目なし。Paper `outlined`・罫線 `hair`/`divider`・hex/インライン style 禁止（design-lint）。表は横スクロール。モック `#SCR-05` と構成一致（注記 → 上段 2 パネル → 下段 2 表 → 各表下の 1 文）。

## 5. 実装順序と RED

1. `ja.json` `versions.inventory.*` → 2. `api.getInventory`（RED: URL/GET/200/非 2xx `ApiError`・並べ替えなし）→ 3. `model`（RED: 並び 2 種・ラベル決定・`inventoryCounts` は配列長・`documentNames`・`buildCoverageRequest` は `kind:"coverage"`＋`itemId` なし＋空白名で `E_RECORDER_REQUIRED`・`inventoryErrorKey` の上書きとフォールバック）→ 4. `hooks`（RED: `inventoryKey`・confirm/undo 後に inventory＋`versionKey` を再取得し `itemsKey` は触らない・409/404 でも再取得・`retry:false`・**1 回の `renderHookWithProviders`**・本番 `Providers` で 400 POST が 1 回）→ 5. components（RED: 3 状態・注記が unmapped=0 でも出る・9 件数と ID 生値非表示・並び・2 系統ラベル・`inconsistent` が文字で判別・HTML/URL リンク化なし・多重対応ラベル・確認者名空で POST 0・`{kind:"coverage", recordedBy}` 1 回・記録済みで「記録」非表示と「取消」の引数・`recordedAt` 応答値・`E_ALREADY_CONFIRMED` 網羅性文言（行向き文言の否定）・「元資料を開く」の href と `rel`・h1 1・contained 0）→ 6. ルート＋導線（RED: `case-routes.test.tsx` 正・不正 ID、SCR-03 の「網羅性照合へ」href。影響する既存 assert は置換）→ 7. `mutator.ts` `apiBaseUrl`（RED: 既定値と env 優先）→ 8. ブラウザ確認（画像は `docs/test-results/coverage-review-ui/`・ドライバは残さない）→ 9. 変異（先頭優先を外す / 件数を配列長以外に / `retry:false` / `versionKey` invalidate / クライアント検査 / `itemId:null` 混入 / `E_ALREADY_CONFIRMED` 上書き / `rel`）→ 10. `npx prettier --write` → `AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe`

## 6. 完了条件

`make check-fe` green（除外なし・FE 266＋新規・prettier 込み）、`git status --short -- backend` 空、design-lint 0、`generated/**` 手編集なし、`docs/t403-handoff.md`（触ったファイル（本体 / 共有 `mutator.ts`・`ItemListPage.tsx`・`ja.json`）→ 実装表 → 既存テスト置換の理由 → 変異 → ブラウザ証跡 → **「T-501 へ渡す契約」節は不要（FE）**）→ 末尾見出し **`## 再レビュー依頼（T-403）`**。commit は Claude。pytest は回さない。
