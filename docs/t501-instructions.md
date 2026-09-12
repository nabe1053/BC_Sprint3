# T-501 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-501【BE】G5 状態遷移・差し戻し・送付可否の記録**（memory §3・依存 T-301 DONE）。T-403（FE）が並行のときは **`frontend/` を触らない**（CV-023）。handoff 冒頭に触るファイル一覧を先に書く（CODEX-INSTRUCTIONS §5）。
設計の正: 04-db.md §3.4（`version_state_events` / `bounces` / `bounce_comments` / `sendoff_decisions`）・§3.6・`versions.current_state`・confirmations 直後の遷移条件注記／05-api-ipo.md FLOW-05/06・3.6 注記・3.7〜3.9・5 章 #22 `carryOver`・#28／02-requirement.md FUNC-08・FUNC-10・7 章／03-spec.md SCR-03「担当者確認済みにする」・SCR-06／06-scenario-test.md TEST-12〜14・16。**AD-028 の書き戻しは 04-db / 05 / 03-spec に反映済み**（下記 §0 の「書き戻し」列）。

## 0. orchestrator 決定（AD-028・確定）

| # | 事項 | 決定 | 書き戻し |
|---|---|---|---|
| ① | `draft → staff_checked` の条件 | **設計どおり両方必須**: 未取消 `row_match` が全 `items` を覆う **かつ** 未取消 `coverage` ≥1。未解決件数は判定に使わず記録するだけ | 不要（4 文書一致） |
| ② | #34 の検査順 | recorder 空 → `toState='draft'`（`E_STATE_ROLLBACK_FORBIDDEN`）→ `E_STATE_ORDER` → `E_STAFF_CHECK_INCOMPLETE`（`details.unmatchedItemIds` 昇順 / `unmatchedRowCodes` 同順 / `coverageRecorded: bool`）→ `E_COVERAGE_NOT_RECORDED`。SCR-03 が両方を同時表示するため未照合エラーの details に `coverageRecorded` を同乗 | 05 3.7 に注記 |
| ③ | `E_STATE_ORDER` の範囲 | `draft → review_checked` に加え **同一状態への再遷移**と **#34 経由の `review_checked → staff_checked`** も `E_STATE_ORDER`（戻す経路は訂正に付随するイベントのみ） | 05 3.7 表に 1 行 |
| ④ | HTTP | 05 どおり `E_STATE_ORDER` 409 / `E_STATE_ROLLBACK_FORBIDDEN` 422（domain Literal 外 → `field_error_codes`）。**`errors.py` への追加は T-502**（T-501 は domain の例外コードだけ） | 不要 |
| ⑤ | `review_checked` からの差し戻し | **`E_STATE_ORDER`（409）**。評価確認済みを取り消す経路が無く「差し戻し中」が意味を持たないため。差し戻せるのは `staff_checked` のみ | 05 3.8 表に 1 行 |
| ⑥ | 差し戻し理由（#36） | リクエストは **`recordedBy` のみ**。Service が版の未紐づけ行コメント（`bounce_id IS NULL`）を `(recorded_at, id)` 昇順に `"{row_code}: {comment}"` を改行 `\n` で連結して `bounces.reason` にする。0 件 → `E_NO_BOUNCE_COMMENT` | 05 3.8 にリクエスト表 |
| ⑦ | `bounce_comments.bounce_id` の付与 | **NULL → 値の 1 回限りの UPDATE を明示的例外として許容**（`undone_at` と同型）。差し戻し INSERT と同一トランザクション。値が入った行は二度と変えない（テストで固定） | 04-db §3.4 に注記 |
| ⑧ | #35・#37 の前提状態 | **確定済み版なら任意の状態で記録可**（未確定は `E_NOT_FOUND`・T-301 と統一）。送付可否は評価確認と独立。最新判断 = `(recorded_at, id)` 降順先頭 | 不要 |
| ⑨ | `review_checked` 版への訂正（TODO-019） | `RecordService.edit` で、ロック下の `version.current_state == 'review_checked'` のとき `review_checked → staff_checked` イベントを**同一トランザクション**で INSERT し `current_state` を更新。`recorded_by` = 訂正者、`recorded_at` = 訂正と同時刻、`unresolved_count` = その時点の値。**`undo_edit` / `confirm` / `judge` では積まない**（設計は「訂正」のみ。undo の扱いは TODO-034） | 不要 |
| ⑩ | 03-spec「評価確認の日時を消す」 | **消さない**（追記型）。「最新 `review_checked` イベントより後に `staff_checked` イベントがある」ことから UI が「再確認が必要」を導出。T-501 は生データを返すだけ | 03-spec SCR-06 注記を改訂 |
| ⑪ | `from_state` の CHECK | `CHECK(from_state IN ('draft','staff_checked','review_checked'))` と `CHECK(from_state <> to_state)` を**追加**（ORM・migration 同名） | 04-db §3.4 表 |
| ⑫ | `versions.current_state` の書込経路 | **`RecordRepository.save_state_event()`（新設）のみ**。既存の `DraftRepository.complete()`（確定時の初期値 `'draft'`）と合わせて 2 箇所。それ以外に `current_state =` の代入が無いことを SSOT テストで機械検査 | 不要 |
| ⑬ | #22 `carryOver` | `editCount` = 未取消 `item_edits` **行数**（#23 `editCount` と同義）/ `rowMatchConfirmed`・`rowMatchTotal` = 未取消 `row_match` 行数・`items` 数 / `coverageRecorded` = 未取消 coverage ≥1 / `judgementCount` = 判断が 1 件以上ある `questions` 数。状態イベント・差し戻し・送付可否は含めない。**`run_repository._has_records` は触らない**（述語の一本化は C-3・LN-056） | 不要 |
| ⑭ | 置き場 | **`app/services/approval_service.py`（`ApprovalService`）新設**。Repository は版行ロックの所有者を 1 つに保つため **`RecordRepository` を拡張**（書込は同一クラス）。`record()` を `yield version` に変える（既存呼び出しは不変） | 不要 |
| ⑮ | 遷移時の `unresolved_count` | `record_service.summary()` の `unresolved_question_ids` と**同じ定義**。純粋関数 `unresolved_count()` を `app/services/version_state.py` に置き、`summary` もそれを使う（二重定義を作らない） | 不要 |
| ⑯ | 「差し戻し中」の終了条件 | **最新 `bounces` 行より後に `to_state='review_checked'` の状態イベントが無い間**は差し戻し中。導出は T-502（`bounced: bool`）。T-501 は材料（最新 bounce・状態イベント列）を返す | 03-spec SCR-03 注記に 1 文 |
| ⑰ | 行コメント空のコード | 新コード **`E_COMMENT_REQUIRED`**（400 相当。domain `field_error_codes`。`errors.py` 追加は T-502） | 05 #35 表に 1 行 |
| ⑱ | `summary`（#23）の拡張 | **T-501 ではしない**（既存キー不変。SCR-06 要約カードに必要なら T-502 で `list_records` から組む） | 不要 |

## 1. 範囲と範囲外

**範囲（BE のみ・endpoint 無し）**: domain 入力型（`StateEventInput` / `BounceCommentInput` / `BounceInput` / `SendoffInput`）＋ `CarryOver` / `Transition` dataclass（`app/domain/record_types.py`）／純粋関数 `decide_transition` / `unresolved_count` / `bounce_reason`（`app/services/version_state.py`。SQLAlchemy・datetime・HTTP を import しない）／ORM `app/models/approvals.py`＋`models/__init__.py`＋migration `alembic/versions/approval_records.py`（**4 テーブルとも未作成**）／`RecordRepository` 拡張／`ApprovalService`／`RecordService.edit` への ⑨ 組み込み／fixtures `tests/fixtures/record_data.py` の拡張／SSOT テスト追記。
**範囲外**: API endpoint / DTO / `app/api/errors.py` / OpenAPI・orval（T-502）、SCR-06（T-503）、.xlsx（G6）、`frontend/`、`app/agent/**` 一切（ツール 13 本・`AGENT_TOOL_NAMES` 不変）、`run_repository._has_records`、`route_contract.py`・`test_api_path_separation.py`、`docs/requirements/*`（orchestrator が反映済み）。**`backend/openapi.json` は不変**（`make check` 後に model 数 146 のままを handoff に）。

## 2. 前提となる決定（引用）

- 記録者名は画面入力値・NOT NULL・`CHECK(trim<>'')`・**AI/Service が補完しない**（CLAUDE.md 決定事項1・04-db 原則5）。`recorded_at` はサーバ採時のみ（CV-009）
- 追記型（04-db 原則1・§3.4 共通ルール）。UPDATE の例外は ①`versions.current_state` キャッシュ（イベント挿入と同一トランザクション）②`undone_at/undone_by` ③`bounce_comments.bounce_id`（⑦）の 3 つだけ
- 版スコープ: `bounce_comments` は複合 FK `(version_id, item_id) → items(version_id, id)`（04-db 原則2）。版外 item → `E_NOT_FOUND`（23503 の翻訳は `record()` 既存経路）
- 差し戻しは `version_state_events` に行を作らない・`current_state` 不変（04-db / 02 FUNC-10 / X13）。送付可否は別テーブル、保留・承認は理由必須（DB CHECK＋`model_validator` の二重）
- 未確定版（`finalized_at IS NULL`）への記録は `E_NOT_FOUND`（`RecordRepository.version` を再利用）。`CHECK(finalized_at IS NOT NULL OR current_state='draft')` が既にある
- 集約資産は import（CV-015）: `DraftRepository._transaction()`・`require()`・`RecordRepository.record()` の版行 `FOR UPDATE`。並行制御の証明は **実 PostgreSQL 2 セッション＋`pg_blocking_pids`＋解放後の値**（CV-024。型: `tests/integration/test_record_repository.py` の row_match 2 セッション）
- CHECK・部分 UNIQUE・複合 FK は ORM `__table_args__` と migration の両方に**同名で**（04-db 0.5。手本 `models/records.py` / `alembic/versions/human_records.py`）
- 新リビジョン `down_revision="human_records"`（着手時 `alembic heads` 単一を再確認）。適用済みリビジョンを編集しない（LN-018）。`make migrate` で両 DB（LN-013/017）
- ファイル名にチケット ID を入れない（CV-017）。テスト間 import 禁止（CV-021）。件数は集合一致で assert（LN-059）
- `UI_ONLY_SEGMENTS` に `state-events` `bounces` `bounce-comments` `sendoff-decisions` は登録済み（`tests/fixtures/route_contract.py`）。触らない
- Codex は BE のみなので作業中は `make check-be`。**T-403 と pytest を同時に走らせない**（LN-027。T-403 は `check-fe` のみ）

## 3. 遷移規則（純粋関数 `decide_transition` の仕様）

入力: `current_state`, `to_state`, `item_ids`（集合）, `matched_item_ids`（未取消 row_match）, `coverage_confirmed: bool`, `rows: dict[item_id, row_code]`。出力: `Transition(from_state, to_state)` または `DraftError`。

| from → to | 判定 |
|---|---|
| `draft → staff_checked` | 未照合 = `item_ids − matched_item_ids`。空でなければ `E_STAFF_CHECK_INCOMPLETE`（details: `unmatchedItemIds` 昇順・`unmatchedRowCodes` 同順・`coverageRecorded`）。次に `coverage_confirmed=False` → `E_COVERAGE_NOT_RECORDED`。未解決件数は判定に使わない |
| `staff_checked → review_checked` | 無条件で可。`unresolved_count` を積む |
| `draft → review_checked` | `E_STATE_ORDER` |
| `X → X`（同一） | `E_STATE_ORDER`（③） |
| `review_checked → staff_checked` | #34 からは `E_STATE_ORDER`。訂正に付随してのみ成立（⑨・`RecordService.edit`） |
| `* → draft` | domain Literal 外 → `E_STATE_ROLLBACK_FORBIDDEN`（純粋関数には到達しない） |

補足: 確定版は `E_NO_ITEMS` により N≥1 だが、純粋関数は空集合でも例外を出さず「未照合 0・coverage 判定」に落ちること（LN-059）。

## 4. 保存仕様

**共通**: 毎回 INSERT・`recorded_at = datetime.now(UTC)` を Service で確定・`repo.record(version_id)` の版行ロック下で判定→INSERT→（状態遷移のみ）`versions.current_state` UPDATE を**同一トランザクション**で行う。`from_state` はロック取得後の `version.current_state`（`populate_existing=True` 再読込済み）。

- **version_state_events（#34）**: `StateEventInput(to_state: Literal["staff_checked","review_checked"], recorded_by: Recorder)`。`field_error_codes = {"recorded_by": "E_RECORDER_REQUIRED", "to_state": "E_STATE_ROLLBACK_FORBIDDEN"}`。Repository `save_state_event(version, *, from_state, to_state, recorded_by, recorded_at, unresolved_count)` が行を add し `version.current_state = to_state` を同メソッド内で代入（唯一の経路・⑫）
- **bounce_comments（#35）**: `BounceCommentInput(item_id: int(gt=0), comment: Recorder, recorded_by: Recorder)`、`field_error_codes` に `"comment": "E_COMMENT_REQUIRED"`。`bounce_id=NULL` で INSERT。`undone_at` を**持たない**（04-db）
- **bounces（#36）**: `BounceInput(recorded_by)`。`draft` → `E_STAFF_CHECK_INCOMPLETE`／`review_checked` → `E_STATE_ORDER`（⑤）。未紐づけコメント 0 → `E_NO_BOUNCE_COMMENT`。`reason = bounce_reason(comments, rows)`（⑥）。INSERT 後、同トランザクションで対象コメントの `bounce_id` を付与（⑦）。**`version_state_events` に行を作らない・`current_state` 不変**をテストで固定
- **sendoff_decisions（#37）**: `SendoffInput(decision: Literal["undecided","hold","approved"], reason: Recorder | None, recorded_by)`。`hold/approved ∧ reason 空` → `E_SENDOFF_REASON_REQUIRED`（`model_validator`）。状態前提なし（⑧）
- **`RecordService.edit`（⑨）**: `async with repo.record(version_id) as version:`。`save_edits` の後・同トランザクション内で `version.current_state == "review_checked"` なら `save_state_event(version, from_state="review_checked", to_state="staff_checked", recorded_by=data.recorded_by, recorded_at=訂正と同じ at, unresolved_count=…)`。`staff_checked` / `draft` では積まない
- **#28 一覧材料**: `RecordRepository.list_records(version_id)` → `{"edits": 全行(取消含む), "confirmations": 全行, "judgements": 全行, "state_events": [...], "bounces": [{"bounce": b, "comments": [...]}], "unlinked_comments": [...], "sendoff_decisions": [...]}`（各 `(recorded_at, id)` 昇順）。DTO 化は T-502
- **#22 材料**: `RecordRepository.list_versions_with_records(case_id)` → 版ごとに `CarryOver(edit_count, row_match_confirmed, row_match_total, coverage_recorded, judgement_count)`（frozen dataclass）＋ `unresolved_count` ＋ 最新状態イベント ＋ 最新 bounce ＋ 最新送付可否。**版数 N に対しクエリ数を固定**（版ごとにループで SELECT しない）

**AGENT-01 が呼べないこと**: `AGENT_TOOL_NAMES` 不変・`AgentToolGateway` に D 層書込を足さない・`/agent/*` 不変（`test_api_path_separation.py` を消さない・弱めない）。

## 5. 実装順序と RED→GREEN（層順・下位は mock）

| 順 | 成果物 | RED（先に書く） | 置き場 |
|---|---|---|---|
| 1 | domain 4 入力型＋`CarryOver`・`Transition` | 空白のみ recorder / `to_state='draft'` → `E_STATE_ROLLBACK_FORBIDDEN` / `hold` で reason 空 → `E_SENDOFF_REASON_REQUIRED` / `undecided` は reason 無しで可 / comment 空 → `E_COMMENT_REQUIRED` | `tests/unit/test_record_inputs.py`（追記） |
| 2 | `app/services/version_state.py` | §3 の表を 1 行 1 テスト（details 集合一致・昇順）/ 空集合で例外なし / 同一状態 → `E_STATE_ORDER` / `unresolved_count` が `summary` と同値（判断なし・judged∧unresolved・resolved）/ `bounce_reason` の順序・書式・0 件 | `tests/unit/test_version_state.py` |
| 3 | ORM `models/approvals.py`＋migration | **実 DB**: `to_state='draft'` 23514 / `from_state=to_state` 23514 / 空 recorded_by 23514 / `hold` で reason NULL 23514 / `undecided` で reason NULL は通る / 別版 item への bounce_comment 23503 / `bounces.reason` 空 23514 / 未確定版へ `current_state='staff_checked'` UPDATE 23514（既存 CHECK） | `tests/integration/test_approval_schema.py` |
| 4 | `RecordRepository` 拡張（`record()` → `yield version`、`save_state_event` / `save_bounce_comment` / `unlinked_bounce_comments` / `save_bounce` / `save_sendoff` / `list_records` / `list_versions_with_records` / `matched_item_ids` / `coverage_confirmed`） | 実 DB: イベント INSERT と `current_state` が同一 commit（途中例外 → 両方 rollback）/ **2 セッション**: A がロック下で `staff_checked` へ遷移中に B が同遷移 → `pg_blocking_pids` で block 観測 → A commit 後 B は `E_STATE_ORDER`（CV-024）/ 差し戻し後 `current_state` 不変・イベント件数不変 / `bounce_id` が未紐づけのみに付き既紐づけは不変 / `list_records` 各集合一致 / carryOver 4 値（undone 行を除外）/ 版 N でクエリ数固定 | `tests/integration/test_approval_repository.py`・`test_approval_queries.py` |
| 5 | `app/services/approval_service.py`（`transition` / `comment` / `bounce` / `decide_sendoff` / `list_records` / `list_versions_with_records`） | Repository mock（`tests/unit/test_record_service.py` の fixture と同型）: 検査順（②）/ `unresolved_count` がイベントに入る / `recorded_at` サーバ採時 / `review_checked` からの bounce → `E_STATE_ORDER` / sendoff は状態非依存 | `tests/unit/test_approval_service.py` |
| 6 | `RecordService.edit` の ⑨＋`summary` の `unresolved_count` を純粋関数へ寄せる | mock: `review_checked` 版の edit で `save_state_event` 1 回・`recorded_by`=訂正者・同時刻 / `staff_checked` 版 0 回 / undo 0 回。integration: edit 後 `current_state='staff_checked'` かつイベント 1 行増 | `tests/unit/test_record_service.py`・`tests/integration/test_record_repository.py`（追記） |
| 7 | SSOT: `app/**` で `current_state =` の代入が `draft_repository.complete` と `save_state_event` の 2 箇所のみ（⑫） | ソース機械検査（既存と同型） | `tests/unit/test_single_source_of_truth.py`（追記） |
| 8 | fixtures: `seed_record_version(state="draft")`（`state≠draft` のときは対応イベント行も入れて整合）/ 各記録のビルダ | — | `tests/fixtures/record_data.py` |

## 6. migration（新規・必須）

- `revision="approval_records"`, `down_revision="human_records"`。4 テーブルとも `id bigserial PK` / `created_at timestamptz NOT NULL DEFAULT now()`（`updated_at` 無し）/ `recorded_by text NOT NULL` / `recorded_at timestamptz NOT NULL`。`RecordedBase`（`models/records.py`）を継承
- 制約（ORM `__table_args__` にも同名で）:
  - `version_state_events`: FK `versions`、`CHECK(to_state IN ('staff_checked','review_checked'))`、`CHECK(from_state IN ('draft','staff_checked','review_checked'))`、`CHECK(from_state <> to_state)`、`CHECK(trim(recorded_by)<>'')`、`unresolved_count integer NOT NULL`、索引 `(version_id)`
  - `bounces`: FK `versions`、`CHECK(trim(reason)<>'')`、`CHECK(trim(recorded_by)<>'')`、索引 `(version_id)`
  - `bounce_comments`: FK `versions` / `bounces`（NULL 可）/ `items`、複合 FK `(version_id, item_id) → items(version_id, id)`、`CHECK(trim(comment)<>'')`、`CHECK(trim(recorded_by)<>'')`、索引 `(version_id)`・`(item_id)`・`(bounce_id)`
  - `sendoff_decisions`: FK `versions`、`CHECK(decision IN ('undecided','hold','approved'))`、`CHECK(decision='undecided' OR (reason IS NOT NULL AND trim(reason)<>''))`、`CHECK(trim(recorded_by)<>'')`、索引 `(version_id)`
- `downgrade` は 4 テーブル drop（`human_records.py` と同型）。完了確認は**両 DB の `\d`**（LN-018/026）。psql 出力を handoff に貼る

## 7. 完了条件

- `DEBUG=false CI=true make check` all green（基準: BE 625 passed / FE は T-403 の進捗で変動 → 実測を handoff に。CV-016）。**T-403 の jest と時間帯を分ける**（LN-027・CV-023）
- 両 DB に migration 適用済み・`\d` 実出力・`alembic heads` 単一
- `backend/openapi.json` 不変（endpoint 追加なし・model 146）
- `docs/t501-handoff.md`: 冒頭に触ったファイル一覧 → §0 ①〜⑱ の反映箇所（file:line）→ 「レビュー対応」表（項目 / 変更 file:line / RED を確認したテスト名・コマンド・件数 / 変異 1 行）→ 既存テスト変更の理由（`record()` の `yield version` 化・`summary` の寄せ）→ `make check` 実出力 → **「T-502 へ渡す契約」節**（下記）→ 末尾に見出し **`## 再レビュー依頼（T-501）`**（本文中でこの語を使わない・LN-033）
- ツール登録・`/agent/*` に変更が無い。commit は Claude

### 「T-502 へ渡す契約」節に書くこと
- `ApprovalService` 各メソッドの戻り値（ORM 行）と `list_records` / `list_versions_with_records` の dict/dataclass の**キー一覧**
- 新コード 7 種と推奨 HTTP（`E_STAFF_CHECK_INCOMPLETE` 409 / `E_COVERAGE_NOT_RECORDED` 409 / `E_STATE_ORDER` 409 / `E_STATE_ROLLBACK_FORBIDDEN` 422 / `E_NO_BOUNCE_COMMENT` 409 / `E_SENDOFF_REASON_REQUIRED` 400 / `E_COMMENT_REQUIRED` 400）→ T-502 が `errors.py` に追記
- `details` のキー（camelCase・CV-011）: `unmatchedItemIds` / `unmatchedRowCodes` / `coverageRecorded`
- 「再確認が必要」「差し戻し中」は最新イベントの比較で T-502 が導出（⑩⑯）
- #36 のリクエストは `recordedBy` のみ（⑥）
