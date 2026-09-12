# T-302 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-302【API】G3 参照 #23〜#26 / 記録 #29〜#33**（memory §3）。依存 T-301（DONE 後に着手。T-301 レビュー結果で Service 契約が変わり得るため、着手時に §0 の表を実コードで再確認）。
設計の正: 05-api-ipo.md（0.2〜0.4・1章 E/F・FLOW-03・3.6・5章・6章・7.1）、04-db.md §3.4/§3.6、03-spec.md SCR-03/SCR-04。前提決定: t301-instructions §0、AD-017/AD-018、**本書 §0（AD-022）**。

## 0. orchestrator 決定（AD-022・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| 1 | `E_FIELD_NOT_EDITABLE` の 422（05 §6）と現行 `route_errors.invalid_request` の 400 固定 | **案 A**: `invalid_request` は非 structural のとき `DOMAIN_ERROR_STATUS_BY_CODE.get(code, 400)` を使い、`errors.py` に `E_FIELD_NOT_EDITABLE: 422` を置く（表は 1 箇所のまま・CV-015）。`route_errors.py` は共有ファイルなので handoff に「T-302 で触った」と明記 |
| 2 | #23 が要する版の状態（`currentState`/`finalizedAt`/`versionNo`/`caseId`）と案件メタ（`case_headers`） | **T-302 で `RecordService.summary` を読取専用に拡張してよい**（T-301 由来の小変更として handoff に file:line を分けて書く。Repository は既存 `version()` を使い、`CaseHeader` は select 1 本追加） |
| 3 | AD-013 の「#1 を versions から拡張」 | **T-302 に含める**: `CaseListItem` に `progressStatus` の導出（確定版なし→`intake`、あり→`draft_review`、`current_state` が `staff_checked`/`review_checked` → その値）と `latestVersionId`（確定済み最新版の ID。無ければ null）を追加。`CaseService`/`CaseRepository` の読取変更は許可（T-101/102 由来の変更として分けて書く） |
| 4 | 案件 → versionId の到達経路 | **#22 の最小版を T-302 に前倒し**: `GET /cases/{caseId}/versions` → `[{versionId, versionNo, currentState, finalizedAt, isComplete, createdAt}]`（確定済みのみ・新しい順）。carryOver・生成所要は T-502 で拡張 |
| 5 | 「訂正 n」の意味 | 両方返す: `editCount`（未取消の記録行数）と `editedItemCount`（訂正のある明細数） |
| 6 | 05 3.6 の数量表記 | 実装語彙（`newState="numeric"` ＋ `qtyUnit`）に 05 を書き戻し済み |
| 7 | #32 パス変数 / undo の status | `{confirmationId}` に統一（05 書き戻し済み）。undo は **200**（UPDATE。05 0.4 に追記済み） |
| 8 | #25 の資料名 | FE が #4（資料一覧）で解決。T-302 では `documentId` のみ |
| 9 | `item_ends`（両端仕様） | 初版 #24 に含めない。SCR-04 で必要になれば T-303 前に追補（TODO-024） |
| 10 | 応答の数値表現 | `Decimal` → JSON 文字列（05 0.4 に追記済み） |
| 11 | `kind` 語彙違反が `E_TARGET_INVALID` になる | 許容 |
| 12 | `JudgementInput.note` の空文字 | DTO で `""` → `None` に正規化 |
| 13 | 422 の形（TODO-005） | 422 も `{code,message,details}` 形で `code` 必須（05 0.2 に追記済み）。既存の `endpoints_reference.py` の code なし 422 は触らない（C-3 で） |

---

## 1. 範囲と範囲外

**範囲（API 層＋§0 で許可した読取拡張）**
- DTO: `app/api/ui/schemas/versions.py`（#22 最小・#23〜#26 応答）・`app/api/ui/schemas/records.py`（#29〜#33 要求/応答）。配置は CODEX-INSTRUCTIONS §3。ファイル名にチケット ID を入れない（CV-017）
- endpoint: `app/api/ui/endpoints/versions.py`（GET #22 最小・#23〜#26）・`app/api/ui/endpoints/records.py`（POST #29〜#33）。`app/api/ui/router.py` に include。`app/api/agent/router.py` は触らない
- DI: `app/api/dependencies.py` に `get_record_service(session) -> RecordService(RecordRepository(session))`（`get_draft_service` と同型）
- `app/api/errors.py` の `DOMAIN_ERROR_STATUS_BY_CODE` に新コード追記（§4）。`app/api/common/route_errors.py` の `invalid_request` を「非構造違反は表を参照」に変更（§0 ①・共有ファイルなので handoff に明記）
- §0 ②③④ の読取拡張: `RecordService.summary` に版の状態（`current_state`/`finalized_at`/`version_no`/`case_id`/`is_complete`）と `CaseHeader` を含める / `CaseService.list_cases` の `progressStatus` 導出と `latestVersionId` / `GET /cases/{caseId}/versions` 最小版の Repository/Service。**T-301・T-101/102 由来の変更として handoff で file:line を分けて書く**
- 統合ポイント: OpenAPI → orval → typecheck（`make check` が内包）
- テスト: `tests/unit/test_record_api.py`（Service mock）＋ `tests/integration/test_api_records.py`（実 HTTP 1 本）＋ パス存在の assert

**範囲外**: 画面（T-303。`frontend/src` は編集しない）、状態遷移・`version_state_events`（T-501・TODO-019）、#27/#28/#34〜#37/#40、`app/agent/**`（人の記録をツールに足さない）。

## 2. DTO（camelCase・CV-010/011/012）

- 要求は `common/schemas/drafts.py` の `StrictRequest`（`extra="forbid"`）を第二基底、**domain の Input を第一基底**（`ItemEditRequest(ItemEditInput, StrictRequest)`）にして `field_error_codes` の業務コードを API 層に出す。応答は `CamelModel`。語彙は `Literal` で二重に（CV-010）
- `numeric` 値は `Decimal` 型 → JSON 文字列（05 0.4）。`recordedAt`/`undoneAt` は応答のみ（入力に置かない）
- **#22 最小** `GET /cases/{caseId}/versions` → `{ versions: [{ versionId, versionNo, currentState, finalizedAt, isComplete, createdAt }] }`（確定済みのみ・新しい順）
- **#23** `GET /versions/{versionId}` → `{ versionId, caseId, versionNo, currentState, isComplete, finalizedAt, caseHeader: {…case_headers の値と状態…} | null, counts: { itemCount, questionItemCount, tbaItemCount, choiceGroupCount, matchedCount, editCount, editedItemCount, unresolvedCount }, coverageConfirmed }`（03-spec SCR-03 の 7 件数と 1 対 1。遷移可否の判定はしない・CV-009）
- **#24** `GET /versions/{versionId}/items` → `{ items: [ItemCurrentResponse] }`。`ItemCurrentResponse` は items の全列をホワイトリストで写す（`versionId`/`createdAt` を出さない）＋ `*Raw` を現在値と別キーで必ず返す ＋ `history: [ItemEditRecord]`（取消済み含む）。`ItemEditRecord`: `editId, itemId, field, oldValue, oldState, newValue, newState, reason, recordedBy, recordedAt, undoneAt, undoneBy`
- **#25** `GET /versions/{versionId}/items/{itemId}/evidence` → `{ itemId, evidences: [{ evidenceId, field, rawValue, adoptedValue, documentId, locator, quote, appliedCondition, conversionNote, changeReason, priorValue }] }`（資料名は FE が #4 で解決）
- **#26** `GET /versions/{versionId}/questions` → `{ questions: [{ questionId, questionCode, itemId|null, targetField, reason, candidates, category, latest: { judgementId, questionId, status, resolution, note, recordedBy, recordedAt } | null }] }`
- **#29** `POST /versions/{versionId}/edits` 201 → `{ edits: [ItemEditRecord] }`。要求 `{ itemId, field, newValue?, newState?, qtyUnit?, reason, recordedBy }`
- **#30 / #32** `POST …/edits/{editId}/undo` / `…/confirmations/{confirmationId}/undo` 200 → `{ editId|confirmationId, undoneAt, undoneBy }`。要求 `{ recordedBy }`
- **#31** `POST /versions/{versionId}/confirmations` 201 → `{ confirmationId, kind, itemId, recordedBy, recordedAt }`。要求 `{ kind, itemId?, recordedBy }`
- **#33** `POST /versions/{versionId}/questions/{questionId}/judgements` 201 → `JudgementRecord`。要求 `{ status, resolution, note?, recordedBy }`（`note` の `""` は None に正規化）
- **#1 拡張**: `CaseListItem` に `latestVersionId: int|null` を追加し、`progressStatus` を導出（確定版なし→`intake`、あり→`draft_review`、`current_state` が `staff_checked`/`review_checked` → その値）。05 §1 #1 の注記と AD-013 を更新するのは Claude

## 3. パス分離

- 全て `app/api/ui/router.py` 配下（`/api/v1/ui/...`）。`edits`/`confirmations`/`judgements` は `tests/fixtures/route_contract.py` の `UI_ONLY_SEGMENTS` に既登録 → `test_api_path_separation.py` が自動検出（**変更禁止**）
- 追加: 「`POST /api/v1/agent/versions/1/edits` → 404」をユニットで固定。`tests/unit/test_api_path_separation_live.py` に 10 パス（#22 最小＋#23〜#26＋#29〜#33）が `/api/v1/ui/` 配下に**存在**することを 1 関数で

## 4. エラー変換（`app/api/errors.py` 1 箇所・CV-015）

| code | status | 根拠 |
|---|---|---|
| `E_REASON_REQUIRED` / `E_RECORDER_REQUIRED` / `E_QTY_UNIT_REQUIRED` / `E_STATE_VALUE_CONFLICT` / `E_TARGET_INVALID` / `E_REQUEST_INVALID` | 400 | 05 §6 |
| `E_FIELD_NOT_EDITABLE` | **422** | 05 §6・§0 ① |
| `E_ALREADY_UNDONE` / `E_ALREADY_CONFIRMED` | 409 | 05 §6 |
| `E_NOT_FOUND` | 404 | 既存 |

- `route_errors.invalid_request`: 構造違反（path/query・snake_case キー）→ 422 `E_REQUEST_INVALID`（現状維持）。それ以外は最初の `E_*` 型を **`DOMAIN_ERROR_STATUS_BY_CODE.get(code, 400)`** で返す（§0 ①）。`recordedAt` 同送 → `extra_forbidden` → 400 `E_REQUEST_INVALID`
- status リテラルは `errors.py` 以外に書かない（`test_single_source_of_truth.py` が検出）。`details` は camelCase（CV-011）

## 5. テスト

- **unit `tests/unit/test_record_api.py`**（`test_run_api.py` の型: `SimpleNamespace`＋`AsyncMock` の Service、`httpx.ASGITransport`、`dependency_overrides`）: 正常系（#29 201・`recordedAt` tz 付き ISO・Service へ `recorded_at` を渡していない・数量 2 行）/ #24 の `history[].undoneBy`・`odRaw`・`Decimal` の文字列化・`versionId`/`createdAt` 非出力 / #26 の `latest:null` と `judged`∧`unresolved` / 契約 parametrize（空 reason 400・`recordedBy` 欠落 400・両 None 400・単位なし 400・`field:"grade_raw"` **422**・`row_match` で `itemId` なし 400・`recordedAt` 同送 400・`recorded_by` 422）/ Service 例外 → status（404/409/409/400）/ `/api/v1/agent/versions/1/edits` → 404 / #22 最小・#1 拡張の導出（Service mock）
- **integration `tests/integration/test_api_records.py`（最小 1 本）**: `tests/fixtures/record_data.py` の `seed_record_version` を使い、`POST edits`(grade→L80) 201 → `GET items`（`grade=="L80"`・`gradeRaw=="K55"`・history 1）→ `POST undo` 200（`undoneBy`）→ `GET items`（元に戻り history 1 のまま）→ `GET /versions/{id}`（`editCount==0`）。`details` camelCase・`recordedAt` tz
- 変異 1 行（`errors.py` の `E_ALREADY_UNDONE` 行を消す → 409 テストが落ちる）
- 既存テストを消さない・弱めない（`test_api_path_separation.py` / `test_single_source_of_truth.py` / `route_contract.py`）

## 6. 統合ポイント

`make check`（OpenAPI → orval → typecheck を内包）。生成先 `frontend/src/shared/api/generated/` は git 管理外。`ls generated/model | wc -l` の前後差と追加ファイル名、消えた型があれば列挙して止まる。`frontend/src` は触らない（FE 166 件は現状維持で緑）。

## 7. 完了条件

- `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green・除外なし（基準 BE 518 / FE 166 ＋新規）
- `docs/t302-handoff.md`: 触ったファイル一覧（T-302 本体 / T-301 由来 / T-101-102 由来 / 共有 `route_errors`）→ レビュー対応表 → OpenAPI に出た 10 パス（`grep -c '"/api/v1/ui/versions/' backend/openapi.json` 等）と orval 追加 model 一覧 → `make check` 実出力 → 末尾 **「再レビュー依頼」**
- `app/agent/**` に diff がない。commit は Claude
