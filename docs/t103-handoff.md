# T-103 引き継ぎ（2026-09-12・RV-019対応）

## 最新：RV-024短ラウンド（§7 2026-09-12 18:05への対応）

タスクGを完了。**`DEBUG=false CI=true make check-fe`は11スイート・78件PASS、design-lintは違反ゼロ。** 下部のRV-019対応・77件の結果は前回の履歴。今回の変更は両画面・翻訳・テストのみ。G2、Makefile、設計書、memoryは編集せず、開始時ハッシュ一致を確認した。commitなし。

| 指摘 | 変更内容（frontend/srcからの相対、ファイル:行） | RED・GREEN／実行コマンド・件数 |
|---|---|---|
| P2-1（必須） | `features/documents/components/IntakePage.tsx:69,161`：`E_LIMIT_EXCEEDED`をdetailsの解釈可否と独立に判定。未知limitでも上限超過の見出し・記録なしのhintを表示、具体的な数値文は既知detailsだけ表示 | `IntakePage.test.tsx:226`「413のlimitが未知でも上限超過と記録が残らない旨を案内する」を先に追加。`CI=true make fe-test`で当該テスト＋P3-3文言の **2 failed / 76 passed** を確認→全体78 passed。未知値の漏出・記録確認への誤誘導がないこともassert |
| P2-2 | コード変更不要、上限実数値の追従は既存TODO-001へ記録済み | Claude側対応済み。新規REDなし、上限数値の変更なし |
| P3-1 | `shared/i18n/ja.json`の未参照`cases.newCaseDialog.caseCodeRequired`を削除 | dead key整理のみ。参照0、全体78件PASS |
| P3-2 | `features/cases/components/CaseListPage.tsx:147,150,153,177,178`を`common.notAvailable`へ統一。`cases.notAvailable`を削除 | 表示値は同じ「—」。既存の案件・メタ表示テストを維持、全体78件PASS |
| P3-3 | `shared/i18n/ja.json:16`の版注記を「版の状態は案の作成後に表示します」へ | `CaseListPage.test.tsx:209`の利用者向け文言assertを新仕様へ変更してREDを実測（上記2 failedのうち1件）。修正後PASS。G3などの内部工程名を画面文言へ残さない |
| P3-5 | `features/documents/__tests__/api.test.ts:49`：HTTP415の同じPromiseに`rejects.toBeInstanceOf(ApiError)`とstatus/documentId検査を適用 | 旧`expect(ApiError).toBeDefined()`は返却例外を検査しないため置換。1回のHTTP応答・呼出し数1のassertを維持。正常コードでPASS、普通のErrorを返す変異でHTTP415と既存HTTP409の **2 failed / 76 passed** を検出 |
| P3-4 / P3-6 | 記録のみ | `E_UNEXPECTED_RESPONSE`をクライアント合成コードとして05 §6へ記載するかはClaude判断。file inputの外観はT-204のSCR-02改修と同時に扱う。今回は変更なし |

既存テストはP3-3の新しい表示仕様への更新とP3-5の検査強化のみ変更。テスト削除・否定ケースの撤去はない。未知limitのケースは追加した。413の既知4値・415の記録・partial表示・二重投入等は従来どおり全体ゲートで確認した。

### 実出力・変異確認

全ログ: [RED](test-results/g1-short-red-2026-09-12.log) / [FE全体](test-results/g1-short-regression-2026-09-12.log) / [変異](test-results/g1-short-mutations-2026-09-12.log)。

```text
$ CI=true make fe-test  # 修正前
Test Suites: 2 failed, 9 passed, 11 total
Tests:       2 failed, 76 passed, 78 total
Time:        4.026 s
make exit 2

$ DEBUG=false CI=true make check-fe  # 最終差分
OpenAPI schema exported to: openapi.json
orval: success
tsc --noEmit: PASS
eslint: 0 errors, 1 warning（未変更のorval.t202.config.ts）
Test Suites: 11 passed, 11 total
Tests:       78 passed, 78 total
Time:        3.482 s
✅ check-fe: frontend green
exit 0

$ node .claude/scripts/design-lint.mjs
✓ design-lint: 違反なし
exit 0

$ git diff --check
出力なし、exit 0
```

変異は`/tmp/rv024-mutations.py`が作成したコピーで`CI=true make fe-test FRONTEND=<隔離コピー>/frontend`を全体実行し、作業ツリーは変更しない。

- `limitExceeded ?`を旧`details ?`へ戻す → **1 failed / 77 passed**。未知limitの新規テストだけが失敗。
- mutatorがApiErrorではなく同じstatus/code/detailsを持つ普通のErrorをthrowする → **2 failed / 76 passed**。強化したHTTP415と既存HTTP409のinstanceof検査が失敗。

**再レビュー依頼。希望Status: T-103 REVIEWING（RV-024のDONE条件を修正済み）。** §0bの常駐ループに従い、§7見出しの`2026-09-12 18:05`が変わるまで作業ツリーを変更せず待機する。次タスクは推測して着手しない。

---

`docs/t103-instructions.md` の指示に基づき、SCR-01 案件一覧・SCR-02 資料投入を実装した。**最終 `DEBUG=false CI=true make check-fe` は11スイート・77件PASS、design-lintは違反ゼロ。** G2の修正は提出済みの状態から、ユーザーの明示指示でT-103へ着手した。独立レビューは未実施。

## 変更範囲

- `frontend/src/features/cases/`：API wrap・hooks・案件一覧／作成ダイアログ・案件メタ・公開index・テスト。
- `frontend/src/features/documents/`：API wrap・デバッグ出力削除・資料投入画面・公開index・テスト。
- `frontend/src/app/(portal)/cases/`、`src/app/page.tsx`：薄いServer Componentとトップのリダイレクト。
- `frontend/src/app/providers.tsx`、`shared/api/unwrap.ts`、`shared/theme/mui-color.ts`：POST自動再送停止・成功応答の型絞込み・MUI v5との色表現互換。
- `frontend/src/shared/i18n/ja.json`、`shared/testing/test-utils.tsx`、`src/app/__tests__/`、`shared/api/__tests__/`：翻訳・テストインフラ・本番Provider／ルートの検証。
- `frontend/package.json` / `package-lock.json`：`@types/jest`を29へ揃え、RTLが必要とするpeerの`@testing-library/dom`を明示。再生成される`frontend/tsconfig.tsbuildinfo`も更新される。
- 本handoffと`docs/test-results/g1-*`。Makefile・BEソース・migration・G2 handoff・設計書・トークン値・`orval.t202.config.ts` / `tsconfig.t202.json`は編集していない。`.claude/memory.md`は読取のみ。並行更新を検出したが編集・復元していない。

## レビュー対応表

パスは特記のないものは`frontend/src/`からの相対。RED実出力は [g1-red-2026-09-12.log](test-results/g1-red-2026-09-12.log)。未実装モジュールのREDは、assertまで実行できたREDと区別して記す。

| 指摘 | 変更内容（ファイル:行） | REDを確認したテスト・コマンド・件数／最終結果 |
|---|---|---|
| P1-1 | `features/documents/__tests__/hooks.test.tsx`・`components/__tests__/IntakePage.test.tsx:190`で413の4値を`file_size/document_count/pdf_pages/xlsx_sheets`に修正。BEは変更しない | `CI=true make fe-test`の元の4スイートは2 failed / 11 passed＋components未実装。4値はhooks・実HTTPクライアント・画面の各層で検証。契約に合うテストへの修正自体は既存hooksを失敗させない。画面のREDは未実装モジュール。最終4値すべてPASS、原識別子表示の変異は4 failed |
| P1-2 | `shared/i18n/ja.json:108`、`features/documents/components/IntakePage.tsx:166`：翻訳ラベル＋単位＋max/actual。未知のdetailsは内部値を露出せず再確認の案内 | `IntakePage: 413 %s は翻訳したラベル・単位・数値を表示する`4例。`CI=true make fe-test`で未実装モジュールのRED→全件PASS。ラベルを`details.limit`へ戻す変異を4例すべて検出 |
| P1-3 | `app/providers.tsx:151`：本番のmutation retryをfalseに | `app/__tests__/providers.test.tsx:11`「本番Providersの記録系POSTは自動再送しない」。本番Providerを使用。テーマ起動エラー修正後の`CI=true make fe-test`は1 failed / 33 passed、Expected false / Received 1。修正後PASS。retry=1変異で1 failed |
| P1-4 | `features/cases/components/CaseListPage.tsx:36,195`、`ja.json:16`：表示状態・送付可否は常に「—」＋AD-013注記 | `CaseListPage: AD-013: 進捗が案の確認でも…`と「版の暫定表示と評価確認が送付承認ではない旨…」。REDはcomponents未実装。最終PASS、ブラウザでも列分離と注記を確認 |
| P1-5 | `CaseListPage.tsx`の操作列は`/cases/{id}/intake`のみ。`cases.list.openButton`を削除 | `CaseListPage: 「投入画面へ」導線がある`。旧テストの誤ったラベルをAD-013に合わせた。未実装RED→PASS、ブラウザの案件作成後の遷移も確認 |
| P2-1 | `features/documents/hooks.ts:40`：console.logとログ用thenを削除。invalidate条件・返すPromiseは維持 | ログ削除は動作変更なし、新規REDなし。元の実行ログにDEBUG出力があったことを確認。最終77件PASS |
| P2-2 | 両featureの`__tests__/hooks.test.tsx`でlistとmutationを単一renderHookにまとめる。`shared/testing/test-utils.tsx:8`に理由 | 変更前`CI=true make fe-test`で「作成成功後に一覧が再取得される」「415…一覧が再取得される」の2 failed / 11 passedを再現。テストインフラだけを直した時点で既存hooksはPASS。invalidateの実装を失敗に合わせて変更していない |
| P2-3 | `shared/api/unwrap.ts:6`にstatus照合と型絞込みを集約。`cases/api.ts:20,25,32`・`documents/api.ts:16,23`が利用 | `make fe-type`で8エラー（成功union混在・未実装・fixture型）。unwrapテストは未作成モジュールのRED。最終全体tsc PASS。200/201/202/204と404/413/415/422/500の9ケース、実生成クライアント＋fetch応答の8ケースもPASS |
| P2-4 | CaseListPage/IntakePageのテストを`new ApiError(status, body)`へ修正 | 既存のError偽装はinstanceof契約を再現しないため変更。未実装RED→409/413/415画面テストPASS。UIの例外判別もApiErrorを使用 |
| P2-5 | `shared/i18n/ja.json:14`：「対外送付の承認ではありません」を追加 | `CaseListPage.test.tsx:205`の明示文言assert。未実装RED→PASS、ブラウザ表示も確認 |
| P2-6 | components作成前にSCR-02の上限・実読取・案件メタ・例外例示・二重投入・表見出しのi18nを追加 | `IntakePage.test.tsx:257`・`CaseMetadata.test.tsx`。未実装RED→PASS。単一h1、必要な注記、未提供値を推測しない表示を固定 |
| P2-7 | `frontend/package.json:38`：`@types/jest`を29.5.14へ。RTLのpeer `@testing-library/dom`も明示 | 依存整合のため新規機能REDなし。旧メジャー30を確認。インストール後の全体tsc・Jest77件PASS。型エラーを専用tsconfigで除外していない |
| P2-8 | 指示どおり`orval.t202.config.ts` / `tsconfig.t202.json`は残す | C-1へ持越し。全体eslintは同orval設定に既存警告1件、エラー0。警告を隠す設定変更なし |
| P3-1 / P3-2 | `cases/hooks.ts:17,19`：CreateCaseInputを前方宣言、casesQueryKeyを関数へ統一 | 型・表現の整理で新規REDなし。キャッシュの値は従来どおり`["cases"]`、全体hooksテストPASS |
| P3-3 | `shared/testing/test-utils.tsx:8`：ThemeProvider未使用の検証限界を明記 | コメントだけの変更。下記の本番テーマ統合テストを別途追加し、実際の起動不具合も検出 |
| P3-4 | 既存の日本語直値assertは5区分・利用者向け文言の固定が目的とコメント。新規キーはi18n.t併用 | 既存のassertは消さない。最終画面テストPASS |
| P3-5 | `IntakePage.tsx`の暗号化注記・i18n：AD-006で当面は読取不能に入る旨を表示 | 5区分のテストを維持。encryptedを消さず、現行処理で到達しない理由を明示 |
| 未完成1〜9 | 両components・公開index・薄いServer Component・トップredirectを追加。3状態、進捗4段、案件作成、ファイル投入を実装 | components/metadata/routesは未作成モジュールのRED。`case-routes.test.tsx`8例、両画面・案件メタの検証が最終PASS。空状態は次の操作へ誘導、エラーは対処を表示 |
| 追加検出：本番テーマ | `app/providers.tsx:25,45`・`shared/theme/mui-color.ts:6`：oklch状態色のcontrastText明示、dividerのcolor-mixを同値rgbaに変換 | 本番Provider初期化でoklch例外を再現。次に実ブラウザでTableCellのcolor-mix例外を再現し、`screen-theme.test.tsx:45`を追加。`CI=true make fe-test`で2 failed / 74 passedを確認→修正後77 passed。元の色・透明度の一致も検証し、divider変異で再発を検出 |

## 既存テストを変更した理由

- `fileSizeMb`はBE契約に存在しない。snake_caseの4値を各層へ展開し、期待する日本語ラベル・単位も固定した。BE契約の変更はしていない。
- 複数Reactルートによる不安定な`result.current`観察を、単一ルートのlist/mutationに変更した。415だけのinvalidate条件を維持する。初回2件のREDは修正前ログに保存した。
- `Object.assign(new Error(), ...)`と一般ErrorをApiErrorへ変更し、fixtureのreadStatusに生成型を明示した。テスト専用の偽の例外判定へ実装を寄せていない。
- 「案件を開く」を「投入画面へ」に変更し、「版がないときだけ—」というテスト名もAD-013の常時表示へ訂正した。
- 今回追加した連打テスト2例は、最初にヘルパーが返す別mockを誤って観察して失敗したため、渡したmutation mockそのものを観察するよう修正した。実装を変更して通したものではない。
- テストの削除なし。agent/BEの既存テストも編集していない。

## APIと画面の接続

生成クライアント→`api.ts`→hooks→componentsの向きを維持する。非2xxは既存mutatorのApiError、成功は共通unwrapを通る。HTTP相当のfetch応答を使い、200一覧／詳細・201作成／multipart投入・409・413全4値・415を実際の生成クライアント経由で検証した。これはBEサーバ実接続ではなく、FEのHTTP境界テストである。

- `/` → `/cases`。案件作成201のcaseIdで`/cases/{caseId}/intake`へ移動。
- 案件メタは既存#3 GETを使用。feature間参照はcasesの公開index経由。
- 415は一覧をinvalidateし、記録済みと案内する。413はinvalidateせず、記録が残らないことを案内。
- 送信中は入力／送信を無効化し、同期refでも二重送信を防止。投入完了後にfile inputを空に戻し、同じファイルの明示的な再投入は可能。
- 再送は自動で行わない。通信失敗時は一覧で記録を確認してから再操作する案内を出す。
- 3状態と5つの読取ラベルを保持。色は状態文字の補助のみ。

## 設計との対応・未提供情報

新たな業務仕様は追加していない。以下は既存APIが提供しないため、UIで推測した値や固定サンプルを埋めなかった箇所であり、設計書/APIの後続整理時に確認する。

| モック／仕様の要素 | 今回の扱いと根拠 |
|---|---|
| SCR-01の中央テーブル・見出し右のprimary・4段メーター・下部注記 | 同じ構成。識別列は実案件の照会番号。表示状態と送付可否はAD-013どおり—。明細件数・未解決数・差し戻し情報は#1にないため、明細件数は—＋注記、他の数値は捏造しない |
| SCR-02の冒頭バナー・左の案件情報・右の投入と一覧・例外開閉 | 同じ配置。狭い画面では縦配置。トークンの白面・ヘアライン・鋼色と既存文字スケールを使用 |
| デモ案件セレクタ | AD-008/009に合わせ、一覧で実案件を選んで対象URLへ遷移。デモ資料を実案件と混在させない |
| 納期・納地・見積期限 | #3が返すのは照会番号・客先名・件名等のみ。3項目は—＋「現在の案件情報では未提供」の注記。抽出値APIの追加は今回行わない |
| 原資料名・形式・ページ／シート数 | #4が返す原資料名・形式を受付一覧へ表示。件数情報は未提供と注記する |
| 固定サンプル生成・版の注記・記録引継ぎ・処理段階 | T-204のエージェント起動／ポーリング／版生成に属するため追加しない |
| 本文テキスト欄 | モック専用の受付イメージであり、現行#5はmultipartのfileを受ける。保存できないテキスト欄を作らず、TXT／EML等を実投入する |
| 仮上限 | モックの5ファイル/10MBから、AD-003の50資料/20MB/PDF200ページ/xlsx50シートへ。D02未確定注記あり |
| 例外表示例 | 実際の受付一覧とは分け、例示であり選択ファイルの判定ではないと明記 |

primary塗りボタンは一覧で1つ、ダイアログが開くと背景側をoutlinedにし送信だけ塗りにする。資料投入画面は塗りボタンなし。各画面h1は1つ。デザイントークンの値は変更せず、MUI v5のJS演算境界だけで同値の色表記へ変換した。

ブラウザ画像: [案件一覧](test-results/g1-ui/case-list-desktop.png) / [資料投入](test-results/g1-ui/intake-desktop.png) / [狭い画面](test-results/g1-ui/intake-mobile.png)。Chromiumで1440pxと390pxを確認。起動したNext.jsとHTTP応答fixtureは隔離コピー上で動かし、実DBへの書込みはない。案件作成→投入・同一ファイル2行・partial・415一回・413具体表示・h1一個・横はみ出しなし・pageerrorなしを確認した。415/413に対応するブラウザconsoleのHTTPエラー表示は想定どおり。

## 再生成・並行作業の保全

- 通常の`make check-fe`で正規OpenAPI→orval全体再生成を実施。専用tsconfig・隔離exporter・生成ファイルの手編集・`clean: false`化は行わない。
- `clean: true`による再生成では、旧余剰型`shared/api/generated/model/itemsCreatedRejectedItem.ts`と`validationResponseCounts.ts`が消えた。正規スキーマでは`ItemsCreated.rejected`は上限0の`unknown[]`、`ValidationResponse.counts`は`ValidationCounts`参照になるため、旧2型は生成されない。feature/app/生成index/ui/agentに旧2型への参照は0、全体tscもPASS。cases/documentsの生成物は維持される。G2の元スキーマは変更していない。
- BEと既存設計書・G2 handoff・Makefileの開始時ハッシュを照合し、変更なしを確認。memoryとCODEX-INSTRUCTIONS.mdの別セッションによる更新を検出したが、そのまま保全した。更新後の§7（17:10）も読み、T-103完了後は再レビュー依頼で止まる指示に変更がないことを確認した。G2のcommitは別セッションによるもので、こちらからcommit操作はしていない。
- 実DBへのmigration適用・BE回帰・エージェント評価・C-1の整理・T-204・commit/pushは今回実施していない。

## 最終ゲート

全ログ: [FE全体](test-results/g1-frontend-regression-2026-09-12.log) / [design-lint](test-results/g1-design-lint-2026-09-12.log) / [ブラウザ確認](test-results/g1-browser-2026-09-12.log)。

```text
$ DEBUG=false CI=true make check-fe
OpenAPI schema exported to: openapi.json
orval v8.30.0: api - Your OpenAPI spec has been converted into ready to use orval!
tsc --noEmit: PASS
eslint: 0 errors, 1 warning（未変更のorval.t202.config.ts）
Test Suites: 11 passed, 11 total
Tests:       77 passed, 77 total
Time:        3.507 s
✅ check-fe: frontend green
exit 0

$ node .claude/scripts/design-lint.mjs
✓ design-lint: 違反なし
exit 0

$ git diff --check
出力なし、exit 0
```

## 変異による強度確認

ソースを一時コピーしnode_modulesだけ共有、各変異を独立に適用して`CI=true make fe-test FRONTEND=<隔離コピー>/frontend`を全体実行した。共有作業ツリーの実装は書換えない。実行スクリプトは`/tmp/t103-mutations.py`、ブラウザ補助検証は`make -f Makefile -f /tmp/t103-browser.mk fe-browser`。いずれも上記の通常全体ゲートの代用にはしない。


全結果: [g1-mutations-2026-09-12.log](test-results/g1-mutations-2026-09-12.log)。正常コピーは77 passed / exit 0。以下の7種類すべてで意図したassertが失敗した（各make exit 2、pytestではなくJestの失敗）。

| 変異 | 検出結果 |
|---|---|
| dividerを元のcolor-mixのままMUIへ渡す | 2 failed / 75 passed |
| mutation retryを1へ戻す | 1 failed / 76 passed |
| 翻訳ラベルを内部識別子へ戻す | 4 failed / 73 passed |
| partialをsuccessラベルとして描画 | 1 failed / 76 passed |
| 415のinvalidateを止める | 1 failed / 76 passed |
| 413でもinvalidateする | 4 failed / 73 passed |
| file inputを空に戻さない | 1 failed / 76 passed |

## 提出状態

**再レビュー依頼。希望Status: T-103 REVIEWING。** 指示された実装とFE全体ゲートを完了し、独立レビューを待つ。memory更新とDONE判定はClaude担当。C-1・T-204・G3へは進まず、ここで停止する。


## 常駐ループの提出状態（RV-024対応後）

**再レビュー依頼。希望Status: T-103 REVIEWING。** 最新結果は冒頭の78件PASS。§7の更新時刻（現在18:05）が変わるまで待機し、変更後に再読する。memory編集・commit・次タスクの先取りは行わない。
