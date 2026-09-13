# T-502 handoff

## 変更予定ファイル（着手前の範囲宣言）

- 本体: 新規 `backend/app/api/ui/schemas/approvals.py` / `endpoints/approvals.py`、既存 `schemas/versions.py` / `schemas/cases.py` / `endpoints/versions.py`、案件一覧の Repository / Service（latestSendoff 読取追加）。
- 共有: `backend/app/api/dependencies.py` / `ui/router.py` / `errors.py`。
- T-501 モジュールへの明示追記: `backend/app/services/version_state.py` の導出関数、`approval_service.py` の一覧に derived flag 付与。T-501既存差分は保全。
- テスト: 新規 `tests/unit/test_approval_api.py` / `tests/integration/test_api_approvals.py`、既存 `test_version_state.py` / `test_approval_service.py` / `test_record_api.py` / 案件 API テスト / `test_api_path_separation_live.py`。共通テストデータが必要なら `tests/fixtures/approval_data.py` に置く。
- 本 handoff / `docs/test-results/approval-api-*` 検証ログ。OpenAPI と orval は root Make で生成。

## T-501 契約との差分

`bounce()` は Bounce ORM 行だけを返し comments を返さない。AD-029 ⑫に従い #36 応答から comments を外し、#28 の履歴と #22 の latestBounce（空配列）にだけ comments を持たせる。専用 DTO を設け、既存 RecordService/Repository の契約は変更しない。`latest_review_checked_at` は T-501 で実装済み（追補不要）。

Status: 実装・全体検証完了。T-501 は独立レビュー DONE 可。ユーザー指定により memory と commit は変更しない。

着手時 `rg -n VersionListItem frontend/src -g "*.ts" -g "*.tsx" -g "!generated/**"`: 非生成コードの参照 0 件。生成モデル146をスナップショット保存。

型共用のため `app/domain/record_types.py` の SendoffInput.decision の既存 Literal を `SendoffState` エイリアスへ抽出（語彙・検証・保存仕様は不変）。`schemas/versions.py` の VersionState も既存 domain 定義を import。案件一覧の変更箇所は `app/repositories/case_repository.py` / `app/services/case_service.py` / `app/api/ui/endpoints/cases.py`。SQLAlchemy 行の列を `id,case_id,current_state,latest_sendoff` に絞り、latest_versions 1 クエリのまま返す。

既存テスト変更: `test_record_api.py` は #22 の DI 切替に合わせ ApprovalService mock を追加し、旧 Service 未呼出を追加assert。`test_case_service.py` は案件一覧 tuple に latest_sendoff を追加する契約へfixture/期待値を追従。`test_approval_service.py` の空版リストは導出処理後の値比較へ（list_records の identity検査は維持）、別テストで derived flag の値と Repository 材料不変を確認。

## 統合時の最小限の範囲調整

CaseListItem.latestSendoff を必須 nullable として生成した結果、既存 FE fixture 2 箇所が tsc の TS2741 で計8エラー。T-403 は独立レビュー DONE 済みで並行 FE 作業なし。契約を optional に弱めず、`frontend/src/features/cases/__tests__/hooks.test.tsx` と `frontend/src/features/cases/components/__tests__/CaseListPage.test.tsx` の sampleCase に `latestSendoff: null` を各1行追加する。これは必須 API フィールド追加へのfixture追従で、FE実装・assert変更ではない。指示書の frontend 無変更からの例外として明記。RED実出力 `/tmp/approval-api-preflight.log`。

`tests/integration/test_api_records.py` の案件一覧 tuple 検証も旧3要素から4要素（送付判断 None）へ更新。全体初回はこの旧展開が 1 failed / 743 passed となった。既存の案件ID・進捗・最新版IDの期待値は維持。

## AD-029 の反映箇所

以下は `backend/` 相対。

| 決定 | 反映 file:line |
|---|---|
| ① | `app/api/ui/schemas/versions.py:28`: 既存 #22 に7必須フィールドを追加。非生成 FE の VersionListItem 参照は着手時0件 |
| ② | `app/api/ui/endpoints/versions.py:36`: ApprovalService に DI 切替。旧 RecordService/Repository の list_versions は保持 |
| ③ | `app/services/version_state.py:49` / `approval_service.py:93`: BE Service が2フラグを付与。endpointは値を写すだけ |
| ④ | `app/services/version_state.py:55`: 最新イベントが review→staff のときだけ再確認。許可された遷移列との同値性をdocstringに記載 |
| ⑤ | `app/services/version_state.py:49`: 最新 bounce と T-501 の latest_review_checked_at を比較。時刻同一は false |
| ⑥ | `app/api/ui/endpoints/approvals.py:28`: #28 の7配列、取消済みを含めRepository順序を維持 |
| ⑦ | `app/api/ui/schemas/approvals.py:80`: ConfirmationHistoryRecord が既存 ConfirmationRecord に取消情報を追加。#31応答は変更なし |
| ⑧ | `app/api/ui/endpoints/approvals.py:25` / `app/api/dependencies.py:35` / `app/api/ui/router.py`: 新規endpoint/DTO・共通DI・router登録 |
| ⑨ | `app/api/errors.py:48`: 新7コードのHTTP表を一元追加 |
| ⑩ | `app/api/ui/schemas/approvals.py:22`: domain Input を第一基底に保持し、rollback禁止を既存 invalid_request→表の経路で422に写す |
| ⑪ | `app/api/ui/schemas/approvals.py:34`: 空文字reasonをNoneに正規化。hold/approvedはdomain理由必須に到達 |
| ⑫ | `app/api/ui/endpoints/approvals.py:74`: #34〜37は201、record_responseでIDを改名。#36は返値契約によりBounceCreatedRecord（comments無し） |
| ⑬ | `app/repositories/case_repository.py:77` / `app/services/case_service.py` / `app/api/ui/endpoints/cases.py`: 最新確定版の最新sendoffを相関subqueryで取得。案件一覧全体でSELECT2回固定 |
| ⑭ | `app/api/ui/schemas/versions.py:28`: elapsedSecは追加なし（T-603） |
| ⑮ | `tests/unit/test_api_path_separation_live.py:13` / `tests/unit/test_approval_api.py`: 新5組の存在、agent側POST404・Service未呼出。route_contractと汎用パス分離検査は変更なし |
| ⑯ | `app/api/ui/endpoints/versions.py:76`: #23は変更なし。SCR-06向け対応表は下記 |
| ⑰ | `app/main.py`: 差分なし。405本文の扱いは対象外 |
| ⑱ | `tests/integration/test_api_approvals.py`: 未照合の実ID・row_code・coverageRecordedをHTTPレスポンスで完全一致検査 |

## レビュー対応

共通環境 `AGENT_MODE=local_dummy DEBUG=false CI=true`。root Makefile に `/tmp/approval-api-checks.mk` を追加して高速RED/GREENを実行。外部モデルを使わず、pytest/jestは逐次実行。

| 項目 | 変更 file:line | RED テスト・コマンド・件数 | 変異1行 |
|---|---|---|---|
| エラー表・要求DTO・5ルート | `app/api/errors.py:48` / `app/api/ui/schemas/approvals.py:22` / `endpoints/approvals.py:28` | `test_approval_error_status_registry` とHTTP契約群、`make -f Makefile -f /tmp/approval-api-checks.mk approval-api-unit`: 初回7 failed / 29 errors（7コード未登録、DI未実装）。実装後36 passed | E_STATE_ORDERの登録行を削除→2 failed / 35 passed |
| 必須nullable・露出制限 | `app/api/ui/schemas/versions.py:28` / `schemas/cases.py:40` | HTTPキー完全一致・再帰camelCase・private/versionId非露出。OpenAPI requiredの追記後 `approval-api-unit` 37 passed | 上記エラー行削除をHTTPまで検出。必須フィールドはschema.requiredで検証 |
| bounced / needsRecheck | `app/services/version_state.py:49` / `approval_service.py:93` | `test_bounced_compares_latest_bounce_and_last_review` / `test_needs_recheck_requires_corrective_transition` / `test_version_list_derives_flags_without_mutating_repository_material`、`approval-api-state`: 11 failed / 27 passed → 38 passed | from_state条件削除→1 failed / 37 passed、時刻比較反転→3 failed / 35 passed |
| #1の最新送付判断・#22導出 | `app/repositories/case_repository.py:77` / `app/services/case_service.py` | `test_case_latest_sendoff_uses_latest_finalized_version_and_constant_queries` と実DI lifecycle、`approval-api-integration`: 初回2 failed / 1 passed→3 passed。1件はfixtureのrow_codeをR1と誤記した期待値で、実row_code参照に修正 | sendoff ORDER BYを昇順へ→1 failed / 2 passed |
| 既存契約の追従 | 既存record/caseテスト・FE fixture2行 | 全体初回1 failed / 743 passed（旧tuple展開）とtsc TS2741計8エラーを修正。元のID/進捗検証を保持 | 取消・versionId・derived flagの実応答assertは削除なし |

## T-503 へ渡す契約

#22 `GET /cases/{caseId}/versions` の `versions[]` は次の13キーを必須で返す:
`versionId`, `versionNo`, `currentState`, `finalizedAt`, `isComplete`, `createdAt`, `unresolvedCount`, `carryOver`, `latestStateEvent`, `latestBounce`, `latestSendoff`, `bounced`, `needsRecheck`。

`carryOver` の5キーは `editCount`, `rowMatchConfirmed`, `rowMatchTotal`, `coverageRecorded`, `judgementCount`。latest3種はnull可。`latestBounce.comments=[]` は版一覧の要約であり、行コメント本文は#28から取得。`bounced` は最新差し戻しがあり、最新評価確認が無いか差し戻しより前のときtrue。`needsRecheck` は最新イベントが review_checked→staff_checked のときtrue。

#28 `GET /versions/{versionId}/records` の7キーは `edits`, `confirmations`, `judgements`, `stateEvents`, `bounces`, `unlinkedComments`, `sendoffDecisions`。各配列は日時・ID昇順、取消済みも含む。`bounces[].comments` に紐付け済みコメント、`unlinkedComments[].bounceId=null`。

| SCR-06の値 | 取得元・条件 |
|---|---|
| 業務状態・明細数・未解決数・照合済み数・訂正件数 | #23 `currentState` / `counts.itemCount` / `counts.unresolvedCount` / `counts.matchedCount` / `counts.editCount` |
| 網羅性記録の有無 | #23 `coverageConfirmed`（#22 `carryOver.coverageRecorded`とも一致） |
| 網羅性確認者・日時・取消用ID | #28 `confirmations` の `kind='coverage' && undoneAt===null` から recordedBy/recordedAt/confirmationId |
| 担当者確認・評価確認の記録者・日時 | #28 `stateEvents` の toState 別の最新行。#22 latestStateEvent は最後の状態イベントだけ |
| 差し戻しコメント件数 | #28 `unlinkedComments.length`（未紐付けコメント数。紐付け済みの履歴コメントは加算しない） |
| 最新差し戻し・送付判断 | #22 `latestBounce` / `latestSendoff`（履歴・コメントは#28） |
| 差し戻し中・再確認必要 | #22 `bounced` / `needsRecheck`をそのまま表示。FEで時刻比較を再実装しない |
| 最新状態の要約と引継ぎ件数 | #22 `currentState` / `unresolvedCount` / `carryOver` |
| 訂正・判断・差し戻し・送付判断の履歴 | #28各配列。対象行の現在値・質問情報は既存#24/#26 |

案件一覧 #1 に `latestSendoff: 'undecided'|'hold'|'approved'|null` を必須追加。最新版に送付判断が無ければnull（旧版の判断を継承しない）。`progressStatus` / `latestVersionId`は既存定義のまま。

#34〜37 は `recordedBy` 必須・recordedAtは送らない。#36入力は recordedBy のみ、201応答は `bounceId,reason,recordedBy,recordedAt`。#35応答のbounceIdはnull、後から#28で紐付けを取得。#37 reasonの空文字はNone扱い、hold/approvedは理由必須。

| コード | HTTP |
|---|---|
| E_STAFF_CHECK_INCOMPLETE | 409 |
| E_COVERAGE_NOT_RECORDED | 409 |
| E_STATE_ORDER | 409 |
| E_STATE_ROLLBACK_FORBIDDEN | 422 |
| E_NO_BOUNCE_COMMENT | 409 |
| E_SENDOFF_REASON_REQUIRED | 400 |
| E_COMMENT_REQUIRED | 400 |

未照合時のdetails: `unmatchedItemIds`（実ID昇順）、`unmatchedRowCodes`（同順）、`coverageRecorded`。draft版のbounce拒否はE_STAFF_CHECK_INCOMPLETEだが、このdetailsを持たない。成功DTOはversionId/createdAt/private属性を含めない（#22自身の既存versionId/createdAtは維持）。

## 生成・最終ゲート

```text
models 146 -> 165
added: bounceCommentRecord.ts, bounceCommentRequest.ts, bounceCreatedRecord.ts, bounceRecord.ts, bounceRequest.ts, carryOverResponse.ts, caseListItemLatestSendoff.ts, confirmationHistoryRecord.ts, confirmationHistoryRecordKind.ts, recordsResponse.ts, sendoffDecisionRecord.ts, sendoffDecisionRecordDecision.ts, sendoffDecisionRequest.ts, sendoffDecisionRequestDecision.ts, stateEventRecord.ts, stateEventRecordFromState.ts, stateEventRecordToState.ts, stateEventRequest.ts, stateEventRequestToState.ts
removed: 
/api/v1/ui/cases: operationId unchanged=True (list_cases_api_v1_ui_cases_get)
/api/v1/ui/cases/{caseId}/versions: operationId unchanged=True (list_versions_api_v1_ui_cases__caseId__versions_get)
GET records: ui=1, agent=0, tags=[['ui']]
POST state-events: ui=1, agent=0, tags=[['ui']]
POST bounce-comments: ui=1, agent=0, tags=[['ui']]
POST bounces: ui=1, agent=0, tags=[['ui']]
POST sendoff-decisions: ui=1, agent=0, tags=[['ui']]
```

`AGENT_MODE=local_dummy DEBUG=false CI=true make check` 実出力（全文 `docs/test-results/approval-api-final-check-2026-09-14.log`）:

```text
745 passed, 172 warnings in 66.51s (0:01:06)
✅ check-be: backend green
All matched files use Prettier code style!
Test Suites: 24 passed, 24 total
Tests:       327 passed, 327 total
Snapshots:   0 total
Time:        21.607 s
✅ check: all green
```

T-501 の694から BE **745 passed**（+51）。FE **24 suites / 327 passed**。4変異すべて検出。生成モデル146→165（追加19・消失0）、#1/#22 operationId維持、新5組はUI各1・AGENT0。ルート契約・汎用パス分離・main・AGENT・適用済みmigration・memoryに変更なし。FE差分は記載した既存fixture2行のみ。commitなし。

レビュー用境界: `/tmp/approval-api-baseline.json` はT-502着手時のapp全ファイル内容。T-501 の未commit差分との照合に利用可能。対象テストへの追加と既存期待値の追従は上記表参照。

## 再レビュー依頼（T-502）

## 独立レビュー（T-502・第1回）

RV 候補:
- T-502 独立レビュー: P1 0 / P2 1 / P3 0。API実装の不具合は検出せず、引継ぎ必須項目の記載不足1件。
- AD-029 ①〜⑱の実装・HTTP/実DI・型/機密境界・N+1なし・既存テスト保全を確認。make check は BE 745 / FE 327、24 suites で再現。
- DONE 保留: T-503 契約表へ「差し戻しコメント件数 = #28 unlinkedComments.length」を補記する。コード修正不要。

P2-1（文書のみ）: `docs/t502-handoff.md:75` の SCR-06 要約カード対応表に「差し戻しコメント件数」の取得元が無い。指示書 §6 は要約カード各値の取得元を要求している。確定済み `docs/t503-instructions.md:16`（AD-031 ⑥）では **#28 `unlinkedComments.length`（未確定コメント件数）** であり、紐付け済みコメントの総数とは異なる。表にこの1行を追加し、後続実装が履歴全件を数えないようにする。

確認結果（パスは backend/ 相対）:

| AD-029 | 独立照合 |
|---|---|
| ① | `app/api/ui/schemas/versions.py:28` 必須7フィールド。非生成FE参照なし、HTTPとOpenAPI required検査あり |
| ② | `app/api/ui/endpoints/versions.py:36` ApprovalServiceへ切替。旧list_versionsは保持 |
| ③ | `app/services/approval_service.py:93` BEで導出しendpointは写すだけ |
| ④ | `app/services/version_state.py:55` review→staff条件・同値性docstring・真理値表あり |
| ⑤ | `app/services/version_state.py:49` 最新評価確認時刻との比較。T-501の材料は維持 |
| ⑥ | `app/api/ui/endpoints/approvals.py:28` 7配列・取消情報・コメント内包・Repositoryの順序維持 |
| ⑦ | `app/api/ui/schemas/approvals.py:80` ConfirmationHistoryRecord新設、既存#31不変 |
| ⑧ | `app/api/dependencies.py:35` / `app/api/ui/router.py:23` 正規DI・UI登録、実DIはget_dbのみoverride |
| ⑨ | `app/api/errors.py:48` 新7コードのHTTP対応を一元化 |
| ⑩ | `app/api/ui/schemas/approvals.py:22` domain Input→StrictRequest、toState欠落/禁止値は既存表経由422 |
| ⑪ | `app/api/ui/schemas/approvals.py:34` 空reason→None、domain validatorでhold/approved拒否 |
| ⑫ | `app/api/ui/endpoints/approvals.py:74` 201・record_response。#36 comments省略は許容されたT-501戻り値分岐 |
| ⑬ | `app/repositories/case_repository.py:80` 最新確定版への相関subquery、時刻/id降順、案件数が増えても一覧SELECT2回 |
| ⑭ | `app/api/ui/schemas/versions.py:28` 生成所要は追加なし |
| ⑮ | `tests/unit/test_api_path_separation_live.py:13` 5組存在。unitでAGENT POST404・Service未呼出、禁止ファイル不変 |
| ⑯ | `app/api/ui/endpoints/versions.py:76` #23不変。引継ぎ表はP2-1の1項目のみ不足 |
| ⑰ | `app/main.py` baselineと同一 |
| ⑱ | `tests/integration/test_api_approvals.py:136` 実HTTPで未照合実ID・rowCode・coverageRecorded完全一致 |

T-502開始時 `/tmp/approval-api-baseline.json` と現行appを比較し、T-501差分と分離してレビューした。main・AGENT・route_contractに変更なし。汎用パス分離テストにdiffなし。既存テスト変更はDI/tuple/fixture追従で旧期待値を保持。FEの2行追加とtsc TS2741のRED記録も照合した。REDおよび4変異のログを確認したが、レビューでのコード変異は行っていない。

品質ゲート: 名前のみの `pgrep -l 'pytest|jest'` が該当なしであることを確認してから、rootの `AGENT_MODE=local_dummy DEBUG=false CI=true make check` を1回、単独実行。exit 0。

```text
745 passed, 172 warnings in 65.21s (0:01:05)
✅ check-be: backend green
Test Suites: 24 passed, 24 total
Tests:       327 passed, 327 total
Time:        23.333 s
✅ check: all green
```

ログ: `/tmp/approval-api-independent-review-check.log`。生成モデル146→165（追加19・消失0）を保存済み前件リストと照合。新5経路はUI各1・AGENT0、tagはui、#1/#22 operationId維持。応答の宣言フィールド限定・camelCase・時刻/内部属性の境界を確認。秘密ファイル読取・実モデル実行・memory編集・commitなし。

DONE 可否: **保留（P2-1の文書補記のみ。コード修正は不要）**。

## レビュー対応（第1回 P2-1）

| 指摘 | 変更内容 | 検証 |
|---|---|---|
| P2-1 | 本handoff「T-503へ渡す契約」の要約カード対応表に、差し戻しコメント件数 = #28 `unlinkedComments.length` を1行追加。紐付け済み履歴を含めないことも明記 | 独立レビューで欠落を検出（文書RED）。コード・テストは変更なし。実装と第1回独立のmake checkはBE745/FE327でgreen |

第1回独立検証ログ: `docs/test-results/approval-api-independent-review-check-2026-09-14.log`。

## 再レビュー依頼（T-502）

## 独立レビュー（T-502・第2回）

RV 候補:
- T-502 第2回独立レビュー: P1 0 / P2 0 / P3 0。第1回 P2-1（引継ぎ表の差し戻しコメント件数欠落）をクローズ。
- `docs/t502-handoff.md:81` は #28 `unlinkedComments.length` と履歴コメントの除外を明記し、AD-029 ⑯・AD-031 ⑥に一致。対象コード14ファイルは第1回レビューの SHA-256 と全件一致。
- root の `AGENT_MODE=local_dummy DEBUG=false CI=true make check` を単独で1回実行し exit 0、BE 745 / FE 327・24 suites を再現。DONE 可。

P2-1 クローズ根拠: `docs/t502-instructions.md:25`（§0 ⑯）・同 `:109`（完了条件）が要求する要約カード対応表に、`docs/t502-handoff.md:81` の1行が追加された。取得式と対象範囲は `docs/t503-instructions.md:16`（§0 ⑥）、`docs/requirements/03-spec.md:377` の未確定コメントの定義、`docs/requirements/05-api-ipo.md:613` の `bounceId=null` の契約に一致する。紐付け済み履歴コメントを足さないことも明記されており、文書の欠落は解消した。

実装との照合: `backend/app/repositories/record_repository.py:447` は `bounce_id=None` の集合だけを返し、`backend/app/api/ui/endpoints/approvals.py:58` がそのまま #28 に写す。`backend/tests/integration/test_api_approvals.py:76`〜`:80` の実HTTP検証は、差し戻し後に履歴へコメントが残り `unlinkedComments == []` になることを確認している。今回の全体ゲートでも当該テストを含めて通過。コード変更を伴わない文書修正のため、テスト追加・変異・実装修正は行っていない。

再現結果: 実行前に名前のみの `pgrep -l 'pytest|jest'` が該当なし（exit 1）を確認し、root の指定コマンドを1回実行した。ログは `/tmp/approval-api-rereview-check.log`。

```text
185 files left unchanged
745 passed, 172 warnings in 68.27s (0:01:08)
✅ check-be: backend green
All matched files use Prettier code style!
Test Suites: 24 passed, 24 total
Tests:       327 passed, 327 total
Snapshots:   0 total
Time:        22.529 s
✅ check: all green
```

P1: 0件。P2: 0件。P3: 0件。秘密ファイル読取・実モデル実行・memory編集・commitなし。

DONE 可否: **DONE 可（第1回 P2-1 クローズ、残指摘なし）**。

## 独立レビュー後の記録（未転記・未commit）

第2回は P1/P2/P3 各0、DONE可。ゲートをBE745/FE327で再現し、対象コード14ファイルは第1回から不変。永続ログ `docs/test-results/approval-api-rereview-check-2026-09-14.log`。希望Statusは T-502 DONE。第1回／第2回のRV候補は上記3行要約を転記案として保持（未転記T-501 RV-045候補に続く RV-046/047 候補、実適用時再採番）。memory編集とcommitはユーザー明示禁止により実施しない。

学び候補: 後続画面向け取得元表は確定したカード値を全件列挙し、履歴総数と現在の未紐付け数を区別する。既存LNと重複する場合は追加不要。次の作業は§7のT-601。
