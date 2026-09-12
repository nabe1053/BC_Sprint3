# T-502 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-502【API】G5 承認・状態 API #22 拡張・#28・#34〜#37（＋#1 の送付可否）**（memory §3・依存 T-501 DONE）。T-403（FE）の未コミット差分があるときは **`frontend/` を触らない**（CV-023）。handoff 冒頭に触るファイル一覧を先に書く（CODEX-INSTRUCTIONS §5）。
設計の正: 05-api-ipo.md 0.2〜0.4・FLOW-05/06・3.7〜3.9・5 章 #1/#22（`carryOver` 4 値）/#28・6 章（AD-029 の書き戻し済み）／03-spec SCR-01（送付可否列）・SCR-03（差し戻し中）・SCR-06／04-db §3.4／`docs/t501-instructions.md` §4 と `docs/t501-handoff.md` の **「T-502 へ渡す契約」節**。**本書で「T-501 契約」と書いた箇所は着手時に t501-handoff の契約節で実型を確認し、差があれば handoff 冒頭に差分を書く。**

## 0. orchestrator 決定（AD-029・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| ① | #22 の置き方 | **既存 `GET /cases/{caseId}/versions` を拡張**（新 endpoint を作らない）。`VersionListItem` に `unresolvedCount` / `carryOver` / `latestStateEvent` / `latestBounce` / `latestSendoff` / `bounced` / `needsRecheck` を**必須**で追加。着手時に `grep -rn VersionListItem frontend/src --include=*.ts* \| grep -v generated` が 0 件であることを handoff に |
| ② | #22 の Service | endpoint `list_versions` の依存を **`ApprovalService.list_versions_with_records(case_id)`** に切替（`get_approval_service` 注入）。`RecordService.list_versions` / `RecordRepository.list_versions` は削除しない（整理は C-3） |
| ③ | `bounced` / `needsRecheck` の導出者 | **API 側（BE）が導出**（3 画面で同じ比較を複製しない・CV-015）。純粋関数 `bounced(latest_bounce_at, latest_review_checked_at)` / `needs_recheck(latest_event)` を **`app/services/version_state.py` に追記**（T-501 のモジュール。追記可）。`ApprovalService.list_versions_with_records` が付与、endpoint は写すだけ（CV-009） |
| ④ | `needsRecheck` の定義 | 最新状態イベントが `from_state='review_checked' ∧ to_state='staff_checked'`（AD-028 ⑩。許可された遷移列では「最新 review_checked イベントより後に staff_checked イベントがある」と同値。同値性の根拠を docstring に） |
| ⑤ | `bounced` の定義 | 最新 `bounces` 行があり、かつ最新 `to_state='review_checked'` イベントが無いか bounce より前（AD-028 ⑯）。**最新イベント 1 件では判定不能**なので、T-501 の `list_versions_with_records` は **最新 `review_checked` イベントの `recorded_at`（`latest_review_checked_at`）** を版ごとに返す（T-501 追補として §7 で Codex に伝達済み。無ければ T-502 で T-501 由来の変更として追加し handoff で分ける） |
| ⑥ | #28 の応答形 | `{edits, confirmations, judgements, stateEvents, bounces, unlinkedComments, sendoffDecisions}` の 7 配列。全て取消済み含む・`(recordedAt, id)` 昇順（Repository の順を信用し DTO で再ソートしない）。`bounces[].comments` に紐づけ済みコメントを内包 |
| ⑦ | 確認記録の DTO | 既存 `ConfirmationRecord`（#31 応答）は**変えず**、#28 用に `ConfirmationHistoryRecord`（＋`undoneAt` / `undoneBy`）を新設 |
| ⑧ | 置き場 | 新規 `app/api/ui/endpoints/approvals.py`（#28 GET・#34〜#37 POST）＋ `app/api/ui/schemas/approvals.py`。#22 拡張は既存 `endpoints/versions.py` / `schemas/versions.py`。DI は `dependencies.py` に `get_approval_service(session) -> ApprovalService(RecordRepository(session))`。`ui/router.py` に include（共有ファイルは handoff に明記） |
| ⑨ | `errors.py` 追加 | 7 コード: `E_STAFF_CHECK_INCOMPLETE` 409 / `E_COVERAGE_NOT_RECORDED` 409 / `E_STATE_ORDER` 409 / `E_STATE_ROLLBACK_FORBIDDEN` **422** / `E_NO_BOUNCE_COMMENT` 409 / `E_SENDOFF_REASON_REQUIRED` 400 / `E_COMMENT_REQUIRED` 400。status リテラルは `errors.py` 以外に書かない |
| ⑩ | `E_STATE_ROLLBACK_FORBIDDEN` の経路 | domain `Literal` 外 → `field_error_codes` → `invalid_request` が表を参照して 422（AD-022 ①）。`toState` 欠落も同コード。TODO-027 ② の式は C-3 で {E_FIELD_NOT_EDITABLE, E_STATE_ROLLBACK_FORBIDDEN} に更新（記録済み） |
| ⑪ | #37 `reason` の空文字 | DTO の `@field_validator("reason", mode="before")` で `""` → `None`。`hold/approved` なら T-501 の `model_validator` が `E_SENDOFF_REASON_REQUIRED`（400）。`undecided` は無し／空で可 |
| ⑫ | 成功応答 | #34 201 `StateEventRecord{stateEventId, fromState, toState, recordedBy, recordedAt, unresolvedCount}` / #35 201 `BounceCommentRecord{bounceCommentId, itemId, bounceId: null, comment, recordedBy, recordedAt}` / #36 201 `BounceRecord{bounceId, reason, recordedBy, recordedAt, comments: BounceCommentRecord[]}`（T-501 の `bounce()` がコメントを返さなければ `comments` を #36 応答から外し #28 のみ → 着手時確認）/ #37 201 `SendoffDecisionRecord{sendoffDecisionId, decision, reason, recordedBy, recordedAt}`。`record_response(schema, row, id_field)` で写す（`versionId` を出さない） |
| ⑬ | #1 の送付可否 | **T-502 に含める**（SCR-01 の送付可否列は G5 で表示。03-spec SCR-01「G5 まで『—』」）: `CaseListItem.latestSendoff: Literal[...] \| null`（最新版の最新 `sendoff_decisions.decision`）。`latest_versions` と同じ 1 クエリ（`LEFT JOIN LATERAL` or 相関サブクエリ）で付与し N+1 を作らない。`progressStatus`・`latestVersionId` は不変 |
| ⑭ | 生成所要（05 #22） | **含めない**。`agent_runs` と版の結線は G6 T-603 で（TODO-037）。05 #22 に注記済み |
| ⑮ | `route_contract.py` | 4 セグメント登録済み → `test_api_path_separation.py` が自動検出（**変更禁止**）。`records` は追加しない（読取）。`(method, path)` 存在 5 組と `POST /api/v1/agent/versions/1/state-events` 404 は `test_api_path_separation_live.py`・unit で固定 |
| ⑯ | #23 `summary` | 拡張しない（AD-028 ⑱）。SCR-06 要約カードの値は #22/#23/#28 から FE が組む（対応表を「T-503 へ渡す契約」に） |
| ⑰ | 405 の本文（TODO-032） | 対象外・`main.py` 不変 |
| ⑱ | `details` の素通し | `E_STAFF_CHECK_INCOMPLETE` の `details`（`unmatchedItemIds` / `unmatchedRowCodes` / `coverageRecorded`）は T-501 の `DraftError.details` をそのまま返す（CV-011。camelCase であることを integration で確認） |

## 1. 範囲と範囲外

**範囲（API 層のみ）**: DTO `app/api/ui/schemas/approvals.py`（新規）／`schemas/versions.py` の `VersionListItem` 拡張＋`CarryOverResponse`／`schemas/cases.py` の `CaseListItem.latestSendoff`／endpoint `app/api/ui/endpoints/approvals.py`（新規。`route_class=DraftRoute, responses=ERROR_RESPONSES`, `Id = Annotated[int, Path(gt=0)]`）／`endpoints/versions.py` の `list_versions` 切替／#1 の repository 1 クエリ拡張（cases 側。読取のみ）／共有 `dependencies.py`・`ui/router.py`・`errors.py`（7 行）・`test_api_path_separation_live.py`／§0 ③ の純粋関数追加／統合ポイント `make check`（OpenAPI → orval → typecheck。model 数の前後差分・消失 0）／テスト `tests/unit/test_approval_api.py`（Service mock）・`tests/integration/test_api_approvals.py`（実 HTTP・実 DI）。
**範囲外**: `frontend/`（T-503）、T-501 の Service/Repository/domain/migration の仕様変更（⑤の追補を除く）、#23 拡張、生成所要（⑭）、#38〜#40、`app/agent/**`（ツール 13 本・`AGENT_TOOL_NAMES` 不変）、`route_contract.py`・`test_api_path_separation.py`・`main.py`（変更禁止）、`docs/requirements/*`（orchestrator が書き戻し済み）。

## 2. DTO（`CamelModel`・CV-010/011/012。既存クラス名と衝突させない）

要求は **domain Input を第一基底・`StrictRequest` を第二基底**（`ItemEditRequest` と同型）。応答は `CamelModel`。語彙は domain の `Literal` を import（AD-026 ⑤）。`recordedAt` は応答のみ。

| クラス | フィールド |
|---|---|
| `StateEventRequest(StateEventInput, StrictRequest)` | `to_state: Literal["staff_checked","review_checked"], recorded_by` |
| `BounceCommentRequest(BounceCommentInput, StrictRequest)` | `item_id: int(gt=0), comment, recorded_by` |
| `BounceRequest(BounceInput, StrictRequest)` | `recorded_by` のみ（AD-028 ⑥） |
| `SendoffDecisionRequest(SendoffInput, StrictRequest)` | `decision, reason: str \| None, recorded_by`。`""` → `None`（⑪） |
| `StateEventRecord` | `state_event_id, from_state: VersionState, to_state, recorded_by, recorded_at, unresolved_count: int(ge=0)` |
| `BounceCommentRecord` | `bounce_comment_id, item_id, bounce_id: int \| None, comment, recorded_by, recorded_at` |
| `BounceRecord` | `bounce_id, reason, recorded_by, recorded_at, comments: list[BounceCommentRecord]` |
| `SendoffDecisionRecord` | `sendoff_decision_id, decision, reason: str \| None, recorded_by, recorded_at` |
| `ConfirmationHistoryRecord` | `confirmation_id, kind, item_id: int \| None, recorded_by, recorded_at, undone_at: datetime \| None, undone_by: str \| None` |
| `RecordsResponse`（#28） | `edits: list[ItemEditRecord], confirmations: list[ConfirmationHistoryRecord], judgements: list[JudgementRecord], state_events, bounces, unlinked_comments, sendoff_decisions` |
| `CarryOverResponse`（#22） | `edit_count, row_match_confirmed, row_match_total: int(ge=0), coverage_recorded: bool, judgement_count: int(ge=0)`（`CarryOver` dataclass から `from_attributes`） |
| `VersionListItem`（拡張） | 既存 ＋ `unresolved_count: int(ge=0), carry_over: CarryOverResponse, latest_state_event: StateEventRecord \| None, latest_bounce: BounceRecord \| None（`comments=[]` 固定・docstring に理由）, latest_sendoff: SendoffDecisionRecord \| None, bounced: bool, needs_recheck: bool` |
| `CaseListItem`（拡張・#1） | ＋ `latest_sendoff: Literal["undecided","hold","approved"] \| None` |

- `ItemEditRecord` / `JudgementRecord` / `VersionState` は既存を import（CV-015）。記録行の `versionId` / `createdAt` を出さない。人由来の文字列（`comment` / `reason`）はそのまま返す（エスケープは FE）

## 3. エラー変換（`app/api/errors.py` 1 箇所）

| code | status | 発生経路 | `details` |
|---|---|---|---|
| `E_RECORDER_REQUIRED` | 400（既存） | `field_error_codes` | 既存形 |
| `E_COMMENT_REQUIRED` | 400 | #35 `comment` 空 → `field_error_codes` | 既存形 |
| `E_SENDOFF_REASON_REQUIRED` | 400 | #37 `model_validator`（T-501） | 既存形 |
| `E_STATE_ROLLBACK_FORBIDDEN` | 422 | #34 `toState='draft'`／欠落／語彙外 | 既存形 |
| `E_STATE_ORDER` | 409 | Service（同一状態・draft→review・#34 での review→staff・review 版への #36） | T-501 契約（無ければ `{}`） |
| `E_STAFF_CHECK_INCOMPLETE` | 409 | Service（#34 未照合／#36 draft 版） | `unmatchedItemIds` / `unmatchedRowCodes` / `coverageRecorded`（素通し） |
| `E_COVERAGE_NOT_RECORDED` | 409 | Service | T-501 契約 |
| `E_NO_BOUNCE_COMMENT` | 409 | Service（#36） | T-501 契約 |
| `E_NOT_FOUND` | 404（既存） | 未確定版・存在しない版・版外 `itemId` | 既存 |
| `E_REQUEST_INVALID` | 422/400（既存） | `versionId<=0`・snake_case キー・`recordedAt` 同送（`extra_forbidden`） | 既存 |

検査順は Service（AD-028 ②）。API は順序を作らない。

## 4. endpoint 一覧とパス分離

| # | method | path（`/api/v1/ui` 配下） | 関数名（orval 名固定） | status |
|---|---|---|---|---|
| 1 | GET | `/cases` | 既存名維持 | 200 |
| 22 | GET | `/cases/{caseId}/versions` | `list_versions`（既存名維持） | 200 |
| 28 | GET | `/versions/{versionId}/records` | `list_records` | 200 |
| 34 | POST | `/versions/{versionId}/state-events` | `record_state_event` | 201 |
| 35 | POST | `/versions/{versionId}/bounce-comments` | `record_bounce_comment` | 201 |
| 36 | POST | `/versions/{versionId}/bounces` | `record_bounce` | 201 |
| 37 | POST | `/versions/{versionId}/sendoff-decisions` | `record_sendoff_decision` | 201 |

`/agent/*` に一切追加しない（`app/agent/**` diff 0）。

## 5. 実装順序と RED→GREEN（層順・Service は mock）

| 順 | 成果物 | RED（先に書く） | 置き場 |
|---|---|---|---|
| 1 | `errors.py` 7 行 | `DOMAIN_ERROR_STATUS_BY_CODE[code] == status` を 7 件 parametrize | `tests/unit/test_approval_api.py` |
| 2 | 要求 DTO 4 種 | `toState:"draft"` → 422 `E_STATE_ROLLBACK_FORBIDDEN` / `toState` 欠落 → 422 同 / `recordedBy` 空 → 400 / `comment:""` → 400 `E_COMMENT_REQUIRED` / `hold`＋`reason:""` → 400 `E_SENDOFF_REASON_REQUIRED` / `undecided` reason 無し → 201 / snake キー → 422 / `recordedAt` 同送 → 400。全て Service 未呼出 | 同上 |
| 3 | `approvals.py` #34〜#37 | 201 と応答キー完全一致（tz 付き `recordedAt`）/ Service に `recorded_at` を渡さない / #36 は `recorded_by` だけ渡る / `DraftError` → status 7 件（`E_STAFF_CHECK_INCOMPLETE` は details 3 キー素通し）/ `versionId`・private 属性非露出 | 同上 |
| 4 | #28 `list_records` | 7 キーちょうど / 各要素キー完全一致 / `confirmations[].undoneBy` / `bounces[0].comments[0].bounceId == bounces[0].bounceId` / `unlinkedComments[].bounceId is None` / 応答 JSON 再帰走査で `_` を含むキー 0 / 空版は 7 配列 `[]` | 同上 |
| 5 | 純粋関数 `bounced` / `needs_recheck` | 真理値表: bounce 無し→F / bounce あり・review 無し→T / bounce < review→F / review < bounce→T / 最新 review→staff → needsRecheck T、staff→review → F、None → F | `tests/unit/test_version_state.py`（追記） |
| 6 | #22 拡張＋`get_approval_service`＋router | `versions[0]` のキー完全一致 / `carryOver` 5 キー / `latest*` null・非 null 両方 / `bounced`・`needsRecheck` が Service 戻り値どおり / `list_versions_with_records.assert_awaited_once_with(case_id)` / `record_service.list_versions.assert_not_awaited()` | `test_approval_api.py` |
| 7 | #1 `latestSendoff` | unit: Service mock で null / `approved` / integration: 送付可否 2 件記録 → 最新が返る・版なし案件は null・クエリ数が案件数に依存しない | `tests/unit/test_case_api.py`（追記）・integration |
| 8 | パス分離追補 | `_live.py` に 5 組追加 / agent 側 POST → 404 ∧ Service 未呼出 | `test_api_path_separation_live.py`・`test_approval_api.py` |
| 9 | integration 1 本（実 DI・`get_db` のみ override・CV-028） | seed → row_match＋coverage → `POST state-events staff_checked` 201（`unresolvedCount`）→ `POST bounce-comments` 201 → `POST bounces` 201（`reason == "{rowCode}: {comment}"`）→ `GET /versions/{id}` `currentState=="staff_checked"` 不変 → `GET records`（件数・順序・`bounceId`）→ `GET /cases/{caseId}/versions`（`bounced true`・`carryOver.rowMatchConfirmed==1`・`coverageRecorded true`）→ `POST state-events review_checked` → `bounced false` → `POST edits` → `needsRecheck true`・`currentState=="staff_checked"` → `POST sendoff-decisions approved` → `latestSendoff.decision=="approved"` → `GET /cases` `latestSendoff=="approved"`。異常: 同一状態再遷移 409 `E_STATE_ORDER` / 未照合版 409 と `details.unmatchedItemIds` 実 ID / 別版 `itemId` の bounce-comment 404 / 未確定版 404 | `tests/integration/test_api_approvals.py` |

- 変異 1 行: `errors.py` の `E_STATE_ORDER` 行を消す → 409 テストが落ちる／`needs_recheck` の `from_state` 条件を外す → 順 5 が落ちる
- 既存テストを消さない・弱めない。`test_record_api.py` の `list_versions` 系が `get_record_service` mock のままなら、`record_http` fixture に `get_approval_service` override を足す（既存テスト変更として理由を handoff に）

## 6. 統合ポイント・完了条件

- `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（基準: BE は T-501 完了時の実測＋新規／FE は T-403 の状態で変動 → 実測を handoff に）。T-403 の未コミット FE で赤なら `frontend/` を直さず原因を handoff に（CV-023 ②）。pytest は Claude・T-403 と同時に走らせない（LN-027）
- OpenAPI: `records` GET・`state-events` / `bounce-comments` / `bounces` / `sendoff-decisions` POST が tag `ui` で各 1 件、`/api/v1/agent/` 配下に同セグメント 0 件（`grep -c` を handoff に）。`/cases/{caseId}/versions`・`/cases` の `operationId` 不変
- orval model **146 → 追加・消失 0** を `ls generated/model | sort` の前後差分で（`versionListItem.ts` / `caseListItem.ts` は内容変化のみ）
- `docs/t502-handoff.md`: 触ったファイル（本体／共有／T-501 由来の変更があれば分ける）→ T-501 契約との差分 → §0 ①〜⑱ の反映箇所（file:line）→ レビュー対応表（項目／file:line／RED テスト名・コマンド・件数／変異 1 行）→ 既存テスト変更の理由 → OpenAPI パス・orval 前後件数と追加名 → `make check` 実出力 → **「T-503 へ渡す契約」節**（#22 のキー・#28 の 7 配列・`bounced`/`needsRecheck` の定義・7 コードと HTTP・SCR-06 要約カード各値の取得元 #22/#23/#28 の対応表・網羅性確認者名は #28 `confirmations` の `kind='coverage' ∧ undoneAt null` から）→ 末尾見出し **`## 再レビュー依頼（T-502）`**（本文中でこの語を使わない・LN-033）。commit は Claude
- `app/agent/**`・`route_contract.py`・`main.py`・`frontend/src` に diff なし
