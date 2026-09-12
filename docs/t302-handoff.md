# T-302 handoff

§7 2026-09-13 07:05版に従い、L-7提出後に着手。Status: REVIEWING。§7 08:20版のfixture例外を適用し、L-8と合わせた全体ゲートはBE567件 / FE166件PASS。

## 調整履歴: T-302 例外（orchestrator 許可）

初回make checkはBE563件PASS後、必須nullableの`latestVersionId`不足でFE fixtureにTS2741が7箇所発生。§7 **2026-09-13 08:20版**でfixture追従2行が許可されたため、以下を適用した。契約のoptional化、テスト本文・assert・FEプロダクトコードの変更はない。

- `frontend/src/features/cases/__tests__/hooks.test.tsx:39`: sampleCaseへ`latestVersionId: null`。
- `frontend/src/features/cases/components/__tests__/CaseListPage.test.tsx:43`: sampleCaseへ`latestVersionId: 1`。
- [適用差分](test-results/record-api-fixture-proposal-2026-09-13.diff)。

### ここまでの検証

- [HTTP RED](test-results/record-api-red-2026-09-13.log): 未実装DIにより21 ERROR。
- [読取/経路 RED](test-results/record-api-read-red-2026-09-13.log): 7 FAIL / 5 PASS。
- [対象GREEN](test-results/record-api-green-2026-09-13.log): HTTP21 PASS、既存5件を含む読取等12 PASS。
- [変異](test-results/record-api-mutation-2026-09-13.log): E_ALREADY_UNDONEのstatus表エントリを子プロセス内で除去 → 409期待が400となり1 FAIL / 3 PASS。
- [全体ゲート途中結果](test-results/record-api-regression-2026-09-13.log): **563 passed, 166 warnings in 35.96s**。OpenAPI/orval成功、tscが上記7件で失敗。FE lint/Jestは今回の全体ゲートでは未到達。
- 生成modelは **85→137（追加52、削除0）**。[追加型一覧](test-results/record-api-model-diff-2026-09-13.json)。既存型の消失なし。
- 既存のT-205変更を保全し、T-302ではapp/agentを変更していない。memory未編集・commitなし。

## 変更ファイル（着手前宣言からの確定一覧）

- T-302本体: `backend/app/api/ui/schemas/versions.py` / `records.py`、`ui/endpoints/versions.py` / `records.py`、`ui/router.py`、`app/api/dependencies.py`、`app/api/errors.py`。
- T-301由来の読取拡張: `backend/app/repositories/record_repository.py` / `services/record_service.py`。
- T-101/102由来の読取拡張: `backend/app/repositories/case_repository.py` / `services/case_service.py`、`api/ui/schemas/cases.py` / `endpoints/cases.py`。
- **共有 `backend/app/api/common/route_errors.py` をT-302で変更する**（AD-022①の非構造違反のstatus表参照）。
- テスト: `backend/tests/unit/test_record_api.py` / `test_api_path_separation_live.py`、`tests/integration/test_api_records.py`、`backend/tests/unit/test_case_service.py`（進捗4状態を追加）。
- 本handoffと`docs/test-results/`の証跡。

`app/agent/**`、T-301の書込処理、FEは上記許可されたfixture 2行のみ変更した。`.claude/memory.md`は編集しない。OpenAPI/orvalの生成型は変更前一覧を保存して前後差を記録する。commitしない。

## 実装とレビュー対応

| 項目 | 変更 file:line | REDを確認したテスト名・コマンド・件数 |
|---|---|---|
| 本体: DTO・5書込 | `backend/app/api/ui/schemas/records.py:15`、`endpoints/records.py:29`。domain Inputを第一基底、StrictRequestを第二基底にしてcamelCase入力/業務コードを維持。POST登録201、取消200。日時は応答だけ、noteの空文字はNone | `test_edit_201_quantity_pair_and_server_timestamp`、`test_other_record_routes_and_blank_judgement_note`、入力契約7ケースほか。record-api-unitの初回21 ERROR→21 PASS |
| 本体: 5参照・パス | `api/ui/schemas/versions.py:57,69`、`endpoints/versions.py:28,36`、`ui/router.py`。#22最小と#23〜26をUIだけに追加。itemsは明示的な応答項目のみに絞り、原値・全履歴・Decimal文字列を返す | `test_current_items_preserve_raw_history_and_decimal_strings`、`test_questions_keep_judged_unresolved_and_null_latest`、`test_all_version_and_record_routes_exist_under_ui`、agent側POST404。パス存在検査はRED→GREEN |
| 本体: DI/エラー表 | `api/dependencies.py:32` / `api/errors.py`。RecordServiceを組み立て、新業務コードを1表へ追加 | `test_service_error_status_and_camel_details`（404/409/409/400）、`test_row_confirmation_requires_target`。E_ALREADY_UNDONEの行を消す変異で1 FAIL |
| **共有route_errors** | `api/common/route_errors.py:29`をT-302で変更。構造違反の422は維持し、非構造違反だけstatus表を参照。E_FIELD_NOT_EDITABLEは422、recordedAtの余分入力は400 | `test_input_business_and_structural_error_contracts`。snake_caseは422のE_REQUEST_INVALID、非構造のgrade_rawは422のE_FIELD_NOT_EDITABLEを実HTTPで確認 |
| **T-301由来・読取のみ** | `repositories/record_repository.py:205,232` / `services/record_service.py:154,157`。summaryにversion情報とCaseHeaderを追加（既存version()＋CaseHeader select）。確定版一覧を提供 | `test_edit_read_undo_preserves_source_history_and_summary`。実HTTPでgrade訂正201→原値保持→取消200→元の値/履歴保持→editCount=editedItemCount=0。header・版情報と日時TZも確認 |
| **T-101/102由来・読取のみ** | `repositories/case_repository.py:76` / `services/case_service.py:78`、`api/ui/schemas/cases.py:48` / `endpoints/cases.py:63`。確定済み最新版だけを取得し、進捗4語彙とlatestVersionIdを導出 | `test_case_progress_uses_latest_finalized_version`（4状態）、`test_latest_case_version_and_version_list_ignore_unfinalized`。新しい未確定版を除外し、確定版2→1の順序と最新IDを実DBで確認。record-api-read: 7 FAIL / 5 PASS→12 PASS |

テスト追加は28件（HTTP21＋ケース進捗4＋パス1＋実DB2）。既存テストの削除・assert除去はしていない。`test_api_path_separation.py` / `test_single_source_of_truth.py` / `route_contract.py`は未変更。T-302の`app/agent/**`差分も無しを確認済み。

### Make入口

```sh
cp docs/test-results/record-api-checks-2026-09-13.mk /tmp/record-api-checks.mk
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-api-checks.mk record-api-unit
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-api-checks.mk record-api-read
cp docs/test-results/record-api-mutation-2026-09-13.txt /tmp/record-api-mutation.py
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-api-checks.mk record-api-mutation
```

変異は意図的な失敗（make exit 2、pytest 1 FAIL）が正。共有ソースを変更せず、子プロセス内のエラー対応表だけを変える。最終完了判定は除外なしの`AGENT_MODE=local_dummy DEBUG=false CI=true make check`による。

## OpenAPIの追加10ルート

```text
POST /api/v1/ui/versions/{versionId}/edits
POST /api/v1/ui/versions/{versionId}/edits/{editId}/undo
POST /api/v1/ui/versions/{versionId}/confirmations
POST /api/v1/ui/versions/{versionId}/confirmations/{confirmationId}/undo
POST /api/v1/ui/versions/{versionId}/questions/{questionId}/judgements
GET /api/v1/ui/cases/{caseId}/versions
GET /api/v1/ui/versions/{versionId}
GET /api/v1/ui/versions/{versionId}/items
GET /api/v1/ui/versions/{versionId}/items/{itemId}/evidence
GET /api/v1/ui/versions/{versionId}/questions

```

## orval modelの前後差

変更前85ファイル→変更後137ファイル。追加52、削除0。生成フォルダはgit管理外。追加名:

```text
caseHeaderResponse.ts
caseHeaderResponseCustomerNameState.ts
caseHeaderResponseDueBasis.ts
caseHeaderResponseDueGranularity.ts
caseHeaderResponseDueState.ts
caseHeaderResponseIncotermsState.ts
caseHeaderResponseInquiryNoState.ts
caseHeaderResponsePlaceState.ts
caseHeaderResponseQuoteDeadlineTzState.ts
confirmationRecord.ts
confirmationRecordKind.ts
confirmationRequest.ts
confirmationRequestKind.ts
confirmationUndone.ts
editUndone.ts
editsResponse.ts
evidenceResponse.ts
itemCurrentResponse.ts
itemCurrentResponseConnectionState.ts
itemCurrentResponseDueState.ts
itemCurrentResponseGradeState.ts
itemCurrentResponseLengthState.ts
itemCurrentResponseOdState.ts
itemCurrentResponsePlaceState.ts
itemCurrentResponseQtyState.ts
itemCurrentResponseWallState.ts
itemCurrentResponseWeightState.ts
itemEditRecord.ts
itemEditRecordField.ts
itemEditRecordNewState.ts
itemEditRecordOldState.ts
itemEditRequest.ts
itemEditRequestField.ts
itemEditRequestNewState.ts
itemEvidenceResponse.ts
itemsResponse.ts
judgementRecord.ts
judgementRecordResolution.ts
judgementRecordStatus.ts
judgementRequest.ts
judgementRequestResolution.ts
judgementRequestStatus.ts
questionResponse.ts
questionResponseCategory.ts
questionsResponse.ts
undoRequest.ts
versionCounts.ts
versionListItem.ts
versionListItemCurrentState.ts
versionResponse.ts
versionResponseCurrentState.ts
versionsResponse.ts
```



## 最終全体ゲート

`AGENT_MODE=local_dummy DEBUG=false CI=true make check` → **exit 0 / all green**。

- BE **567 passed, 166 warnings**。ruff・開発/テストDBのmigration/索引確認PASS。
- OpenAPI export → orval → tsc → eslint PASS。
- FE **15 suites / 166 tests PASS**。上記fixture 2行の型エラーは解消した。
- [全出力](test-results/startup-record-regression-2026-09-13.log)。初回563件からL-8の4ケースが加わった。L-8の変更・RED・変異・既存lifespanテスト追従は`docs/t205-handoff.md`冒頭に分けて記録した。
- T-302の既存テスト変更は許可されたfixture 2行のみ。ケースServiceテストは新規4ケースの追加。必須nullable契約、既存assert、SSOT・パス分離検査は維持。実モデル呼出し・memory編集・commitなし。

## 再レビュー依頼（T-302）

T-302のAPI・読取拡張と、orchestrator許可のfixture追従2行を提出します。全体ゲートは除外なしで成功。§7の更新まで待機します。
