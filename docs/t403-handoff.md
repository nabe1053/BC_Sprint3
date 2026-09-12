# T-403 handoff

§7 **2026-09-13 14:20版**、`docs/t403-instructions.md` / AD-027 の15決定に従って実装。希望Status: REVIEWING。**`AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe`: 24 suites / 326 tests PASS**（既存266＋新規60）。design-lint違反0、ブラウザpageerror0。commit・memory編集なし。

## 変更ファイル

本体は既存 `frontend/src/features/versions/` 内に追加:

- `api.ts:110`: #27 `getInventory`。`hooks.ts`: inventoryKey / useInventory / useCoverageMutations、既存useRecordMutationのresourceにinventoryを追加。
- `model.ts:206`以降: sortEntries / sortItems / inventoryState / inventoryCounts / documentNames / buildCoverageRequest / inventoryErrorKey。
- 新規components5本: `InventoryPage.tsx`、`InventoryScopePanel.tsx`、`CoverageRecordPanel.tsx`、`InventoryEntriesTable.tsx`、`InventoryItemsTable.tsx`。
- `index.ts`: InventoryPage公開。`testing/fixtures.ts`: 合成照合データを追記（不整合・欠落・余分・多重対応・分割・除外の例）。
- `__tests__/inventory-api.test.ts` / `inventory-model.test.ts` / `inventory-hooks.test.tsx` / `inventory-components.test.tsx` を新規追加。既存 `components.test.tsx` に導線2件追加。
- `frontend/src/app/(portal)/cases/[caseId]/versions/[versionId]/inventory/page.tsx`: 正整数の案件/版を検査する薄いServer Component。`app/__tests__/case-routes.test.tsx`に6件追加。

共有ファイル（指示書の許可範囲）:

- `frontend/src/shared/api/mutator.ts:19`: **`export const apiBaseUrl = baseURL;` 1行のみ**。既存fetchと同じ接続先を原本リンクに公開。`shared/api/__tests__/base-url.test.ts`に既定値/公開設定優先の2件追加。
- `frontend/src/features/versions/components/ItemListPage.tsx`: coverage表示の隣に「網羅性照合へ」。確認済み/未確認のどちらでも表示。
- `frontend/src/shared/i18n/ja.json`: `versions.inventory.*` をcomponentsより先に追加。状態・操作・エラーの語彙を指示書と対応させた。補間変数に予約名`count`を使用していない。

本handoffと`docs/test-results/coverage-review-*`のログ・8画像を追加。検証用Makefile・変異/ブラウザドライバは/tmpのみで、リポジトリに残していない。既存`tsconfig.tsbuildinfo`差分を保全。`git status --short -- backend`は空、[BEの前後ハッシュ比較](test-results/coverage-review-boundaries-2026-09-13.log)も変更0。pytest・migration・実モデル呼出しなし。

## 実装・レビュー対応表

| 決定・画面観点 | 実装 | RED→GREEN / 検証 |
|---|---|---|
| AD-027① feature再利用 / #27 GET | api.getInventoryは `getInventoryApiV1UiVersionsVersionIdInventoryGet` を呼びunwrap200。#31/#32は既存api.confirm / undoConfirmationを再利用 | inventory-api **3 FAIL→3 PASS**。実生成fetchのURL/GET/200/404/500、未整列応答をそのまま返す、エラーはApiErrorで1回 |
| ⑤⑨ 9件数・実数説明文 | inventoryCountsは3件数＋6 ID配列のlength。説明と表下注記も実数。inconsistentEntryIdsにentriesに無い98765があっても2件として表示 | inventory-model **19 FAIL→19 PASS**。画面でdlのdt9件/dd9値を完全一致、98765は非表示、分割理由の推測なし |
| ⑥ 並び / ⑦ トーン | sortEntriesはinconsistent→missing→(seq,entryId)、sortItemsはhasSource=false→(seq,itemId)。コピーを並べ、元配列は不変。missing=warn / inconsistent=danger / mapped,split=ok / excluded=中立 | modelで順序・tie・入力不変・5語彙のtone。画面とブラウザもp.5→p.4、R3先頭を確認。行強調はjudgementのみから決定 |
| ⑧ 保存状態と導出判定 / CV-027 | 状態セルにjudgementの文字＋caption「記録: statusDetail ?? statusLabel」、basisありなら別caption | 不整合の行に「不整合（記録された状態と対応関係が一致しません）」と「記録: 対応済み」を同時表示。除外詳細と根拠もassert |
| ④⑩ 範囲・原本リンク | documentNamesで初出順distinct/null保全。同名資料はまとめて表示し、documentIdごとに#10へのリンク。`apiBaseUrl`＋生成URL関数、target=_blank / rel=noopener noreferrer | 名前2種・リンク2つ・href/rel/targetをassert。base-url **2 FAIL→2 PASS**（既定値/公開設定優先、customInstanceが同じbaseでfetch）。原文のHTML/URLはReact文字列のまま、資料表内のa/scriptは0 |
| ②③⑪ 確認記録・取消 | primary0。確認者名は空で開始し画面メモリのみ。記録済みは記録ボタンなし、取消のみ。応答名/日時を表示し取消にも入力名必須。useRefで二重送信をロック | 未入力POST0、trimした `{kind:"coverage", recordedBy}` 1回、要求にitemId/recordedAtなし。取消は応答confirmationId＋入力名。入力必須・常時ラベル・AI非補完helper、記録済み応答日時、送信中disabledをassert |
| ⑮ エラー・再送抑止 / CV-019 | inventoryErrorKeyはE_ALREADY_CONFIRMEDだけ網羅性文言へ、他はrecordErrorKey。409/404/E_TARGET_INVALIDはinventory＋versionをinvalidate。全mutation retry:false | hooks **9 FAIL→9 PASS**。confirm/undo×成功/409/404/400を各1回renderHookWithProvidersで同じclientの再取得まで検査、items取得は1回のまま。本番Providersで400 POST1回（既定retry1よりhook設定が優先） |
| 記録系エラー表示 | E_ALREADY_CONFIRMED / ALREADY_UNDONE / NOT_FOUND / TARGET_INVALID / 5xxを固定文言へ。再取得操作はinventory/版両方 | 画面で5コードの表示、private/secret非露出、競合時の行向き文言の否定。通信断等の未知値はmodelテストで既存unknown文言へ |
| 3状態・N03 | loading明示、404→案件一覧/Item List、失敗→原因と再取得、両表空→資料投入、片側空→該当なし。unmapped=0でも「対応なし 0 件は網羅性の保証ではない」を常時表示 | components初回は未実装moduleでsuite FAIL→**19 PASS**。両queryの404/通信エラー、再取得2回、空/片側空、0件注記をassert |
| 出力側の対応・候補 | hasSourceの文字、G1 · A区切り、対応元位置と原項番、multiMappedItemIdsに属する行に「多重対応（n 要素）」、表下の規定注記 | R3余分先頭、G1 · A、p.1（原項番1）、多重対応2要素、集計注記をassert。どちらの表も横スクロールで、見出しはnowrap |
| ⑫⑬ URL選択・往復導線 | URL案件/版に固定。SCR-03 coverage隣→SCR-05、SCR-05→Item List。ルートkeyで案件/版変更時に入力状態をリセット | ルート未実装suite FAIL＋既存画面の新導線 **2 FAIL / 31 PASS** → ルート/既存画面合わせ **53 PASS**。不正5種×両ID、正しいID、coverage済/未両方のhref |
| ⑭ 既存assertの保全 | 既存期待値の置換は不要だったため、既存assertを削除/弱化せず追記のみ | 既存266件を含め全326件成功。追加60=API3＋model19＋hooks9＋components19＋route6＋導線2＋base2 |

## テスト実行・変異

開発中の高速フィードバック:

```sh
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-api
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-model
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-hooks
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-components
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-routes
CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-base
make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-mutations
```

[変異一覧](test-results/coverage-review-mutations-2026-09-13.log)。隔離コピーで1箇所ずつ変更し、assert失敗を検出。本体は変更していない。

| 変異 | 実結果 |
|---|---|
| 資料側の先頭優先を外す | 1 FAIL / 18 PASS |
| 明細側の先頭優先を外す | 1 FAIL / 18 PASS |
| 不整合件数を配列長から0へ | 1 FAIL / 18 PASS |
| retry:falseを外す | 1 FAIL / 8 PASS |
| versionKeyのinvalidateを外す | 8 FAIL / 1 PASS |
| クライアント確認者名検査を外す | 2 FAIL / 17 PASS |
| coverage要求にitemId:nullを混入 | 1 FAIL / 18 PASS |
| E_ALREADY_CONFIRMED上書きを外す | 1 FAIL / 18 PASS |
| 原本リンクのrelを外す | 1 FAIL / 18 PASS |

9変異の詳細ログは`test-results/coverage-review-mutation-*.log`。初回typecheckでは新テストのTesting Library getByRoleにPlaywright用の`exact`オプションを書いていたため型エラーになった。Testing Libraryの名前完全一致に不要なオプションだけを除き、assertの対象は維持して全体を通した。

## ブラウザ確認

```sh
make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-design coverage-review-browser
```

[実結果](test-results/coverage-review-browser-2026-09-13.log): **design-lint違反0 / h1=1 / contained=0 / 390px幅でdocument横はみ出し0 / pageerror0**。実ブラウザ＋合成API応答で確認し、BEや実資料は使っていない。

原本リンクのhref/rel/target、先頭優先、原文非リンク化、空名POST0、記録→応答名/日時表示→取消（各POST1回）、空/片側空/取得失敗/404を検証。資料表見出しの縦折返しを避けるnowrap調整後に8画像を再採取し、最終ゲートも再実行した。初回ブラウザドライバはNextのroute announcerもalertとして拾ったため、確認記録パネル内へ検査範囲を絞った。

- [一覧・異常状態](test-results/coverage-review-ui/overview.png)
- [記録済み](test-results/coverage-review-ui/recorded.png)
- [取消後](test-results/coverage-review-ui/undone.png)
- [390px表示](test-results/coverage-review-ui/mobile.png)
- [片側空](test-results/coverage-review-ui/one-side-empty.png)
- [両側空](test-results/coverage-review-ui/empty.png)
- [取得失敗](test-results/coverage-review-ui/error.png)
- [404](test-results/coverage-review-ui/not-found.png)

## 最終ゲート

```sh
make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-format
AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe
```

[全ログ](test-results/coverage-review-regression-2026-09-13.log):

```text
OpenAPI schema exported to: openapi.json
🎉 api - Your OpenAPI spec has been converted into ready to use orval!
All matched files use Prettier code style!
Test Suites: 24 passed, 24 total
Tests:       326 passed, 326 total
Snapshots:   0 total
Time:        19.684 s
Ran all test suites.
✅ check-fe: frontend green
```

Orvalモデル146を維持、生成コードの手編集なし。#27の生成関数名はT-402再生成後の `getInventoryApiV1UiVersionsVersionIdInventoryGet`、#10 URLは `getGetFileApiV1UiDocumentsDocumentIdFileGetUrl` を確認した。G5/G6の操作や業務状態遷移は追加していない。

## 再レビュー依頼（T-403）

## R-2 対応

RV-043 P2-1/P3-1: `frontend/src/shared/i18n/ja.json:484` の注意文を `noticeLead` / `noticeBody` に分割し、モックの抽出範囲・ページ／別紙／後続メールの見落としに関する説明を全文反映。`requiredNote:509`・`undoNote:510` も敬体へ変更。`frontend/src/features/versions/components/InventoryPage.tsx:83` で両方を常時表示し、見出し句だけ既存の `tokens.typography.weight.bold` で強調（色は追加なし）。

`frontend/src/features/versions/__tests__/inventory-components.test.tsx:62`・`:69` の既存期待文字列を更新し、`:302` に説明全文と記録／取消時の敬体を検証するケースを追加。RED は `AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/coverage-review-checks.mk coverage-review-components`: **3 failed / 17 passed**。修正後 `AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe`: **24 suites / 327 passed / 14.289 s**（lint・型・生成を含め green）。実出力: `docs/test-results/coverage-review-r2-{red,green}-2026-09-13.log`。pytest と jest の同時実行なし。

## 再レビュー依頼（T-403）
