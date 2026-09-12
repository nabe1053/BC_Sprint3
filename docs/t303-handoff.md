# T-303 handoff

## O-2 対応（RV-039）

§7 **2026-09-13 11:40版**に着手、**12:20版**の継続指示を確認。P2 2件を修正し、Status: REVIEWING。**再レビュー依頼**。commit・memory編集なし。T-401 は Claude の commit `949d043` / RV-040 DONE を確認し、変更していない。

| 指摘 | 修正ファイル・内容 | RED → GREEN・検証 |
|---|---|---|
| P2-1 / CV-025 | `frontend/src/features/versions/components/ItemValue.tsx:51` に DimensionValue。現在の値/単位は共有状態で一度だけ表示し、値/単位それぞれの旧値は PreviousValue で保持。`ItemTable.tsx:150,153` の外径・単重に適用 | `components.test.tsx:492` 以降の5件追加。od/weight/wallを実際のtd内で各1ラベルと検査＋実一覧のod/weight列を検査。RED **5 FAIL / 26 PASS** → **31 PASS**。状態ラベルを再度二重にする変異も **5 FAIL / 26 PASS** で検出 |
| P2-2 / CV-026 | frontend の全 `src/**/*.{ts,tsx}` を Prettier 整形。`Makefile:71` fe-lint に `npx --no-install prettier --check` を追加。`package.json` / lock にローカル Prettier を devDependency 追加。`orval.config.ts` の旧 `prettier: true` を現行版が読む `formatter: 'prettier'` に変更 | 追加ゲートは未整形 **126ファイルでFAIL**。整形後の初回check-feはorvalが117生成ファイルを未整形へ戻してFAIL → formatter設定追従後、再生成を含め **All matched files use Prettier code style!** |

SCR-03 の19列仕様には肉厚列がないため、列を新設せず、共通 DimensionValue の wall 分岐をセルとして検証した。stated の小数文字列は数値変換せず結合する。P3の記録のみ6件には着手していない。

Orval v8.30.0 のインストール済み `node_modules/orval/dist/config-BF1guadq.mjs:769,3195` は `outputOptions.formatter` / `output.formatter` を読み、旧 `prettier` は読まない。型定義にも `formatter?: SupportedFormatter` がある。生成物の手修正・除外追加ではなく、再生成時の整形を修正した。

### O-2 の検証結果

```sh
# 限定テスト・変異は開発中のフィードバック
CI=true make -f Makefile -f /tmp/item-review-checks.mk item-review-components
make -f Makefile -f /tmp/item-review-checks.mk item-review-dimension-mutations
make fe-lint
make -f Makefile -f /tmp/item-review-checks.mk item-review-format-all
# 提出根拠（除外なし）
AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe
make -f Makefile -f /tmp/item-review-checks.mk item-review-design item-review-browser
```

最終ゲート出力（[全ログ](test-results/item-review-o2-regression-2026-09-13.log)）:

```text
All matched files use Prettier code style!
Test Suites: 19 passed, 19 total
Tests:       266 passed, 266 total
Snapshots:   0 total
Time:        14.805 s
Ran all test suites.
✅ check-fe: frontend green
```

[追加RED](test-results/item-review-dimensions-red-2026-09-13.log) / [GREEN](test-results/item-review-dimensions-green-2026-09-13.log) / [二重表示変異](test-results/item-review-mutation-shared-state-label-2026-09-13.log) / [整形ゲートRED](test-results/item-review-format-red-2026-09-13.log) / [整形実行](test-results/item-review-format-write-2026-09-13.log)。

[design-lint・ブラウザ](test-results/item-review-o2-browser-2026-09-13.log): 違反0、pageerror0、390px画面外はみ出し0、h1=1、contained=一覧0/詳細1、担当者空POST0/明示照合POST1、引用エスケープ・前後端制御PASS。`test-results/item-review-ui/` の8画像も再採取し、一覧の単重が「記載なし」1回になったことを視認した。実API/モデルは使わずfixture応答。BE差分なし、migrationなし。

### 整形対象ファイル一覧

全srcにコマンドを実行し、実際に内容が変わったのは以下126ファイル（うち生成コード117）。生成コードはgitignore対象で、最終内容はOrvalによる再生成。`documents/__tests__/hooks.test.tsx` は `Prettier(HEAD)` との完全一致も確認した。O-2の機能差分は上表の ItemValue / ItemTable / components.test とゲート設定。その他は整形のみで、既存のT-303実装差分は保全した。

<details>
<summary>126ファイル（frontend/src 基準）</summary>

```text
app/(portal)/cases/[caseId]/versions/[versionId]/page.tsx
app/__tests__/case-routes.test.tsx
features/agent-runs/components/RunProgress.tsx
features/agent-runs/components/__tests__/AgentRunPanel.test.tsx
features/cases/components/CaseListPage.tsx
features/cases/components/__tests__/CaseListPage.test.tsx
features/documents/__tests__/hooks.test.tsx
features/versions/__tests__/components.test.tsx
features/versions/components/ItemValue.tsx
shared/api/generated/agent.ts
shared/api/generated/health.ts
shared/api/generated/model/agentRunResponse.ts
shared/api/generated/model/agentRunResponseOutcome.ts
shared/api/generated/model/agentRunResponseStage.ts
shared/api/generated/model/agentRunResponseStopReason.ts
shared/api/generated/model/caseHeaderResponse.ts
shared/api/generated/model/caseHeaderResponseCustomerNameState.ts
shared/api/generated/model/caseHeaderResponseDueBasis.ts
shared/api/generated/model/caseHeaderResponseDueGranularity.ts
shared/api/generated/model/caseHeaderResponseDueState.ts
shared/api/generated/model/caseHeaderResponseIncotermsState.ts
shared/api/generated/model/caseHeaderResponseInquiryNoState.ts
shared/api/generated/model/caseHeaderResponsePlaceState.ts
shared/api/generated/model/caseHeaderResponseQuoteDeadlineTzState.ts
shared/api/generated/model/caseListItem.ts
shared/api/generated/model/caseListItemProgressStatus.ts
shared/api/generated/model/caseListResponse.ts
shared/api/generated/model/confirmationRecord.ts
shared/api/generated/model/confirmationRecordKind.ts
shared/api/generated/model/confirmationRequest.ts
shared/api/generated/model/confirmationRequestKind.ts
shared/api/generated/model/contentResponse.ts
shared/api/generated/model/documentIntakeResponse.ts
shared/api/generated/model/documentIntakeResponseReadStatus.ts
shared/api/generated/model/documentSummary.ts
shared/api/generated/model/documentSummaryKind.ts
shared/api/generated/model/documentSummaryReadStatus.ts
shared/api/generated/model/documentsListResponse.ts
shared/api/generated/model/editsResponse.ts
shared/api/generated/model/emailPartResponse.ts
shared/api/generated/model/emailPartResponsePartRole.ts
shared/api/generated/model/emailResponse.ts
shared/api/generated/model/endRequest.ts
shared/api/generated/model/endRequestSide.ts
shared/api/generated/model/endRequestThreadEnd.ts
shared/api/generated/model/errorResponse.ts
shared/api/generated/model/finalizedResponse.ts
shared/api/generated/model/getContentApiV1AgentDocumentsDocumentIdContentGetParams.ts
shared/api/generated/model/getContentApiV1UiDocumentsDocumentIdContentGetParams.ts
shared/api/generated/model/hTTPValidationError.ts
shared/api/generated/model/headerRequest.ts
shared/api/generated/model/headerRequestCustomerNameState.ts
shared/api/generated/model/headerRequestDueBasis.ts
shared/api/generated/model/headerRequestDueGranularity.ts
shared/api/generated/model/headerRequestDueState.ts
shared/api/generated/model/headerRequestIncotermsState.ts
shared/api/generated/model/headerRequestInquiryNoState.ts
shared/api/generated/model/headerRequestPlaceState.ts
shared/api/generated/model/headerRequestQuoteDeadlineTzState.ts
shared/api/generated/model/healthCheckApiV1HealthGet200.ts
shared/api/generated/model/index.ts
shared/api/generated/model/inventoryBatchRequest.ts
shared/api/generated/model/inventoryCreated.ts
shared/api/generated/model/inventoryRequest.ts
shared/api/generated/model/inventoryRequestStatus.ts
shared/api/generated/model/issueCreateRequest.ts
shared/api/generated/model/issueCreateRequestIssueType.ts
shared/api/generated/model/itemCurrentResponse.ts
shared/api/generated/model/itemCurrentResponseConnectionState.ts
shared/api/generated/model/itemCurrentResponseDueState.ts
shared/api/generated/model/itemCurrentResponseGradeState.ts
shared/api/generated/model/itemCurrentResponseLengthState.ts
shared/api/generated/model/itemCurrentResponseOdState.ts
shared/api/generated/model/itemCurrentResponsePlaceState.ts
shared/api/generated/model/itemCurrentResponseQtyState.ts
shared/api/generated/model/itemCurrentResponseWallState.ts
shared/api/generated/model/itemCurrentResponseWeightState.ts
shared/api/generated/model/itemEditRecord.ts
shared/api/generated/model/itemEditRecordField.ts
shared/api/generated/model/itemEditRecordNewState.ts
shared/api/generated/model/itemEditRecordOldState.ts
shared/api/generated/model/itemEditRequest.ts
shared/api/generated/model/itemEditRequestField.ts
shared/api/generated/model/itemEditRequestNewState.ts
shared/api/generated/model/itemEvidenceResponse.ts
shared/api/generated/model/itemRequest.ts
shared/api/generated/model/itemRequestConnectionState.ts
shared/api/generated/model/itemRequestDueState.ts
shared/api/generated/model/itemRequestGradeState.ts
shared/api/generated/model/itemRequestLengthState.ts
shared/api/generated/model/itemRequestOdState.ts
shared/api/generated/model/itemRequestPlaceState.ts
shared/api/generated/model/itemRequestQtyState.ts
shared/api/generated/model/itemRequestWallState.ts
shared/api/generated/model/itemRequestWeightState.ts
shared/api/generated/model/itemsCreated.ts
shared/api/generated/model/itemsRequest.ts
shared/api/generated/model/itemsResponse.ts
shared/api/generated/model/judgementRecord.ts
shared/api/generated/model/judgementRecordResolution.ts
shared/api/generated/model/judgementRecordStatus.ts
shared/api/generated/model/judgementRequest.ts
shared/api/generated/model/judgementRequestResolution.ts
shared/api/generated/model/judgementRequestStatus.ts
shared/api/generated/model/pageContent.ts
shared/api/generated/model/pageContentReadStatus.ts
shared/api/generated/model/questionRequest.ts
shared/api/generated/model/questionRequestCategory.ts
shared/api/generated/model/questionResponse.ts
shared/api/generated/model/questionResponseCategory.ts
shared/api/generated/model/questionsResponse.ts
shared/api/generated/model/rootGet200.ts
shared/api/generated/model/runStepResponse.ts
shared/api/generated/model/runStepResponseResultStatus.ts
shared/api/generated/model/runStepsResponse.ts
shared/api/generated/model/searchApiV1AgentCasesCaseIdSearchGetParams.ts
shared/api/generated/model/searchResponse.ts
shared/api/generated/model/validationResponse.ts
shared/api/generated/model/versionListItem.ts
shared/api/generated/model/versionListItemCurrentState.ts
shared/api/generated/model/versionResponse.ts
shared/api/generated/model/versionResponseCurrentState.ts
shared/api/generated/model/versionsResponse.ts
shared/api/generated/model/violationResponse.ts
shared/api/generated/model/violationResponseKind.ts
shared/api/generated/ui.ts
```

</details>

---

§7 **2026-09-13 09:50版**でN-2/L-8cの全体ゲート成功後に着手し、**10:40版**の継続指示を確認。Status: REVIEWING。最終`AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe`は**19 suites / 261 tests PASS**（既存166＋新規95）、design-lint違反0、ブラウザpageerror 0。commit・memory編集なし。

## 変更ファイル

- `frontend/src/features/versions/`: `api.ts`、`model.ts`、`hooks.ts`、`index.ts`。公開はItemListPageのみ。
- 同`components/`: `ItemListPage.tsx`、`VersionSummary.tsx`、`ItemFilters.tsx`、`ItemTable.tsx`、`ItemValue.tsx`、`QuestionJudgementForm.tsx`、`EvidenceDrawer.tsx`、`EditForm.tsx`、`EditHistory.tsx`、`VersionHistory.tsx`。
- 同`__tests__/`: api/model/hooks/componentsの4ファイル、共通データは`testing/fixtures.ts`。
- `frontend/src/app/(portal)/cases/[caseId]/versions/[versionId]/page.tsx`と`app/__tests__/case-routes.test.tsx`。
- `features/cases/components/CaseListPage.tsx`と既存テスト、`features/agent-runs/components/RunProgress.tsx` / `AgentRunPanel.tsx`と既存テスト、`features/documents/index.ts`（useDocuments/documentsQueryKeyの公開）。
- `shared/i18n/ja.json`（versions.*をcomponentsより先に作成、既存導線文言を更新）、本handoff、`docs/test-results/item-review-*`の出力・画像。

BE app/testsの160ファイルはT-303着手時ハッシュと一致（[比較結果](test-results/item-review-boundaries-2026-09-13.log)）。先行L-8c/N-2はClaudeのcommit `4fb11f6`に取り込まれ、完了時`git status --short -- backend`は空。生成APIはMakeの再生成のみで手編集なし。既存`frontend/tsconfig.tsbuildinfo`差分は保全。

## 実装・レビュー対応

下表の相対ファイルは`frontend/src/features/versions/`基準。限定テストは`make -f Makefile -f /tmp/item-review-checks.mk item-review-{api,model,hooks,components,routes}`でRED→GREENを確認し、提出根拠は末尾の除外なしcheck-fe。採取用Makefile・ブラウザ/変異ドライバは/tmpだけに置き、リポジトリには残していない。

| 項目 | 変更内容（file:line） | REDテスト・実出力 |
|---|---|---|
| API 10経路 | `api.ts:21`以降。実生成関数＋unwrapSuccessでGET200 / 記録201 / 取消200を区別。数値・camelCaseをそのまま送る | api.testの14件。初回未実装moduleでsuite FAIL→14 PASS。URL/メソッド・201/200・400/409/404/500・recordedAt未送信・長い10進文字列を実fetch境界でassert |
| 状態・フィルタ・訂正 | `model.ts:57,81,90,137`。TBA→択一→継承→確認事項→警告なしの文字/トーン、全件を含む7フィルタ、取消済みを除いた旧値、16項目の要求組立と入力検査 | model.testの31件。未実装moduleでFAIL→31 PASS。判断済み未解決を残す、数量値/単位の旧値を別々に表示、状態のみではnewValue/qtyUnitを送らない |
| キャッシュ・再送抑止 | `hooks.ts:21,51,83`。指定query keyを使用。全mutationでretry:false。items系はitems＋summary、judgeはquestions＋summary。409/404とE_TARGET_INVALIDでも最新化 | hooks.testの17件。未実装moduleでFAIL→17 PASS。各テスト1回のrenderHookWithProvidersで成功/409/404後のgetQueryDataと再取得回数を検証。本番Providersを使った400 POSTは1回（既定retry=1に対するhook設定の優先も検証） |
| SCR-03・件数/状態 | `components/ItemListPage.tsx` / `VersionSummary.tsx:8` / `ItemTable.tsx:28` / `ItemFilters.tsx`。h1は1つ、7件数と照合n/N、訂正行数、案件情報、網羅性文字、19列相当（判断3列はcolSpan=3内のフォーム）、担当者名はメモリのみ | components.test初回module FAIL→26 PASS。loading/404/明細空/絞り込み空/各読取エラー、7件数、長い数値/TBA/旧値、名前空POST0、判断済み未解決・案件枠を確認 |
| SCR-04・訂正/判断 | `components/EvidenceDrawer.tsx:46` / `EditForm.tsx:15` / `EditHistory.tsx` / `QuestionJudgementForm.tsx:11`。原表記・採用値・資料名/locator/quote/条件/変更理由を文字表示。前後はフィルタ後の順。訂正/照合取消/判断は明示操作。履歴は取消後も残す | 照合ON/OFFのconfirmationId、訂正取消後のundoneBy/At、前後端disabled、HTML/URL非リンク化、空根拠、11エラー種の翻訳と生message/detailsの否定をassert。納期/納地の読取専用表示は追加RED 1 FAIL / 24 PASS→25 PASS |
| AD-024⑥ 共有する長さ状態 | `components/ItemTable.tsx`。レンジと定尺長を常に併記し、共有状態ラベルを1つにする。数量の旧値と旧単位は別セル | 「レンジと定尺長は共有状態でも併記し状態ラベルは1つにする」が追加RED 1 FAIL / 25 PASS→26 PASS。rangeClass=R3・lengthState=not_statedでもレンジを隠さない |
| ルート・既存画面の導線 | appの薄いServer Componentが両IDを検査。CaseListPage.tsx:177,187は表示状態とlatestVersionIdリンク。RunProgress.tsx:50 / AgentRunPanel.tsx:185はGET確定版へのリンク。documents/index.tsから公開hook使用 | ルート/導線の初回3 FAIL / 69 PASS＋新ルートmodule FAIL→3 suites / 86 PASS。正整数/不正ID、latestVersionId=nullのリンク非表示、成功の完全/部分両方のリンク、失敗/停止で非表示を確認 |

## 既存テストの期待更新（AD-024⑭）

1. `CaseListPage.test.tsx`: 「版は後で表示／案件を開くリンクなし」という暫定期待を、作成案ラベル・確認者/日時は承認画面で記録の注記・`/cases/1/versions/1`リンクへ置換。送付承認ではない注記とh1=1は維持。null時リンク非表示を追加。
2. `AgentRunPanel.test.tsx`: 完全成功/部分成功の「次の段階／リンクなし」を、`/cases/8/versions/99`の「Item Listを確認する」へ置換。部分完了注記と失敗/停止でリンクが無い検査は維持。
3. `case-routes.test.tsx`: 既存案件/投入ルートの全assertを維持し、版ルートの正ID・両パラメータの不正ID検査を追加。

新しい共通fixtureを初め`__tests__/fixtures.ts`へ置いたところ、全体Jestがテストsuiteとして収集し「テスト0件」で失敗したため、`testing/fixtures.ts`へ移した。テストやassertを削って回避したものではない。

## 数値入力・設計判断の扱い

BEの`exact_decimal`（domain/draft_types.py:18）はPython Decimalで解釈できる有限の10進文字列または整数を受け付け、float/bool・NaN/Infinity・分数を拒否する。文字列は符号・小数点・指数表記を受理し、Python Decimalとして空白/桁区切りunderscore/Unicode十進数字も受理しうる。FEは前後空白をtrimし、ASCIIの符号・整数/小数・指数からなる10進文字列（例`4.500`、`.5`、`1e3`）を送り、数値化・丸めをしない。最終的な値/状態/範囲の判定はBEに委譲する。

03-specのうちG5/G6・SCR-05・item_ends・対象案件セレクタはAD-024の明示範囲外。原項番列、読取専用の版履歴、ドロワー内判断、primary無し、success時リンク、一部完了注記、APIが持つ16項目だけの訂正を採用した。納期・納地は根拠閲覧だけで編集不可。設計書の書き戻しはClaudeの担当。今回新たに判断待ちとなる設計不足はない。

## 変異・最終ゲート

[変異まとめ](test-results/item-review-mutations-2026-09-13.log)。共有作業ツリーを変更せず、.envと生成キャッシュを除いた一時frontendコピーごとにMake経由で実行。

| 変異 | 検出結果 |
|---|---|
| retry:falseを外す | 1 FAIL / 16 PASS |
| 修正理由のクライアント検査を外す | 1 FAIL / 30 PASS |
| 旧値で取消済みを除外しない | 1 FAIL / 30 PASS |
| TBAの優先を外す | 1 FAIL / 30 PASS |
| itemsのinvalidateを外す | 12 FAIL / 5 PASS |
| 状態のみの要求にもnewValueを入れる | 3 FAIL / 28 PASS |

```text
$ AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe
Test Suites: 19 passed, 19 total
Tests:       261 passed, 261 total
Time:        19.503 s
✅ check-fe: frontend green

$ make -f Makefile -f /tmp/item-review-checks.mk item-review-design
✓ design-lint: 違反なし
```

[最終FEゲート](test-results/item-review-regression-2026-09-13.log) / [design-lint](test-results/item-review-design-2026-09-13.log) / [API RED](test-results/item-review-api-red-2026-09-13.log) / [model RED](test-results/item-review-model-red-2026-09-13.log) / [hooks RED](test-results/item-review-hooks-red-2026-09-13.log) / [components RED](test-results/item-review-components-red-2026-09-13.log) / [導線 RED](test-results/item-review-routes-red-2026-09-13.log) / [長さ RED](test-results/item-review-length-red-2026-09-13.log) / [長さ・画面GREEN](test-results/item-review-length-green-2026-09-13.log)。OpenAPI/orval・tsc・eslintを含め除外なしで成功。

## ブラウザ証跡

`.env*`を除いたfrontendコピー・Next dev・Chromium、実生成クライアント＋HTTP fixtureで確認。APIはfixtureに閉じ、実DBジョブ・実モデルを呼ばない。h1=1、containedは一覧0/ドロワー1、390pxのページ横はみ出し0、pageerror=0。表は横スクロールし日本語を縦に1文字ずつ折り返さない。担当者名空POST0、明示照合POST1、フィルタ/ドロワー前後端/空/404も確認。サーバー・ブラウザは終了済み。

[ブラウザログ](test-results/item-review-browser-2026-09-13.log) / [一覧](test-results/item-review-ui/list.png) / [根拠](test-results/item-review-ui/evidence.png) / [訂正履歴](test-results/item-review-ui/history.png) / [絞り込み空](test-results/item-review-ui/filtered-empty.png) / [390px](test-results/item-review-ui/mobile.png) / [390pxドロワー](test-results/item-review-ui/mobile-evidence.png) / [明細空](test-results/item-review-ui/empty.png) / [404](test-results/item-review-ui/not-found.png)。画像8枚。

## 再レビュー依頼（T-303）

SCR-03/SCR-04と既存画面からの導線を提出します。全体FEゲート261件、指定変異6種、design-lint、ブラウザ確認が成功。commitはしていません。§7 10:40版で明示されたT-401へ続行します。
