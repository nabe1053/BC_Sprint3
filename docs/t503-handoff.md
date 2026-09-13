# T-503 handoff

## 変更予定ファイル（着手前）

- 本体: frontend/src/features/versions/{api.ts,model.ts,hooks.ts,index.ts,testing/fixtures.ts}、新規components/{ApprovalPage,ApprovalSummaryCard,ReviewCheckPanel,SendoffPanel,ApprovalFilters,ApprovalTable,BounceCommentCell,ApprovalListsDrawer,StaffCheckAction,BounceBanner}.tsx、approval/page.tsx。
- 共有: components/{ItemListPage,EvidenceDrawer,EditHistory}.tsx、features/cases/components/CaseListPage.tsx、shared/i18n/ja.json。EditHistoryはreadOnly時の取消非表示のためprop追加。
- テスト: versions/__tests__/approval-{api,model,hooks,components}.test.* を新規。既存versions/components、cases/CaseListPage、case-routesを期待追従し、理由を記録。
- 文書: 本handoff・docs/test-results/approval-ui/。backend/generatedの手編集なし、memory編集・commitなし。

## 前提と実契約

T-502/T-601独立レビュー済み。指示書のcommit済み前提はユーザーのcommit禁止を優先し、既レビューの作業ツリーと直近make check（BE786/FE327）を基準とする。backendの既存未commit差分は保全し、T-503着手時ハッシュ `/tmp/approval-ui-protected.json` で変更なしを検証する。

#28は7配列、#22は13キー（latestBounce.comments=[]）。#36の実生成応答はBounceCreatedRecord（commentsなし）、取得#28/#22のBounceRecordと異なる。T-502で確定済みの契約を使用する。

入力検証の優先順は確認者名→コメント/未紐付け件数、判断者名→送付理由。i18n表のmetaは文字列と子キーの同居が不可能なため、meta.line/meta.recorded/meta.unrecordedへ配置する（文言不変）。

Status: 独立レビュー第3回でP1/P2/P3各0・DONE可。実装・検証完了。memory未転記・未commit（ユーザー指示）。

## 実装範囲の確定と契約補足

上記に加え、同featureの `components/ApprovalError.tsx` を共用エラー表示として追加（SCR-03・評価確認・送付判断の3箇所）。`src/app/__tests__/case-routes.test.tsx` は承認routeの正常/不正ID検査を追記。T-502追従の追加修正は不要だった（着手時型検査green、CaseListItem fixtureはT-502で追従済み）。既存未commitのcases/hooks.test.tsxの1行はT-502差分でT-503は変更していない。

`ja.json` は指示書の全句を敬体で保持。metaの子キー化以外、指示文言の省略なし。ケース一覧の送付可否見出しは既存 `cases.list.columns.sendoff` を使用。未解決述語は既存filterItemsから `unresolvedQuestions` の呼出しへ機械的に集約し、両者の結果一致をテスト。

承認fixtureは数量TBA・択一・継承候補・材質K55→L80訂正・判断済み未解決1件＋案件レベル未解決1件。現在値と訂正履歴の整合を保ち、件数を同じ定義で計算。実業務資料は使用していない。

## 生成関数名の確認

`shared/api/generated/ui.ts` に以下を確認。`make check-fe`で再生成した同名関数をapi.tsで呼ぶ。#1/#22は既存wrapperを利用し、生成ファイル手編集なし。

| # | 実生成関数 | unwrap |
|---|---|---|
| 28 | listRecordsApiV1UiVersionsVersionIdRecordsGet | 200、RecordsResponseの7配列をそのまま |
| 34 | recordStateEventApiV1UiVersionsVersionIdStateEventsPost | 201、StateEventRecord |
| 35 | recordBounceCommentApiV1UiVersionsVersionIdBounceCommentsPost | 201、BounceCommentRecord |
| 36 | recordBounceApiV1UiVersionsVersionIdBouncesPost | 201、BounceCreatedRecord（commentsなし） |
| 37 | recordSendoffDecisionApiV1UiVersionsVersionIdSendoffDecisionsPost | 201、SendoffDecisionRecord |

型参照の着手時 `rg -n 'VersionListItem|CaseListItem' frontend/src --glob '*.ts' --glob '*.tsx' --glob '!**/generated/**'` 出力は `docs/test-results/approval-ui-type-uses-2026-09-13.log`。

## AD-031 25決定の対応

api.ts/model.ts/hooks.tsおよびcomponents配下は `frontend/src/features/versions/` 相対。他パスは `frontend/src/` 相対。

| 決定 | 反映箇所 | 検証 |
|---|---|---|
| ① feature再利用 | features/versions/{api,model,hooks,index}.ts | 新featureなし、既存基盤・ItemValue・EvidenceDrawer利用 |
| ② 3画面 | components/ApprovalPage.tsx:37、ItemListPage.tsx:145、features/cases/components/CaseListPage.tsx:184 | SCR-06、SCR-03遷移/バナー、SCR-01送付列 |
| ③ SCR-04コメント対象外 | ItemListPage.tsx:45、BounceBanner.tsx:6 | SCR-03は#22のみ、#28を呼ばないassert |
| ④ ルート | app/(portal)/cases/[caseId]/versions/[versionId]/approval/page.tsx:1 | 薄いServer、正整数2ID、公開featureへ |
| ⑤ primary | ReviewCheckPanel.tsx:7、StaffCheckAction.tsx:13 | SCR-06=1、SCR-03draft=1/他=0、実ブラウザ確認 |
| ⑥ 7要約 | model.ts:272、ApprovalSummaryCard.tsx:7 | #23/#22/#28を指定通り利用、未紐付けコメント件数 |
| ⑦ メタ3項目 | model.ts:291、ApprovalPage.tsx:37 | 最新staff/review、未取消coverage、未記録 |
| ⑧ 版一覧 | model.ts:268、ApprovalPage.tsx:37、ItemListPage.tsx:45 | 既存useVersionHistoryを共用、不在は取得失敗 |
| ⑨ 行コメント | BounceCommentCell.tsx:7、ApprovalPage.tsx:37 | 明示POST、成功時入力クリア、応答後一覧、blur送信なし |
| ⑩ 差し戻し | model.ts:380、ApprovalPage.tsx:37 | 名前→未紐付け数検査、bodyはrecordedByだけ、成功SCR-03 |
| ⑪ 評価確認 | model.ts:364、ApprovalPage.tsx:37 | review_checked、画面に留まりstatus、未解決件数を表示 |
| ⑫ 有効条件 | model.ts:402、ReviewCheckPanel.tsx:7 | draft/review_checkedは両ボタン無効・注記 |
| ⑬ 送付可否 | model.ts:388、SendoffPanel.tsx:13 | 独立記録、理由/判断者検査、undecided空理由=null、任意状態 |
| ⑭ 記録者2欄 | ApprovalPage.tsx:37、SendoffPanel.tsx:13 | 確認者名と判断者名は別state、初期空、永続化なし |
| ⑮ 索引Drawer | ApprovalListsDrawer.tsx:16、ApprovalTable.tsx:23 | 全行/行、案件レベル注記、根拠リンク、0行ボタン、排他state |
| ⑯ 変更タグ | model.ts:312、:329 | 5タグ、未取消・最新判断、未解決述語を共用 |
| ⑰ 根拠readOnly | EvidenceDrawer.tsx:46、EditHistory.tsx:7 | 照合/訂正/取消/判断操作を非表示、読取部分は保持 |
| ⑱ 5絞り込み | model.ts:339、ApprovalFilters.tsx:6 | 表のshown/total、索引数不変を5パターン検査 |
| ⑲ 10列 | ApprovalTable.tsx:23 | 数値文字列を保持、現在値と履歴を別欄、状態別表示 |
| ⑳ トーン | ApprovalSummaryCard.tsx:7、model.ts:441、ApprovalTable.tsx:23 | ok/warn/中立、dangerなし、入力欄aria-invalid |
| ㉑ hooks | hooks.ts:55、:158、:166 | 4mutation、records/version/versions(caseId)だけ再取得、retry:false |
| ㉒ エラー | model.ts:420、:425、ApprovalError.tsx:7 | 新7コード＋既存recorder、fallback、内部itemID非表示 |
| ㉓ 日時 | 各表示でrecordedAt文字列をそのまま | FE側の変換/丸めなし、書式統一はC-3 |
| ㉔ 案件送付列 | features/cases/components/CaseListPage.tsx:184 | undecided/hold/approved/nullの4検査、#1以外の導出なし |
| ㉕ 既存テスト | versions/__tests__/components.test.tsx、case-routes.test.tsx、cases/components/__tests__/CaseListPage.test.tsx | 既存期待の理由付き追従、削除/弱化なし |

## レビュー対応・TDD証跡

全実行はルートMakefile入口。高速確認の接頭辞は `AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/approval-ui-checks.mk`。正式ゲートは `make check-fe`。pytestとの同時実行なし。

| 項目 | 主変更 | RED→GREEN | 変異 |
|---|---|---|---|
| API5関数 | api.ts:126 | approval-ui-api: 10 failed→10 passed | 実fetchのURL/method/body/statusをassert |
| 純粋モデル | model.ts:268 | approval-ui-model: 16 failed→16 passed | 名前、未紐付け0、hold理由、取消メタ、inherit、内部IDを各検出 |
| hooks | hooks.ts:55 | approval-ui-hooks: 17 failed→17 passed | retry削除1失敗、versions invalidate削除16失敗 |
| 新画面 | ApprovalPage等 | approval-ui-components: モジュール不存在でsuite失敗→11 passed、補強後18 passed | readOnly解除1失敗、入力上の行クリック誤動作1失敗 |
| SCR-03/01 | StaffCheckAction/BounceBanner/CaseListPage | approval-ui-screens: 6 failed/47 passed→54 passed（既存部品検査＋追加分） | 実mutateAsync要求・遷移先・実表示をassert |
| aria-invalid | BounceCommentCell/StaffCheckAction/ItemListPage | コメント欄1 failed/17 passed、担当者欄1 failed/53 passed→18/54 passed | input属性を実DOMでassert |
| route | approval/page.tsx | 既存route方式を拡張、26 passed（追加6） | 不正ID5値を両引数で検査 |

変異は隔離コピー内のみ。10種すべて検出。`versions-invalidation`の初回は対象文字列が2箇所あるため変異ハーネスの一意性検査で停止し、invalidate側に限定して再開（その時点でソースは未変異）。検出成功分を重複実行せず記録。全文 `docs/test-results/approval-ui-mutations-2026-09-13.log`。

既存テスト変更理由:

- ItemListのprimary期待0→1はAD-031⑤のdraft時ボタン追加。非draftの0も別にassert。
- 版一覧で現在版が見つからない場合はAD-031⑧により取得失敗へ。元のVersionHistory部品の「空と取得失敗を区別する」検査は対象を部品自身へ移して維持し、ItemList側の取得失敗テストを追加。
- ItemListの共用hook mockにuseApprovalMutationsとrouterを追加。過去の表示・記録assertは維持。
- ケース一覧とrouteは検査追加のみ。T-502で必要になったlatestSendoff:nullの既存fixture行は維持。

## 実ブラウザ・デザイン証跡

隔離Next.js＋合成API応答で検証。ドライバは一時ディレクトリだけに置き、リポジトリに残さない。実DB/実LLMを使用しない。

`make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-browser` の最終結果: **12 screenshots、h1=1、SCR-06 contained=1、10列、390pxのscrollWidth=390、pageerror=0**。POSTは行コメント/差し戻し/評価確認/送付判断が各1回、採時は要求に含めない。SCR-03への遷移と差し戻し表示、SCR-01送付列、loading/empty/error/404も確認。新規記録がサーバ応答のメタで表示されることを確認。

初回のブラウザ確認は送付selectのアクセシブル名の完全一致で停止した。実DOMはMUIのlabel＋選択中値を含むため、検証側のlocatorを見出し部分へ合わせて再実行し全成功。製品側ラベルを弱めたり外したりしていない。

画像: [通常](test-results/approval-ui/overview.png)、[行索引](test-results/approval-ui/row-index.png)、[閲覧専用根拠](test-results/approval-ui/read-only-evidence.png)、[差し戻し後SCR-03](test-results/approval-ui/bounced-item-list.png)、[評価確認後](test-results/approval-ui/reviewed.png)、[送付判断](test-results/approval-ui/sendoff.png)、[SCR-01](test-results/approval-ui/case-list.png)、[390px](test-results/approval-ui/mobile.png)、[読込](test-results/approval-ui/loading.png)、[空](test-results/approval-ui/empty.png)、[エラー](test-results/approval-ui/error.png)、[404](test-results/approval-ui/not-found.png)。

`approval-ui-design`: design-lint違反0。画像も目視確認し、3領域→メタ→注記→絞り込み/索引→横スクロール表→表下注記の順、狭い幅では縦配置を確認。


## 最終品質ゲート・保護確認

`AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-design check-fe`。実出力末尾:

```text

Test Suites: 28 passed, 28 total
Tests:       402 passed, 402 total
Snapshots:   0 total
Time:        27.24 s
Ran all test suites.
✅ check-fe: frontend green
```

全文: `docs/test-results/approval-ui-final-check-fe-2026-09-13.log`。FEはT-502/T-601基準327から75増加して402。OpenAPI/orval、全体型検査、eslint/prettier、Jest28 suitesが成功。

バックエンド保護ハッシュ214件は全一致。既存未commitのT-501/T-502/T-601差分があるため `git status --short -- backend` 自体は空ではないが、T-503由来の変更は0件。ユーザーの保全指示に従い既存差分を削除しない。memoryは読取のみ、git add/commitなし。

## 次スライスへ渡す契約

ApprovalPageをversions/index.tsから公開。SCR-03の版一覧/記録者入力はG5導線を追加済み。G6の出力ボタンや版履歴のelapsedSecは未追加でT-603対象。`useApprovalMutations(caseId,versionId)`は4種を公開、`recordsKey`と既存版/版一覧キーを共用。readOnly根拠ドロワーは記録用callback省略可、callbackが渡されても操作を表示しない。T-602はBE/APIの次スライスとしてT-601の契約を使用する。

## 転記案（未適用）

希望Statusは独立レビュー後に確定する。memory/commit禁止を継続。学び候補: MUI selectの実ブラウザaccessible nameは選択値を含むことがあるためDOMを確認して検証する。入力必須エラーは文言に加えてaria-invalidを実DOMで確認する。

## 再レビュー依頼（T-503）

AD-031の25決定、3画面の導線、readonly境界、記録後再取得と二重送信防止、実ブラウザ証跡を独立確認してください。402 tests / 28 suites成功、design-lint0、10変異検出、backend214ハッシュ不変。既レビューのBE差分を混同せず、memory編集・commit禁止を継続。

## 独立レビュー（2026-09-13）

RV候補: T-503 独立レビュー。P1 0 / P2 2 / P3 0。DONE不可。
RV候補: 訂正後の版一覧再取得が無く再確認バナーが更新されない点と、索引の変更・判断事項に理由・判断内容が無い点を要修正。
RV候補: 独立 make check は BE786 / FE402・28 suites 成功。FE259 / BE214ファイルのハッシュ一致。memory・コード・git indexは変更なし。

### 指摘

- **P2-1 — 訂正後に SCR-03 の「再確認が必要」が更新されない。** `frontend/src/features/versions/components/ItemListPage.tsx:45` で取得した #22 の `listItem` を同ファイル:172 の `BounceBanner` が表示するが、訂正は従来の `useRecordMutations(versionId)`（:49）を呼び、`frontend/src/features/versions/hooks.ts:81` の版一覧 invalidate は `resource === "approvals"` に限られる。`useRecordMutations` の edit は :106 で `"items"` を渡すだけなので、評価確認済み版で訂正を保存しても #23 の状態は担当者確認済みに変わる一方、#22 の `needsRecheck=false` が残る。ページ再読込等まで再確認バナーが出ない。`docs/requirements/03-spec.md:445` と AD-031②の「訂正が記録されると再確認が必要を表示」を満たすため、SCR-03 の訂正成功後に既存 #22 を再取得すること。FEで導出を複製せず、承認mutationの㉑の再取得範囲も保つ。回帰検査は初期 #22=false → 訂正成功 → #22=true の応答更新を同一マウントで通し、バナーが現れることを確認する。現在の `components.test.tsx:614` 付近のバナーテストは最初から true のmockで、保存後の経路を検査していない。
- **P2-2 — 索引の「変更・判断事項」に確認事項の理由・判断内容が表示されない。** `frontend/src/features/versions/components/ApprovalListsDrawer.tsx:121` から :144 は行コードと5種のタグだけを描画し、`question.reason` / `question.latest.note` を表示しない。`docs/requirements/03-spec.md:410` は同一覧に「確認事項の理由と判断内容を1行で併記」を要求する。判断が解決済みだと未解決一覧（:36）からも外れるため、上司が行索引または全行索引を開いても判断の内容を確認できない。既存 #26 の当該行の確認事項から理由・最新判断内容を読取専用で併記すること。解決済みかつ note ありの質問を使い、変更・判断事項欄内に理由と判断内容が見える回帰検査が必要。`row-index.png` でも同欄がタグのみであることを確認した。

P1・P3: 今回の対象差分では追加指摘なし。P2-1は今回新設のバナーとの結線、P2-2は既定設計の表示内容に関する指摘であり、AD-031の決定変更やBE改修を求めるものではない。

### AD-031 25決定の独立照合

以下で `versions/` は `frontend/src/features/versions/`、`src/` は `frontend/src/` を表す。

| 決定 | 独立確認した file:line | 結果 |
|---|---|---|
| ① | versions/index.ts:5、versions/api.ts:126、versions/hooks.ts:166 | 既存versions featureへ追加し公開。既存基盤を再利用 |
| ② | versions/components/ApprovalPage.tsx:37、ItemListPage.tsx:144、src/features/cases/components/CaseListPage.tsx:180 | 3画面を実装。ただし訂正後の再確認表示にP2-1 |
| ③ | versions/components/ItemListPage.tsx:45、BounceBanner.tsx:21 | SCR-03は#22理由を引用。#28の取得なし。SCR-04コメントは対象外を維持 |
| ④ | src/app/(portal)/cases/[caseId]/versions/[versionId]/approval/page.tsx:1 | 薄いServer Component。ID検証とkey付き公開feature |
| ⑤ | versions/components/ReviewCheckPanel.tsx:59、StaffCheckAction.tsx:53 | SCR-06 primary1、SCR-03 draftのみprimary1、他はtext導線 |
| ⑥ | versions/model.ts:272、components/ApprovalSummaryCard.tsx:13 | 7値の取得元一致。未紐付けコメント件数と送付記録なしを区別 |
| ⑦ | versions/model.ts:291、components/ApprovalPage.tsx:225 | 最新staff/review・未取消coverage。名前/日時と未記録表示 |
| ⑧ | versions/model.ts:268、components/ApprovalPage.tsx:65、ItemListPage.tsx:117 | 既存版一覧をfind。該当なしは取得失敗で操作非表示 |
| ⑨ | versions/components/BounceCommentCell.tsx:24、ApprovalPage.tsx:294 | 明示POST、成功時だけクリア、未紐付け履歴メタ列挙、取消なし |
| ⑩ | versions/model.ts:380、components/ApprovalPage.tsx:204 | 名前→未紐付け件数検査、recordedByだけ送信、成功SCR-03へ |
| ⑪ | versions/components/ApprovalPage.tsx:190、:268 | review_checked送信、画面に留まり未解決件数付きstatus |
| ⑫ | versions/model.ts:402、components/ReviewCheckPanel.tsx:61、ApprovalPage.tsx:236 | draft/review_checked両操作disabled、理由と照合内訳・導線 |
| ⑬ | versions/model.ts:388、components/SendoffPanel.tsx:36 | 3判断、判断者/理由検査、空理由null、状態による記録制限なし |
| ⑭ | versions/components/ApprovalPage.tsx:52、SendoffPanel.tsx:31 | 別stateの空名2欄、SCR-03とは非共有、永続化なし |
| ⑮ | versions/components/ApprovalListsDrawer.tsx:32、ApprovalTable.tsx:84 | 全行/行の読取専用Drawer・入力除外・案件レベル注記・根拠導線あり。設計の内容不足はP2-2 |
| ⑯ | versions/model.ts:312、:329 | 5タグ、未取消訂正、最新判断、共通未解決述語。変更採用タグなし |
| ⑰ | versions/components/ApprovalPage.tsx:317、EvidenceDrawer.tsx:255、:281、:295、:305 | readOnly時に照合/訂正/取消/判断操作を非表示。閲覧系維持 |
| ⑱ | versions/model.ts:339、components/ApprovalFilters.tsx:39、ApprovalPage.tsx:274 | 5絞り込みとshown/total。索引件数は全行から算出 |
| ⑲ | versions/components/ApprovalTable.tsx:58、:117、:165、:187 | 10列、寸法/数量文字列保持、訂正前後/理由、判断状態/内容、明示コメント |
| ⑳ | versions/model.ts:441、components/ApprovalSummaryCard.tsx:13、ApprovalTable.tsx:108 | ok/warn/中立と文字ラベル。danger追加なし、入力aria-invalid |
| ㉑ | versions/hooks.ts:57、:90、:158、:166 | 4承認mutationはrecords/version/versionsだけinvalidate、retry:false。訂正経路の不足はP2-1に分離 |
| ㉒ | versions/model.ts:411、:420、:425、components/ApprovalError.tsx:22 | 新7コード＋既存recorderの専用文言、既存fallback、行IDだけ抽出 |
| ㉓ | versions/components/ApprovalPage.tsx:99、BounceCommentCell.tsx:57、SendoffPanel.tsx:115 | recordedAt応答文字列をそのまま表示 |
| ㉔ | src/features/cases/components/CaseListPage.tsx:184 | #1 latestSendoffの3値/nullを承認/保留/未判断/—へ。差し戻し補足なし |
| ㉕ | versions/__tests__/components.test.tsx:151、:442、src/app/__tests__/case-routes.test.tsx、src/features/cases/components/__tests__/CaseListPage.test.tsx:259 | primary期待と版履歴テストの移動理由は妥当。既存検査の削除・弱化なし。cases/hooks既存1行はT-502として除外 |

### 検証と限界

依存は薄いroute→公開feature→components/hooks→api→生成client。新規modelの型import以外にUI依存なし。shared→feature逆依存なし。生成コードの手編集、HTTP本文や内部item IDの直接表示、HTML/URLの自動リンク化、外部送信の追加なし。readOnlyはcallbackが渡っても操作を隠す否定assertがある。各記録入口はrefの同期ロックとpending/disabledを持ち、mutation retry:falseも本番Providersで検査している。

REDログはAPI10失敗、model16失敗、hooks17失敗、componentsモジュール未実装のsuite失敗、既存画面追加6失敗を確認。API検査は生成clientを通ったfetchのURL/method/body/応答をassertし、hooksは同一QueryClientの更新後データをassert。既存テスト置換は期待される仕様変更に対応し、元の版履歴の空/エラー検査も維持されている。10変異の検出ログはhandoffの件数と一致する。P2の2経路は現在のテスト集合では検出されない。

ブラウザは提出された最終12画像をすべて目視し、ログのPOST4件（各1回）と390px幅=scrollWidthを照合。3領域→メタ→注記→絞り込み/索引→横スクロール表の順、文字ラベル、empty/loading/error/404を確認。Drawer幅min(600px,94vw)は03-spec.md:626の明示例外。独立レビューではブラウザドライバを再実行していないため、画像/ログは提出証跡として扱い、正式ゲートのみ独立再現した。

開始前のpytest/jestプロセス検査は非実行を確認。その後、ルートで `AGENT_MODE=local_dummy DEBUG=false CI=true make check` を**1回のみ**実行し exit 0。実出力:

```text
786 passed, 172 warnings in 71.55s (0:01:11)
✅ check-be: backend green
Test Suites: 28 passed, 28 total
Tests:       402 passed, 402 total
Snapshots:   0 total
Time:        26.373 s
Ran all test suites.
✅ check: all green
```

全文: `docs/test-results/approval-ui-independent-review-check-2026-09-13.log`。レビュー前後の `/tmp/approval-ui-review-snapshot.json`（FE259件）と `/tmp/approval-ui-protected.json`（BE214件）は全件一致。ゲートによるコード変更なし。実装・memory編集・.env*閲覧・実LLM呼出・git add/commitは行っていない。

DONE可否: **不可 — P2-1 / P2-2を修正して独立再レビューすること。**


## 独立レビュー第1回への対応（2026-09-13）

| 指摘番号 | 変更内容（file:line） | REDテスト・コマンドと実件数 |
|---|---|---|
| P2-1 | `frontend/src/features/versions/components/ItemListPage.tsx:49` からcaseIdを渡し、`hooks.ts:81,105` でSCR-03記録後も既存#22をexact invalidate。needsRecheckは引き続きAPI値を表示する | `approval-refresh.test.tsx`「評価確認済み版の訂正POST後、同一画面で版一覧を再取得して再確認バナーを出す」。`make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-refresh`: RED 1 failed → GREEN 1 passed。実hooks/API/生成client/mutatorを通し、fetchの#22 false→true、#23 review→staff、POST本文と1回送信、保存後#22が1回増加、#28未取得をassert |
| P2-2 | `frontend/src/features/versions/components/ApprovalListsDrawer.tsx:145` に行の全確認事項のreasonと最新noteを同一Typographyで併記。解決済みも含み、読取専用を維持 | `approval-components.test.tsx:62`「索引%sの変更・判断事項に解決済み確認の理由と判断内容を併記」（全行null/行4）。`make ... approval-ui-components`: RED 2 failed /18 passed → GREEN 20 passed。変更欄の見出し親内にreason/noteの組をassertし、未解決欄の重複で誤PASSしない |

SCR-03の訂正・取消・照合・判断は同じ版一覧を表示するためcaseIdを共通mutationへ渡す。以前のitems/questions/versionの再取得は維持。承認4mutationの再取得は引き続きrecords/version/versionsのみ（既存17パラメータ検査がGREEN）。#28をSCR-03へ新規取得する変更やSCR-05の変更はない。承認画面の#28は再マウント時に既存Query既定（staleTime=0）で再取得される。

REDログ: `docs/test-results/approval-ui-refresh-red-2026-09-13.log`、`approval-ui-lists-red-2026-09-13.log`。修正後の最初の検査ではバナーassertは通ったが、テストが初期#22の取得を1回と仮定して件数で失敗した。既存VersionHistoryの後続マウントによる初期再取得があるため、保存直前の実回数に対し保存後+1を検査するようテストを修正した（再取得数を不問にしていない）。そのログは `approval-ui-fixes-green-2026-09-13.log`、最終GREEN（1+20+17件）は `approval-ui-fixes-final-green-2026-09-13.log`。既存assertの削除・弱化なし。

追加2変異はenvを除外した一時frontendコピーのみで実行。`hooks.ts`の版一覧invalidateを承認専用へ戻す変異→1 failed、索引noteの表示を消す変異→2 failed /18 passed。`docs/test-results/approval-ui-fix-mutations-2026-09-13.log` および `approval-ui-mutation-{edit-versions,index-note}-2026-09-13.log`。従来10変異と合わせて12種検出。


## 修正後の正式ゲート・再レビュー依頼

`AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-design check-fe` がexit 0。design-lint違反0、実出力:

```text
Test Suites: 29 passed, 29 total
Tests:       405 passed, 405 total
Snapshots:   0 total
Time:        17.796 s, estimated 25 s
Ran all test suites.
✅ check-fe: frontend green
```

全文: `docs/test-results/approval-ui-fix-check-fe-2026-09-13.log`。ブラウザも同じ12シナリオを修正後コードで再実行して成功（`approval-ui-fix-browser-2026-09-13.log`）。12画像を更新し、row-index.pngの変更欄に「材質を照会 / 客先回答待ち」があることを目視。追加の解決済み/全行索引のケースは上記RTLで検査。

BE214ハッシュ不変。前回FE259ハッシュとの変更はhooks / ItemListPage / ApprovalListsDrawer / approval-components.testの4件だけ、追加はapproval-refresh.testの1件。今回レビュー用スナップショット `/tmp/approval-ui-rereview-snapshot.json` はFE260件。memoryは読取のみ、git add/commitなし。

**再レビュー依頼**: 独立第1回P2-1/P2-2の解消、追加TDDと2変異、AD-031維持をフレッシュ文脈で再確認してください。承認mutation17検査を含むFE405件は正式ゲート成功済みです。


## 独立再レビュー第2回（2026-09-13）

RV候補: T-503 独立再レビュー。前回P2-1/P2-2は解消。P1 0 / P2 1 / P3 0。DONE不可。
RV候補: SCR-06から開く根拠ドロワーの前後行IDがnull固定のため、複数行でも隣の根拠へ移動できない。閲覧導線の結線と回帰検査を要修正。
RV候補: 独立make checkはBE786 / FE405・29 suites成功。検査前後FE260 / BE214とmemory・git indexのSHA256一致。コード・テスト・memory・index変更なし。

### 指摘

- **P2-3 — SCR-06の根拠ドロワーで前後行へ移動できない。** `frontend/src/features/versions/components/ApprovalPage.tsx:323` / `:324` が `previous={null}` / `next={null}` を常に渡すため、`components/EvidenceDrawer.tsx:112` / `:119` が両ボタンを常時無効にする。全行表示でR1/R2の2行がある場合でも、R1の「根拠」または行索引の「この行の根拠を開く」から開いた後にR2へ進めず、一度閉じて別の行を開き直す必要がある。`docs/requirements/03-spec.md:251` はSCR-03/SCR-06両方から使うドロワーを定義し、`:258` / `:284` は「ドロワーを閉じずに隣の行へ移動（端では無効化）」を要求する。AD-031⑰のreadOnlyは記録操作を隠すもので、閲覧移動を外す決定ではない。既存SCR-03の `ItemListPage.tsx:275` / `:276` と同様に、承認画面の対象行列と現在行から前後IDを渡し、`onMove` の既存結線を有効にすること。最低2行で次行→前行の見出し/内容更新、端の無効化、readOnly維持を検査する必要がある。現行 `approval-components.test.tsx:336` のreadOnly検査も両IDがnullで、移動の欠落を検出しない。提出された `docs/test-results/approval-ui/read-only-evidence.png` でもR1/R2表示中にR1の次行ボタンが無効であることを目視した。

P1・P3: 今回の対象に追加指摘なし。既レビューのT-501/T-502/T-601 backend差分およびcases/hooks.test.tsxのT-502追従1行はT-503として評価していない。P2-3は新規ApprovalPageの結線不足であり、設計変更・API追加は不要。

### 前回指摘の独立確認

| 前回指摘 | 今回確認した箇所・根拠 | 判定 |
|---|---|---|
| P2-1 訂正後の再確認バナー | `ItemListPage.tsx:49` がcaseIdを渡し、`hooks.ts:81` の既存versionsKey exact invalidateまで結線。`__tests__/approval-refresh.test.tsx:14` はhooksをmockせず、生成client/mutatorを通るfetch応答を初期#22 needsRecheck=falseから訂正POST後trueへ変化させ、同一マウントのバナー表示・POST本文/1回・保存前比#22取得+1・#28未取得をassertする。#23の状態変化も応答で与え、FEでneedsRecheckを再導出していない | 解消 |
| P2-2 索引の理由・判断内容 | `ApprovalListsDrawer.tsx:145` が対象行の全質問を列挙し、reason/latest.noteを同一Typographyに表示。解決済みも除外しない。`approval-components.test.tsx:62` のnull/4の2ケースは「変更・判断事項」見出しの親に範囲を限定して解決済み質問の理由とnoteの組をassertし、未解決欄による誤PASSを防ぐ | 解消 |

REDログはバナー不在1失敗と索引内容不在2失敗を確認。保存前の#22取得回数を動的に取る修正は、後続VersionHistoryマウントによる初期再取得を許容しつつ保存後+1を固定しており、検査の弱化ではない。追加変異ログの版一覧invalidate削除1失敗、note削除2失敗/18成功も確認した。変異の独立再実行は行わず、正式全体ゲートで最終コードを独立検証した。

### 関連契約・表示・依存の確認

今回の修正に関わるAD-031②⑧⑮⑯⑰㉑㉒㉕を中心に、全体の新規/変更FEコードと既定契約を確認した。承認4mutationは依然としてrecords/version/versions(caseId)のみをexact invalidateし、items/questionsには触れない。`approval-hooks.test.tsx:28` の4種×201/409/404/400、および本番Providersでのretry:false検査が正式ゲートで成功。SCR-03の共通mutationはcaseId付きで版一覧も更新するが、従来items/questions/versionの更新を維持している。

行索引→全行索引、索引→根拠、表の根拠ボタン、ドロワー閉鎖・取得失敗時の再取得は既存state/callbackに結線されている。根拠の原表記・採用値・出典・条件・履歴・最新判断の閲覧表示は維持し、readOnly時はcallbackがあっても照合・訂正・取消・判断入力を出さない。前後移動の欠落はP2-3に分離した。承認と送付の別記録、名前の空初期値・メモリ内保持、時刻を要求に載せないこと、#22/#23/#28の要約取得元、5絞り込みと全体索引件数、10列・状態文字ラベル、SCR-01の3判断/null表示も確認。

依存は薄いroute→公開versions feature→components/hooks→api→生成client。新規modelにUI依存は無く、sharedからfeatureへの逆依存も増えていない。生成ファイル手編集・HTML挿入/URL自動リンク化・エラー本文や内部item IDの直接表示・外部送信処理の追加なし。既存テスト変更はprimaryの仕様変更および版履歴検査の責務移動で、元の空/エラーのassertを維持している。

修正後12画像（overview / row-index / read-only-evidence / bounced-item-list / reviewed / sendoff / case-list / mobile / loading / empty / error / not-found）をすべて目視した。row-indexに理由/noteの併記、3領域の配置と390pxでの縦配置・表内横スクロール、成功・空・読込・取得失敗・404を確認。ブラウザログのPOST4件各1回、width=scroll=390、pageerror=0と照合した。ブラウザドライバは再実行していないため、画像/ログは提出証跡として扱う。

### 独立ゲート・保全

開始直前の指定pgrep検査でpytest/jest非実行を確認後、ルートで `AGENT_MODE=local_dummy DEBUG=false CI=true make check > docs/test-results/approval-ui-rereview-check-2026-09-13.log 2>&1` を1回実行しexit 0。全体回帰を除外せず、pytest/jestを並列実行していない。

```text
786 passed, 172 warnings in 65.31s (0:01:05)
Test Suites: 29 passed, 29 total
Tests:       405 passed, 405 total
Snapshots:   0 total
Time:        21.084 s
Ran all test suites.
✅ check: all green
```

全文: `docs/test-results/approval-ui-rereview-check-2026-09-13.log`。検査前後 `/tmp/approval-ui-rereview-snapshot.json` のFE260件と `/tmp/approval-ui-protected.json` のBE214件は全一致。memoryのSHA256 `5de96d50ffb72bb2da03c9b5e8f705b3d16c275727b9a664a099f73b05130dc5`、git indexのSHA256 `db9400f2abb2618ce726932bd33fa75182b2184597c86b0626fd10f15452ac1a` も前後一致。本報告と指定ゲートログ以外は編集せず、.env*閲覧/表示/コピー・実LLM呼出・git add/commitは行っていない。

DONE可否: **不可 — 前回2件は解消。新規P2-3（根拠の前後行移動）を修正し独立再レビューすること。**


## 独立レビュー第2回への対応（2026-09-13）

| 指摘番号 | 変更内容（file:line） | REDテスト・コマンドと実件数 |
|---|---|---|
| P2-3 | `frontend/src/features/versions/components/ApprovalPage.tsx:112,325` で全明細の現在位置を取得し、隣接itemIdをEvidenceDrawerに渡す。両端はnullで無効化 | `approval-components.test.tsx`「%sから開いた根拠は前後行へ移動でき、両端だけ無効」（table/index）。`make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-components`: RED 2 failed /20 passed → GREEN 22 passed。R1→R2→R1の見出しとuseEvidence引数、両端disabled/中間enabled、Drawer1枚、textbox/checkboxなしをassert |

SCR-06の索引と既存current行の解決は絞り込み外も含む全明細を使用するため、隣接行も同じ全明細の順序に揃えた。テーブル絞り込みは表示行の抽出だけとし、索引から根拠へ進んだときも同じ隣接順で閲覧できる。これは閲覧用callbackの結線であり、記録やAPI契約を変更しない。

RED/GREEN: `docs/test-results/approval-ui-navigation-{red,green}-2026-09-13.log`。追加変異（隔離コピーでnextをnullへ戻す）は2 failed /20 passedで検出: `approval-ui-navigation-mutations-2026-09-13.log` / `approval-ui-mutation-evidence-navigation-2026-09-13.log`。累計13種の変異検出。既存テストは追加のみ、期待の削除・弱化なし。


## 再レビュー依頼（P2-3修正後）

`AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/approval-ui-checks.mk approval-ui-design check-fe`: exit 0、design-lint違反0。実出力:

```text
Test Suites: 29 passed, 29 total
Tests:       407 passed, 407 total
Snapshots:   0 total
Time:        20.76 s
Ran all test suites.
✅ check-fe: frontend green
```

全文: `docs/test-results/approval-ui-navigation-check-fe-2026-09-13.log`。ブラウザ12シナリオにR1→R2→R1移動・端disabled・閲覧専用維持のassertを加えて成功し、12画像を再更新（`approval-ui-navigation-browser-2026-09-13.log`）。read-only-evidence.pngの先頭行で「次の行」が有効、「前の行」が無効であることを目視した。

今回の変更はApprovalPage.tsxとapproval-components.test.tsxの2件のみ。BE214不変、レビュー固定対象FE260は `/tmp/approval-ui-navigation-review-snapshot.json`。memory編集・git add/commitなし。

**再レビュー依頼**: P2-3と既存の閲覧導線・readOnly境界の維持を、独立した正式ゲート（BE786/FE407期待）と併せて確認してください。第1回P2-1/P2-2は第2回独立レビューで解消確認済みです。

## 独立再レビュー第3回（2026-09-13）

RV候補: T-503 独立再レビュー。P2-3は解消。P1 0 / P2 0 / P3 0。DONE可。
RV候補: 表・行索引からの根拠前後移動、全明細の順序と両端の無効化、取得先・readOnly境界を確認。AD-031を変更する差分なし。
RV候補: 独立make checkはBE786 / FE407・29 suites成功。前後FE260 / BE214、memory・git indexのSHA256一致。コード・テスト・memory・index変更なし。

### 指摘・前回修正の判定

P1 / P2 / P3: **追加指摘なし**。

**P2-3解消** — `frontend/src/features/versions/components/ApprovalPage.tsx:112` で現在行の位置を全明細から求め、`:325` / `:326` で隣接itemIdまたはnullを渡す。`:328` のonMoveで選択行を更新し、`components/EvidenceDrawer.tsx:84` のuseEvidence(versionId, item.itemId)と`:105` の見出し・行データが更新される。`:112` / `:119` は実際の端だけ無効になる。0行・現在行不在ではApprovalPage:318の条件で根拠を描画せず、1行では両端nullとなる。仕様 `docs/requirements/03-spec.md:258` / `:284` と一致し、全明細順は `mocks/mockup.html:423` / `:517` のC().rowsによる前後移動とも一致する。

`__tests__/approval-components.test.tsx:280` の2入口は、実ApprovalPage・EvidenceDrawerを描画してR1→R2→R1のaccessible name、取得引数(9,6)→(9,4)、両端disabled/移動先enabled、Drawer1枚をassertする。索引入口は「訂正あり」で表を1行に絞った状態から始めるため、索引の全明細順も検査している。移動先にtextbox/checkboxが無いことに加え、既存のreadOnly単体検査でcallbackを渡しても訂正・取消・判断・照合を出さないことを維持。hooks/apiの既存検査は案件・版・行のキー分離と生成clientの根拠GET経路を検査している。

REDログの失敗箇所は両入口の「次の行が有効」で2 failed /20 passed、GREENは22 passed。nextをnullへ戻す隔離変異ログも同じ2 failed /20 passedであり、単なる見出し表示テストではない。第2回と今回のスナップショット差は上記実装・テストの2ファイルだけ（新規ファイル0）。既存テストの期待削除・弱化は認めなかった。変異は提出ログとして照合し、独立再実行はしていない。

### 関連導線・契約の維持

AD-031⑮⑰⑱に関わる表→索引、索引→全行/根拠、閉じる→承認画面はApprovalPage:282 / :294 / :308 / :318の排他的stateを共用。前後移動でもreadOnlyを外さず、原表記・採用値・出典・履歴・最新判断を表示する既存処理を使う。UIの行選択からhooks→api→生成clientへの依存を維持し、生HTTP・sharedからfeatureへの逆依存、外部送信・HTML挿入・内部ID表示の追加はない。デザイン値・翻訳・記録処理・API契約は今回変更していない。

第1回P2-1のItemListPage:49→hooks.ts:81の版一覧再取得と、P2-2のApprovalListsDrawer.tsx:145のreason/latest.note併記も確認。対応するapproval-refreshと索引2モードの既存テストは正式ゲートで成功し、解消を維持している。AD-031の25決定は所与として扱い、対象外のSCR-04差し戻しコメント・変更採用タグ・SCR-01差し戻し補足を追加していない。既レビューBE差分とcases/hooks.test.tsxのT-502追従1行は保全対象として区別した。

提出画像read-only-evidence.pngでR1の前無効/次有効、overview.pngで3領域と文字ラベル、row-index.pngで理由/note、mobile.pngで縦配置と表内横スクロールを目視。最新ブラウザログの12シナリオ成功、POST4件各1回、width=scroll=390、pageerror=0と照合した。ブラウザドライバは独立再実行しておらず、画像/ログは提出証跡として扱う。

### 独立ゲート・保全

開始直前に指定の `if pgrep -x pytest >/dev/null || pgrep -f '/[j]est' >/dev/null; then exit 75; fi` を通過後、ルートで `AGENT_MODE=local_dummy DEBUG=false CI=true make check > docs/test-results/approval-ui-navigation-review-check-2026-09-13.log 2>&1` を**1回**実行しexit 0。全体回帰の除外・pytest/jest並列実行なし。

```text
786 passed, 172 warnings in 66.02s (0:01:06)
✅ check-be: backend green
Test Suites: 29 passed, 29 total
Tests:       407 passed, 407 total
Snapshots:   0 total
Time:        20.669 s
Ran all test suites.
✅ check: all green
```

全文: `docs/test-results/approval-ui-navigation-review-check-2026-09-13.log`。検査前後 `/tmp/approval-ui-navigation-review-snapshot.json` のFE260件と `/tmp/approval-ui-protected.json` のBE214件は全一致。memoryのSHA256 `5de96d50ffb72bb2da03c9b5e8f705b3d16c275727b9a664a099f73b05130dc5`、git indexのSHA256 `db9400f2abb2618ce726932bd33fa75182b2184597c86b0626fd10f15452ac1a` も前後一致。本報告と指定ゲートログ以外は編集せず、.env*閲覧/表示/コピー・実LLM呼出・git add/commitは行っていない。

DONE可否: **可 — P2-1/P2-2の解消を維持し、P2-3も解消。追加指摘なし。memory転記・commitは未実施。**


## 完了記録・周回待機

第3回独立レビューで全指摘解消・DONE可。希望Status: DONE。独立正式ゲートBE786 / FE407・29 suites成功。memoryへの決定・RV/LN転記とgit add/commitは、ユーザー明示指示に従い実施しない。転記案は本handoff内に保持する。

**再レビュー依頼**の各回に対し、上記の独立レビューで解消確認済み。T-503の残作業なし。次スライス候補は現行§7にT-602/T-603とあるが、会話の「§7見出しの更新時刻が変わるまで待って再読」に従い、§7を自己更新して次へ進まず外部更新を待機する。改訂§0bの自己更新手順と会話の待機指示の相違はユーザーへ通知した。
