# T-503 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-503【FE】G5 SCR-06 引合書承認（＋SCR-03 の G5 追加・SCR-01 送付可否列）**（memory §3・依存 **T-502 DONE ＋ commit 後**。`make check-fe` の再生成で `generated/ui.ts` に #28/#34〜#37 が出ていることを確認してから着手）。handoff 冒頭に触るファイル一覧を先に書く（CODEX-INSTRUCTIONS §5）。
設計の正: 03-spec.md SCR-06・SCR-03（「Build 実装との対応」②に G5 追加の明記）・SCR-01・SCR-04・3 章（AD-031 の注記追記済み）、05-api-ipo.md #1/#22/#28・3.7〜3.9・FLOW-05/06・6 章、02 FUNC-10・7 章、04-db §3.4、モック `mockup.html` の `#SCR-06`。
前例: `docs/t403-instructions.md` / `docs/t403-handoff.md` / `frontend/src/features/versions/**`。前提決定: AD-024〜AD-030、CV-015/018/019/021/023/025/026/027、LN-021/031/058/060、TODO-030 ③（補間名 `count` 不可）、**RV-043 P2-1/P3-1（注記は「見出し句＋理由＋行動」を敬体で。見出し句だけに切り詰めない）**。**`docs/t502-handoff.md` の「T-503 へ渡す契約」節で #22/#28 の実キーと 7 コードを確認し、差があれば handoff 冒頭に差分を書く。**

## 0. orchestrator 決定（AD-031・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| ① | feature の置き場 | **`features/versions/` に追加**（#22/#23/#24/#26・`useRecordMutation`・`versionKey`・`recordErrorKey`・`ItemValue`・`EvidenceDrawer` を再利用。CV-015）。`index.ts` に `ApprovalPage` を公開 |
| ② | 範囲の 3 画面 | **SCR-06 新規 ＋ SCR-03 の G5 追加（「担当者確認済みにする」・差し戻し中バナー・再確認が必要・「引合書承認へ」導線）＋ SCR-01 送付可否列を 1 スライスで**。理由: 遷移ボタンが無いと G5 の経路が閉じない。`bounced`・`needsRecheck` は API 導出（AD-029 ③）で FE は表示のみ |
| ③ | SCR-04 の「上司の差し戻しコメント」 | **含めない**（TODO-041）。SCR-03 の差し戻し表示は #22 `latestBounce.reason` で足り、SCR-03 で #28 を取らない |
| ④ | ルート | `src/app/(portal)/cases/[caseId]/versions/[versionId]/approval/page.tsx`（inventory と同型の薄い Server Component） |
| ⑤ | primary | **SCR-06 は「評価確認済みにする」1 つ**。他は outlined / text。**SCR-03 は「担当者確認済みにする」1 つ**（`currentState==='draft'` のときのみ表示。他状態は text リンク「引合書承認へ」→ primary 0）。AD-024 ②「T-303 では置かない」は G5 で解除 |
| ⑥ | 要約カード 7 値の取得元 | 評価状態=#23 `currentState`（＋#22 `bounced`→「差し戻し中」/ `needsRecheck`→「再確認が必要」を隣に文字ラベル）／送付可否=#22 `latestSendoff?.decision`（null→「未判断」＋caption「記録なし」）／一致確認=#23 `counts.matchedCount / itemCount`／網羅性=#23 `coverageConfirmed`／訂正=#23 `counts.editCount`／未解決=#23 `counts.unresolvedCount`／**差し戻しコメント=#28 `unlinkedComments.length`**（未確定＝次の差し戻しの理由になる件数）。純粋関数 `approvalSummary(version, listItem, records)` |
| ⑦ | 記録者メタ 1 行 | #28 から純粋関数 `recorderMeta(records)`: 担当者=`stateEvents` の最新 `toState==='staff_checked'`／網羅性確認=`confirmations` の `kind==='coverage' ∧ undoneAt===null`／評価確認=最新 `toState==='review_checked'`。無い項目は「未記録」 |
| ⑧ | #22 の取り方 | 既存 `useVersionHistory(caseId)` から `findVersionListItem(list, versionId)` で抜く（新 API 関数を作らない）。見つからなければ取得失敗扱い |
| ⑨ | 行コメント（#35） | **行ごとの `TextField` ＋ text ボタン「記録」で明示 POST**（blur だけでは記録しない）。記録後は入力を空にし、その行の `unlinkedComments` を「{comment} — {recordedBy} / {recordedAt}」で列挙。取消 API は無いので取消操作を置かない |
| ⑩ | 差し戻す（#36） | 要求は `{recordedBy}` のみ。クライアント検査: 確認者名空→`E_RECORDER_REQUIRED` 文言・`unlinkedComments` 0→`E_NO_BOUNCE_COMMENT` 文言（POST しない）。成功→`router.push` で SCR-03 へ。サーバ 409 は code で分岐し再取得 |
| ⑪ | 評価確認済みにする（#34） | `{toState:'review_checked', recordedBy}`。成功後は画面に留まり `role="status"` で「評価確認済みにしました（未解決 n 件を含む）。送付可否は別に判断してください」。`E_STATE_ORDER` は文言＋再取得 |
| ⑫ | ① ボタンの有効条件 | `draft`→両ボタン disabled ＋「担当者の確認が未完了です」注記（照合 n/N・網羅性 済/未・SCR-03 へリンク）。`review_checked`（`needsRecheck=false`）→両ボタン disabled ＋「評価確認済みです。訂正が記録されると再確認が必要になります」（AD-028 ⑤: review 版は差し戻せない） |
| ⑬ | 送付可否（#37） | `decision` select（未判断/保留/承認）＋理由・条件＋判断者（必須）＋ outlined「記録」。クライアント検査: 判断者空→`E_RECORDER_REQUIRED`、`hold`/`approved` で理由空→`E_SENDOFF_REASON_REQUIRED`（POST しない）。`undecided` で理由空は `reason: null`。現在値は #22 `latestSendoff`。任意状態で記録可（AD-028 ⑧） |
| ⑭ | 記録者名の入力欄 | **2 欄**: 確認者名（評価確認・差し戻し・行コメントに共用）／判断者名（送付可否）。SCR-03 の担当者名と共有しない（AD-027 ⑪）。メモリのみ・初期値空 |
| ⑮ | 変更・判断事項／未解決事項の索引 | **MUI `Drawer`（読取専用）`ApprovalListsDrawer`**。全行索引（絞り込み欄右のボタン。0 行でもボタンを残す）と行単位（行クリック／Enter。`button,a,input,select,textarea,label` 上は開かない）の 2 モード。API 追加なし・クライアント側で絞る。行単位では案件レベル未解決件数の注記＋「全行の索引を開く」「この行の根拠を開く」 |
| ⑯ | 「変更・判断事項」の定義 | 純粋関数 `changeTags(item, questions)` → `choice`(groupCode) / `tba`(qtyState) / `inherit`(isInheritCandidate) / `edited`(未取消 history 件数) / `judged`(latest≠null)。**「変更採用（P.S./Rev.）」タグは #24/#26 に判別項目が無いため出さない**（TODO-039）。未解決=`latest===null ∨ latest.resolution==='unresolved'`（`filterItems.unresolved` と同じ述語） |
| ⑰ | SCR-06 での根拠ドロワー | 既存 `EvidenceDrawer` に **`readOnly` prop**（照合チェック・訂正フォーム・取消・判断フォームを非表示、閲覧系は表示）。上司が担当者名欄無しで訂正できてしまうのを防ぐ |
| ⑱ | 絞り込み | 5 択 `approvalFilters=['all','changes','edited','unresolved','bounce']` ＋「{shown} / {total} 行」。索引の件数は絞り込みに影響させない |
| ⑲ | 承認テーブル 10 列 | 行ID（＋caption 照合済み/未照合）／品種／仕様（外径・単重・材質・接続・長さを `DimensionValue`/`ItemValue` で 1 セル・「 / 」区切り）／数量（TBA は文字）／納期／グループ（＋「合算しない」caption）／担当者の訂正（未取消 history を「{項目}：{旧} → {新}」＋caption 理由／修正者）／担当者の判断（対応状況・解決状態＋判断内容＋caption 理由）／根拠（text ボタン）／上司の差し戻しコメント（⑨）。数値は丸めない（AD-024 ⑦） |
| ⑳ | トーン | 差し戻し中・再確認が必要・保留・未解決・未照合=warn／承認・評価確認済み・解決・照合済み・網羅性 済=ok／未判断・未記録・作成案・担当者確認済み=中立。danger は使わない（入力エラーは `aria-invalid`）。5 色目なし |
| ㉑ | hooks | `recordsKey=["version",vid,"records"]`・`useRecords`・`useApprovalMutations(caseId, versionId)`={`transition`,`bounceComment`,`bounce`,`sendoff`}。`useRecordMutation` の `resource` に `"approvals"` を追加し **`recordsKey`＋`versionKey`＋`versionsKey(caseId)`** を invalidate（`caseId` を optional 引数で受ける。`itemsKey`/`questionsKey` は触らない）。`retry:false`。SCR-03 の遷移も同 hook |
| ㉒ | エラー文言 | `approvalErrorKey(error)`: 7 コード→`versions.approval.errors.*`、他は `recordErrorKey` へフォールバック。`E_STAFF_CHECK_INCOMPLETE` は `staffCheckDetails(error)` で `details.unmatchedRowCodes` と `coverageRecorded` を補間（`unmatchedItemIds` は出さない・CV-019） |
| ㉓ | 日時表示 | 応答値の文字列をそのまま（T-303/403 と同じ）。書式統一は C-3（TODO-030 ⑥・AD-030 ⑪ の書式に揃える） |
| ㉔ | SCR-01 送付可否列 | #1 `latestSendoff`（`undecided`/`hold`/`approved`/null）→「未判断／保留／承認／—」。「差し戻しあり」補足は #1 に `bounced` が無いため出さない（TODO-040） |
| ㉕ | 既存テスト | 期待の更新として置換（削除しない・理由を handoff に）。T-502 再生成で typecheck が赤ければ fixture 追従を **「T-502 追従」として分けて**先に直す |

## 1. 範囲と範囲外

**範囲（FE のみ）**
- `features/versions/`: `api.ts`（`listRecords`・`recordStateEvent`・`recordBounceComment`・`recordBounce`・`recordSendoffDecision`）／`hooks.ts`（㉑）／`model.ts`（§4）／components（`ApprovalPage`・`ApprovalSummaryCard`・`ReviewCheckPanel`・`SendoffPanel`・`ApprovalFilters`・`ApprovalTable`・`BounceCommentCell`・`ApprovalListsDrawer`・`EvidenceDrawer` の `readOnly`）／`testing/fixtures.ts` 追記（`records`・`listItem`。件数が ⑯ の述語と一致する合成データ）／tests
- ルート `.../approval/page.tsx`。`index.ts` に `ApprovalPage`
- **SCR-03**（`ItemListPage.tsx`）: 見出し右に「担当者確認済みにする」（⑤）→ #34 `staff_checked` → 成功で SCR-06 へ／`E_STAFF_CHECK_INCOMPLETE`「未照合 {n} 行（{rowCodes}）。網羅性確認：{済/未}」＋「網羅性照合へ」／`E_COVERAGE_NOT_RECORDED` 文言＋リンク／未解決>0 のときボタン脇に注記。メタ下に **差し戻し中バナー**（#22 `bounced`: 文言＋判断者・日時＋`latestBounce.reason` を行ごとに `blockquote`）と **再確認が必要**（#22 `needsRecheck`）。#22 は `useVersionHistory(caseId)` を `ItemListPage` でも呼ぶ（同キー）
- **SCR-01**（`CaseListPage.tsx`）: 送付可否列 ㉔
- `ja.json` `versions.approval.*`・`versions.staffCheck.*`・`cases.list.sendoffState.*`（**components 着手前に** §3 と 1 対 1）

**範囲外**: G6（出力ボタン・版の履歴の生成所要）、SCR-04 の差し戻しコメント表示（③）、「変更採用」タグ（⑯）、SCR-01「差し戻しあり」補足、表下の 2 つ目の差し戻しボタン、対象案件セレクタ、`backend/**`、`generated/**`（編集禁止。再生成は `make check-fe`）、`docs/requirements/*`・memory・commit（Claude）。

## 2. 使う API（`shared/api/generated/ui.ts`。**T-502 commit 後の再生成で名前を確認し handoff に**）

| # | 生成関数（見込み） | 要求 / 応答 | unwrap |
|---|---|---|---|
| 22 | 既存 `api.listVersions` | `VersionListItem{…既存, unresolvedCount, carryOver{…}, latestStateEvent\|null, latestBounce\|null（comments=[]）, latestSendoff\|null, bounced, needsRecheck}` | 200 |
| 23 / 24 / 26 | 既存 `useVersion` / `useItems` / `useQuestions` | 状態・件数・行・確認事項 | 200 |
| 28 | `listRecordsApiV1UiVersionsVersionIdRecordsGet` | `RecordsResponse{edits, confirmations(+undoneAt/undoneBy), judgements, stateEvents, bounces(comments 内包), unlinkedComments, sendoffDecisions}` 各 `(recordedAt,id)` 昇順 | 200 |
| 34 | `recordStateEventApiV1UiVersionsVersionIdStateEventsPost` | `{toState, recordedBy}` → `StateEventRecord` | 201 |
| 35 | `recordBounceCommentApiV1UiVersionsVersionIdBounceCommentsPost` | `{itemId, comment, recordedBy}` → `BounceCommentRecord` | 201 |
| 36 | `recordBounceApiV1UiVersionsVersionIdBouncesPost` | `{recordedBy}` → `BounceRecord` | 201 |
| 37 | `recordSendoffDecisionApiV1UiVersionsVersionIdSendoffDecisionsPost` | `{decision, reason\|null, recordedBy}` → `SendoffDecisionRecord` | 201 |
| 1 | 既存 `listCases` | `CaseListItem.latestSendoff` | 200 |

エラーは `ApiError.code` で分岐・生値非表示: `E_RECORDER_REQUIRED` / `E_COMMENT_REQUIRED` / `E_SENDOFF_REASON_REQUIRED` 400、`E_STATE_ROLLBACK_FORBIDDEN` 422、`E_STATE_ORDER` / `E_STAFF_CHECK_INCOMPLETE`（details 3 キー）/ `E_COVERAGE_NOT_RECORDED` / `E_NO_BOUNCE_COMMENT` 409、`E_NOT_FOUND` 404、他 → `versions.errors.unknown`。`recordedAt` は要求に載せない。

## 3. i18n（`ja.json`。敬体・「事実＋理由＋行動」。03-spec SCR-06 の要素表・操作表・エラー表と 1 対 1）

| キー（`versions.approval.` 配下） | 文言 |
|---|---|
| `title` / `description` | 引合書承認 ／ 担当者が確定した Item List を、修正と判断がわかる状態で確認し、承認または差し戻しを記録します。 |
| `back` / `link`（SCR-03 側導線） | Item List へ ／ 引合書承認へ |
| `summary.title` | 状態の要約 — 担当者の確認結果 |
| `summary.{state,sendoff,matched,coverage,edits,unresolved,bounceComments}` | 評価状態／送付可否／一致確認／網羅性確認／訂正／未解決／差し戻しコメント |
| `summary.matchedValue` | `{{matched}} / {{total}}` |
| `summary.bounced` / `summary.needsRecheck` | 差し戻し中（作成案には戻りません） ／ 再確認が必要（評価確認済みの後に訂正が記録されました。評価確認の記録は消えません） |
| `summary.noSendoff` | 記録なし |
| `meta` / `meta.recorded` / `meta.unrecorded` | 担当者：{{staff}} ／ 網羅性確認：{{coverage}} ／ 評価確認：{{review}} ／ `{{by}} / {{at}}` ／ 未記録 |
| `review.title` | ① 評価確認 — 原資料への適合を確認する |
| `review.recorder` / `review.recorderHint` | 確認者名（必須） ／ 評価確認・差し戻し・行コメントの記録者になります。AI は補完しません。 |
| `review.approve` / `review.bounce` | 評価確認済みにする ／ 差し戻す |
| `review.hint` | 差し戻しは表右端の行コメント（{{rows}} 行）を理由にします。評価確認済みは送付承認ではありません。 |
| `review.draftHint` / `review.reviewedHint` | 担当者の確認が完了すると押せます。 ／ 評価確認済みです。訂正が記録されると再確認が必要になります。 |
| `review.done` | 評価確認済みにしました（未解決 {{unresolved}} 件を含む）。送付可否は別に判断してください。 |
| `review.bounced` | 差し戻しを記録しました（{{rows}} 行）。状態は担当者確認済みのままです。 |
| `sendoff.title` | ② 送付可否 — 対外送付の判断（①とは別の記録） |
| `sendoff.{decision,reason,recorder,record}` | 判断／理由・条件（保留・承認は必須）／判断者（必須）／記録 |
| `sendoff.current` / `sendoff.done` | 現在：{{decision}} ／ {{by}} ／ {{at}} ／ 送付可否を「{{decision}}」として記録しました。評価確認とは別の記録です。 |
| `sendoff.state.{undecided,hold,approved}` | 未判断／保留／承認（`cases.list.sendoffState.*` と同語） |
| `notice.lead` | 評価確認済みは送付承認ではありません。 |
| `notice.incomplete` | 担当者の確認が未完了です（照合 {{matched}}/{{total}} 行・網羅性確認 {{coverage}}）。Item List 確認画面で照合と網羅性確認を完了してください。 |
| `notice.unresolved` | 未解決 {{unresolved}} 件を含めて評価確認を終えられます。件数は記録と出力に残ります。 |
| `filters.label` / `filters.{all,changes,edited,unresolved,bounce}` / `filters.shown` | 表示 ／ 全行・変更・判断事項のある行・訂正あり・未解決のみ・差し戻しコメントあり ／ `{{shown}} / {{total}} 行` |
| `lists.open` / `lists.title` / `lists.rowTitle` | 変更・判断事項 {{changes}} 行 ／ 未解決 {{unresolved}} 件 を開く ／ 変更・判断事項と未解決事項 ／ 行 {{row}} の変更・判断事項と未解決事項 |
| `lists.description` | どの行を見るべきかを示す索引です。{{total}} 行のうち 変更・判断事項 {{changes}} 行／未解決 {{unresolved}} 件。判断の入力は表または Item List 確認画面で行います。 |
| `lists.rowDescription` / `lists.caseUnresolved` | この行に紐づく事項だけを表示しています（変更・判断事項 {{changes}} 件／未解決 {{unresolved}} 件）。 ／ 行に紐づかない案件レベルの未解決 {{caseLevel}} 件があります。「全行の索引を開く」で確認してください。 |
| `lists.openEvidence` / `lists.openAll` / `lists.close` | この行の根拠を開く ／ 全行の索引を開く ／ 閉じる |
| `lists.changesTitle` / `lists.unresolvedTitle` | 変更・判断事項（{{total}} 行）／ 未解決事項（{{total}} 件） |
| `lists.noChanges` / `lists.noRowChanges` | 変更・択一・TBA・継承候補・訂正・判断のある行はありません。 ／ この行に変更・判断事項はありません。原資料との照合は必要です。 |
| `lists.noUnresolved` / `lists.noRowUnresolved` | 未解決の確認事項はありません。 ／ この行に未解決の確認事項はありません。 |
| `lists.unresolvedNote` | 「照会中」「保留」と判断しても客先回答が無い限り未解決です。件数は評価確認の記録と .xlsx に残ります。 |
| `lists.caseLevel` | 案件レベル |
| `tags.{choice,tba,inherit}` / `tags.edited` / `tags.judged` | 択一 {{group}}／数量TBA／継承候補 ／ 担当者訂正 {{total}} 件 ／ 担当者判断 {{status}}／{{resolution}} |
| `columns.{rowCode,kind,spec,qty,due,group,edits,judgement,evidence,bounce}` | 行ID／品種／仕様（外径／単重／材質／接続／長さ）／数量／納期／グループ／担当者の訂正／担当者の判断／根拠／上司の差し戻しコメント |
| `row.{matched,unmatched}` / `row.noGroupSum` / `row.openLabel` / `row.edit` / `row.evidence` | 照合済み／未照合 ／ 合算しない ／ 行 {{row}} の変更・判断事項と未解決事項を開く ／ `{{field}}：{{old}} → {{new}}` ／ 根拠 |
| `bounce.label` / `bounce.record` / `bounce.recorded` | 行 {{row}} の差し戻しコメント ／ 記録 ／ `{{comment}} — {{by}} / {{at}}` |
| `emptyFiltered` / `emptyItems` | 条件に一致する行はありません。表示を「全行」に戻してください。 ／ この版に明細がありません。資料投入画面で案を作成してください。 |
| `tableNote` | 仕様・数量は担当者の訂正を反映した確定値です。訂正欄に旧値・新値・理由、判断欄に対応状況・解決状態・判断内容が出ます。差し戻す行にコメントを入れて記録し、①の「差し戻す」で確定してください。 |
| `notFound` / `loadError` / `reload` | 版が見つかりません。案件一覧から版を選び直してください。 ／ 承認データを取得できませんでした。接続を確認して再取得してください。 ／ 再取得 |
| `errors.E_STAFF_CHECK_INCOMPLETE` | 担当者の確認が未完了です。未照合 {{unmatched}} 行（{{rowCodes}}）・網羅性確認 {{coverage}}。Item List 確認画面で完了してから再操作してください。 |
| `errors.E_COVERAGE_NOT_RECORDED` | 網羅性確認が未記録です。網羅性照合画面で記録してから再操作してください。 |
| `errors.E_STATE_ORDER` | この状態からは記録できません（同じ状態への再遷移、または評価確認済みの版への差し戻し）。最新の状態を再取得して確認してください。 |
| `errors.E_STATE_ROLLBACK_FORBIDDEN` | 作成案には戻せません。差し戻しは状態を変えず記録として残します。 |
| `errors.E_NO_BOUNCE_COMMENT` | 差し戻す行にコメントを入力してください（表の右端の列）。理由の無い差し戻しは記録できません。 |
| `errors.E_SENDOFF_REASON_REQUIRED` | 保留・承認は理由・条件の入力が必要です。未解決を残して承認する場合も理由を残してください。 |
| `errors.E_COMMENT_REQUIRED` | 行コメントを入力してから記録してください。空のコメントは記録できません。 |
| `errors.E_RECORDER_REQUIRED` / `errors.E_RECORDER_REQUIRED_SENDOFF` | 確認者名を入力してください。AI は補完しません。 ／ 判断者を入力してください。AI は補完しません。 |

`versions.staffCheck.*`（SCR-03）: `button`「担当者確認済みにする」／`link`「引合書承認へ」／`unresolvedNote`「未解決 {{unresolved}} 件のまま担当者確認済みにできます。件数は記録と出力に残ります。」／`bounced`「差し戻し中（作成案には戻りません）」／`bouncedBy`「判断者：{{by}} / {{at}}」／`needsRecheck`「再確認が必要：評価確認済みの後に訂正が記録されました。評価確認の記録は消えません。」／`errors.E_STAFF_CHECK_INCOMPLETE`「未照合 {{unmatched}} 行（{{rowCodes}}）。網羅性確認：{{coverage}}。すべて照合し、網羅性確認を記録してから再操作してください。」／`toInventory`「網羅性照合へ」。
`cases.list.sendoffState.{undecided,hold,approved}` = 未判断／保留／承認、null は `common.notAvailable`。**補間名に `count` を使わない。**

## 4. components / model / hooks

**model.ts（純粋関数・RED 対象）**: `findVersionListItem` / `approvalSummary` / `recorderMeta` / `changeTags`・`hasChanges` / `unresolvedQuestions`・`rowUnresolved`・`caseLevelUnresolved` / `rowBounceComments(records, itemId)` / `approvalFilters`＋`filterApprovalRows` / `buildStateEventRequest`（空白名→`E_RECORDER_REQUIRED`）・`buildBounceCommentRequest`（空コメント→`E_COMMENT_REQUIRED`）・`buildBounceRequest(recordedBy, unlinkedCount)`（0→`E_NO_BOUNCE_COMMENT`）・`buildSendoffRequest`（`hold|approved` 空→`E_SENDOFF_REASON_REQUIRED`、`undecided` 空→`reason:null`）／`canReview(currentState)` → `'incomplete'|'ready'|'reviewed'` / `approvalErrorKey` / `staffCheckDetails` / `sendoffTone`・`stateTone`。
**hooks.ts**: `recordsKey`・`useRecords`・`useApprovalMutations`・`useRecordMutation` の `resource:"approvals"`＋`caseId?`。
**components**: `ApprovalPage`（h1・3 状態・ドロワー状態 `{kind:'lists', itemId|null} | {kind:'evidence', itemId} | null` を 1 state で排他）／`ApprovalSummaryCard`／`ReviewCheckPanel`／`SendoffPanel`／`ApprovalFilters`／`ApprovalTable`／`BounceCommentCell`／`ApprovalListsDrawer`／`EvidenceDrawer`（`readOnly`）。SCR-03: `StaffCheckAction`・`BounceBanner` を小コンポーネントで。SCR-01: 1 セル。
**design-guidelines**: primary は SCR-06 1・SCR-03 draft 時 1・SCR-01 既存 1。h1 1（カード・ドロワー見出しは h2）。Paper `outlined`、罫線 `hair`/`divider`、hex/インライン style 禁止。表は横スクロール・`nowrap`。モック `#SCR-06` と構成一致: 3 カード横並び → メタ → 注記 → 絞り込み＋索引ボタン → 表 → 表下注記。`blockquote` は差し戻し理由の引用のみ。

## 5. 実装順序と RED→GREEN

0. **T-502 追従**（該当時）: typecheck が赤なら fixture を追従し handoff で分ける。`grep -rn "VersionListItem\|CaseListItem" frontend/src --include=*.ts* | grep -v generated` を handoff に
1. `ja.json`（§3 と 1 対 1・敬体）
2. `api.ts` 5 関数 → RED `__tests__/approval-api.test.ts`（URL/method・201/200 unwrap・非 2xx `ApiError` 1 回・body 透過）
3. `model.ts` → RED `__tests__/approval-model.test.ts`（7 値と `unlinkedComments.length`・`recorderMeta` の末尾選択と `undoneAt` 除外・`changeTags` 5 種で「変更採用」を出さない・未解決述語が `filterItems.unresolved` と一致・5 択と入力不変・`build*Request` 4 種の検査順と `reason:null`・`canReview` 3 状態・`approvalErrorKey` 7 コードとフォールバック・`staffCheckDetails` が `unmatchedItemIds` を返さない）
4. `hooks.ts` → RED `__tests__/approval-hooks.test.tsx`（4 mutation × 201/409/404/400 で `records`＋`version`＋`versions(caseId)` を再取得し `items`/`questions` は触らない・`retry:false`・1 回の `renderHookWithProviders`（LN-021）・本番 `Providers` で 400 POST 1 回（CV-018））
5. components → RED `__tests__/approval-components.test.tsx`（h1 1・contained 1・3 状態・7 値・`bounced`/`needsRecheck` ラベル・メタ 3 項目と未記録・draft/review_checked で disabled＋注記・確認者名空で POST 0・#34 1 回と status 文・行コメント空で POST 0／記録後の列挙・unlinked 0 で差し戻し POST 0・差し戻し成功の遷移先・送付可否 3 検査と `reason:null`・5 絞り込み・索引 0 件でもボタン表示・行クリックで行モード（ボタン上では開かない）・readOnly ドロワーに訂正フォーム無し・HTML/URL のリンク化なし・`unmatchedItemIds` 非表示・ドロワー同時 open は 1）
6. SCR-03/01 → 既存 `components.test.tsx`（draft で contained 1・他状態で導線・#34 `staff_checked` 1 回・成功で遷移・`E_STAFF_CHECK_INCOMPLETE` 文言＋SCR-05 リンク・`bounced` バナー・`needsRecheck`）／`CaseListPage.test.tsx`（3 値＋null）／`case-routes.test.tsx`（approval ルート）。置換は理由を handoff に
7. ブラウザ確認（合成 API 応答・画像は `docs/test-results/approval-ui/`・390px 横はみ出し 0・pageerror 0・ドライバは残さない）
8. 変異（各 1 行・隔離コピー）: `retry:false` を外す／`versionsKey` invalidate を外す／確認者名検査／unlinked 0 検査／`hold` の理由検査／`recorderMeta` の `undoneAt` 除外／`changeTags` から `inherit`／readOnly で訂正フォームを出す／行クリック判定／`unmatchedItemIds` 混入
9. `npx prettier --write` → `AGENT_MODE=local_dummy DEBUG=false CI=true make check-fe`

## 6. 完了条件

`make check-fe` green（prettier 込み・件数は実測）／`git status --short -- backend` 空／design-lint 0／`generated/**` 手編集なし／primary: SCR-06 1・SCR-03 draft 1／他 0・SCR-01 1／h1 各 1／3 状態／`docs/t503-handoff.md`: 触ったファイル（本体／共有 `ItemListPage.tsx`・`CaseListPage.tsx`・`EvidenceDrawer.tsx`・`hooks.ts`・`ja.json`／T-502 追従は分ける）→ 生成関数名の確認結果 → §0 ①〜㉕ の反映箇所（file:line）→ レビュー対応表 → 既存テスト置換の理由 → ブラウザ証跡 → 末尾見出し **`## 再レビュー依頼（T-503）`**（本文中でこの語を使わない・LN-033）。commit は Claude。pytest は回さない（LN-027）。
