# T-301 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-301【BE】G3 明細の現在値算出・人の記録**（memory §3）。依存 T-201（DONE）。
設計の正: `docs/requirements/04-db.md` §3.4（D層）・§3.6 / `05-api-ipo.md` FLOW-03・3.6・5章 #29〜#33 / `02-requirement.md` FUNC-08・7章。
本書の「orchestrator 決定」は確定済み（memory AD-017 / AD-018）。蒸し返さず、設計書に無い判断が新たに必要なら handoff に「要判断」と書いて止まる。

## 0. orchestrator 決定（確定）

| # | 事項 | 決定 |
|---|---|---|
| ① | 読取側（#23 件数・#24 明細＋現在値＋履歴・#25 根拠・#26 確認事項＋最新判断）の Repository/Service | **T-301 に含める**。T-302 は DTO＋endpoint のみ |
| ② | `item_edits.field` の語彙 | `kind`,`usage_note`,`od_value`,`od_unit`,`wall_value`,`wall_unit`,`weight_value`,`weight_unit`,`grade`,`connection`,`range_class`,`length_value`,`length_unit`,`qty_value`,`qty_unit`,`note`（04-db.md `item_edits.field` に書き戻し済み）。`due_raw`/`place_raw` は**編集不可**（原則4） |
| ③ | `old_value` / `old_state` | **訂正時点の現在値**（直前の有効訂正適用後）。Service が確定して保存 |
| ④ | 未確定版（`finalized_at IS NULL`）への人の記録 | **拒否**。コードは `E_NOT_FOUND`（画面に存在しない版） |
| ⑤ | `review_checked` 版への訂正で状態イベントを積む契約（05:438 / 04-db:775） | **T-301 では実装しない**（G3 で到達不能）。T-501 の指示書へ転記（memory TODO-019） |
| ⑥ | 取消者の記録 | **`undone_by` 列を `item_edits` / `confirmations` に追加**（`CHECK(undone_at IS NULL OR trim(undone_by)<>'')`）。取消 API は `recorded_by` 相当の入力を必須にする（memory AD-017。04-db に書き戻し済み） |
| ⑦ | #32（確認取消） | **T-301 に Repository/Service、T-302 に endpoint**。tickets.md 訂正済み |
| ⑧ | `recorded_at` / `undone_at` | **サーバ採時のみ**（`datetime.now(UTC)` を Service で確定）。API 入力に置かない（T-302 へ伝達） |
| ⑨ | `run_repository._has_records`（raw SQL・テーブル存在分岐）と `tests/integration/test_runs.py` の carry-over テスト | **T-301 で ORM 化**（実テーブル導入で必然的に壊れる）。振る舞い不変を 3 点（diff・関数名・assert 数）で示す（LN-032） |
| ⑩ | `E_TARGET_INVALID`（確認）と `E_NOT_FOUND`（訂正の版外 item） | 設計どおり別コード |

## 1. 範囲と範囲外

**範囲（BE のみ）**: domain 入力型 → ORM＋migration（`item_edits` / `confirmations` / `question_judgements`。現状未作成）→ Repository → Service（記録 5 種 #29〜#33 と読取 4 種 #23〜#26 の材料）。
**範囲外**: API endpoint / DTO / `app/api/errors.py` の status 追加 / OpenAPI・orval（T-302）、画面（T-303）、版の状態遷移・`version_state_events`・差し戻し・送付可否（T-501）、インベントリ照合（T-401・並行可）、`app/agent/` 一切（ツール追加禁止。05-api-ipo「登録するのは 13 本だけ」）。

## 2. 前提となる決定（引用）

- `recorded_by` / `undone_by` は画面の入力値。NOT NULL（undone_by は取消時）・空文字禁止（CHECK）。**AI・Service が補完しない**（CLAUDE.md 決定事項1 / 04-db 原則5 / 02:183）
- 人の記録 API は `/ui/*` のみ。`tests/fixtures/route_contract.py` の `UI_ONLY_SEGMENTS` に `edits` `confirmations` `judgements` は登録済み
- 換算値の列を作らない（決定事項4）。`new_value` は text 1 列
- 日時は `timestamptz`、数量は `numeric`（決定事項2）
- 追記型。UPDATE は `undone_at`/`undone_by` の付与のみ（04-db 原則1・:698）
- 複合 FK `(version_id, item_id) → items(version_id, id)`（原則2）
- CHECK・部分 UNIQUE は migration と ORM `__table_args__` の両方に**同名で**（04-db 0.5。手本: `app/models/drafts.py` / `alembic/versions/t201_artifacts.py`）
- 集約資産は import（CV-015）: `DraftRepository._transaction()`（SQLSTATE 限定翻訳）・`require()`。HTTP status 表は T-302 で `app/api/errors.py` に追記
- テスト間 import 禁止（CV-021）。共有ビルダは `tests/fixtures/record_data.py`
- ORM 変更と同手順で `make migrate`（LN-013・LN-017）。適用済みリビジョンを編集しない（LN-018）。新リビジョンは `down_revision="add_run_step_locator_index"`（着手時に `alembic heads` で単一ヘッドを再確認）
- ファイル名にチケット ID を入れない（CV-017）: 例 `app/models/records.py` / `app/repositories/record_repository.py` / `app/services/record_service.py` / `alembic/versions/human_records.py`
- Service は ORM を直接触らない（CV-005）。`recorded_at` 等のデータ事実は Service で確定（CV-009）

## 3. 明細の現在値算出

- 現在値 = `items` の値と状態 ＋ 未取消 `item_edits` を `(recorded_at, id)` 昇順で適用。**キャッシュしない・`items` を UPDATE しない**（04-db:723・:848）
- `*_raw` は不変・訂正対象外（原則4）。適用後も「値と状態が対」を保つ（04-db:569-577・:723）
- 状態のみ訂正（`new_value IS NULL`）が正当。`new_value` と `new_state` の少なくとも一方は必須。`new_state` が `stated`/`numeric` 以外なら当該項目の値は None
- 数量の訂正は `qty_value` と `qty_unit` を**同一トランザクションで 2 行**。単位なし数量を作らない（`E_QTY_UNIT_REQUIRED`）
- 取消 = `undone_at`＋`undone_by` 付与。再取消は `E_ALREADY_UNDONE`
- 訂正履歴（#24・SCR-04）は**取消済みを含む全行**（項目・旧値→新値・理由・修正者・日時・取消日時・取消者）
- 純粋関数 `apply_edits(item, edits) -> CurrentItem` を `app/services/item_current_values.py` に置く（duck-typing。`tests/fixtures/draft_data.py` の `snapshot()` と同じ流儀）→ unit テスト

## 4. 人の記録の保存仕様

**共通**: 毎回新しい行を INSERT（05 0.2。`E_NO_CHANGE` は置かない）。`recorded_by` は `StringConstraints(strip_whitespace=True, min_length=1)`（LN-007）→ 欠落は `E_RECORDER_REQUIRED`。版行を `FOR UPDATE` で直列化（`DraftRepository.edit()` と同型。ただし**確定済み版が対象**で、未確定版は `E_NOT_FOUND`）。`RecordRepository` を新設し `_transaction()` / `require()` を import で共用（`DraftRepository` を継承しない）。`versions.current_state` は変更しない。

**item_edits（#29 / #30）**: 検査順 ①`reason` 空 → `E_REASON_REQUIRED` ②`recorded_by` 空 → `E_RECORDER_REQUIRED` ③`field` 語彙外 → `E_FIELD_NOT_EDITABLE` ④値も状態も無し／矛盾 → `E_STATE_VALUE_CONFLICT` ⑤数量に単位なし → `E_QTY_UNIT_REQUIRED` ⑥版外 item → `E_NOT_FOUND`（23503 も同コードへ）。取消 #30: 版外 → `E_NOT_FOUND`、既取消 → `E_ALREADY_UNDONE`、`undone_by` 空 → `E_RECORDER_REQUIRED`。

**confirmations（#31 / #32）**: `kind='row_match'` は `item_id` 必須・`coverage` は NULL（CHECK）。`row_match` の版外 item → `E_TARGET_INVALID`。未取消の重複 → `E_ALREADY_CONFIRMED`（部分 UNIQUE の 23505 を**制約名で限定翻訳**＋Service 事前チェックの両方）。取消 #32: `undone_at`/`undone_by`、`E_ALREADY_UNDONE`。`coverage` は G4 の入口だが Repository は kind 非依存で 1 本。

**question_judgements（#33）**: `status ∈ {open,in_progress,judged}` と `resolution ∈ {unresolved,resolved}` は**別列**（`judged`∧`unresolved` は正当。06 TEST-09 #5）。版外 question → `E_NOT_FOUND`。最新判断 = `(recorded_at, id)` 降順先頭。未解決件数 = 最新判断が無い or `unresolved` の件数。`undone_at` は持たない。

**AGENT-01 が呼べないこと**: `AGENT_TOOL_NAMES` に追加しない。`AgentToolGateway` に D層の書込を足さない。

## 5. 実装順序と RED→GREEN（層順・下位は mock）

| 順 | 成果物 | RED（先に書く） | 置き場 |
|---|---|---|---|
| 1 | `app/domain/record_types.py`（`ItemEditInput` / `UndoInput` / `ConfirmationInput` / `JudgementInput`。`draft_types.Input` を継承し `field_error_codes` で業務コード） | 空 reason / 空白のみ recorded_by / 語彙外 field / 両 None / 数量単位なし | `tests/unit/test_record_inputs.py` |
| 2 | `app/services/item_current_values.py`（`apply_edits`） | 訂正→現在値 / 取消→元に戻る / 状態のみ訂正で値 None / 数量 2 行 / 履歴順序（取消含む）/ `*_raw` 不変 / 同一項目後勝ち | `tests/unit/test_item_current_values.py` |
| 3 | ORM `app/models/records.py`＋`models/__init__.py`＋migration `alembic/versions/human_records.py` | **実 DB**で制約 RED: 空 recorded_by 23514 / 両 NULL 23514 / 別版 item 23503 / `row_match` 二重 23505 / `coverage` 二重 23505 / 取消済み後に再登録できる（部分 UNIQUE の WHERE）/ `undone_at` ありで `undone_by` 空 23514 | `tests/integration/test_record_schema.py` |
| 4 | `app/repositories/record_repository.py` | §4 の各コード＋正常系。実 DB integration（SQLite fixture は FOR UPDATE・部分 UNIQUE を保証しない。LN-014・LN-026） | `tests/integration/test_record_repository.py` |
| 5 | `app/services/record_service.py` | Repository を mock（`tests/unit/test_draft_service.py` と同型）。数量 2 行が同一 `record()` 内 / `old_value` が直前有効訂正後の値 / `E_ALREADY_UNDONE` / 版外 `E_NOT_FOUND` / `recorded_at` サーバ採時 | `tests/unit/test_record_service.py` |
| 6 | 読取 Repository/Service: `list_items_with_edits(version_id)` / `summary(version_id)`（照合 n/N・訂正 n・未解決 n・明細数・確認事項のある行・数量 TBA・択一グループ）/ `list_questions_with_latest(version_id)` / `list_item_evidence(version_id, item_id)` | 実 DB integration。件数は**集合一致**で assert（RV-017 P3） | `tests/integration/test_record_queries.py` |
| 7 | 既存追従: `tests/integration/test_runs.py` の carry-over テストは raw SQL `CREATE TABLE item_edits` を作るため実テーブル導入で衝突する。ORM 行 INSERT に書換え、`run_repository._has_records` の存在分岐を外して ORM/`select` に置換（振る舞い不変。変更理由を handoff に必ず書く） | 変更前に落ちることを実測し記録 | 同ファイル |

## 6. migration（新規・必須）

- `down_revision="add_run_step_locator_index"`。3 テーブル `id bigserial PK` / `created_at timestamptz NOT NULL DEFAULT now()`（`updated_at` 無し）
- 明示する制約（ORM `__table_args__` にも同名で）:
  - `item_edits`: FK version/item、複合 FK、`CHECK(trim(reason)<>'')`、`CHECK(trim(recorded_by)<>'')`、`CHECK(new_value IS NOT NULL OR new_state IS NOT NULL)`、`CHECK(new_state IN (...))`、`CHECK(field IN (§0 ②の語彙))`、`CHECK(undone_at IS NULL OR trim(undone_by)<>'')`、索引 `(version_id)`・`(item_id)`
  - `confirmations`: 複合 FK、`CHECK(kind IN ('row_match','coverage'))`、`CHECK((kind='row_match' AND item_id IS NOT NULL) OR (kind='coverage' AND item_id IS NULL))`、`CHECK(trim(recorded_by)<>'')`、`CHECK(undone_at IS NULL OR trim(undone_by)<>'')`、部分 UNIQUE 2 本（`WHERE kind='row_match' AND undone_at IS NULL` / `WHERE kind='coverage' AND undone_at IS NULL`。`Index(..., unique=True, postgresql_where=text(...))`）、索引 `(version_id)`・`(item_id)`
  - `question_judgements`: FK questions、`CHECK(status IN ('open','in_progress','judged'))`、`CHECK(resolution IN ('unresolved','resolved'))`、`CHECK(trim(recorded_by)<>'')`、索引 `(question_id)`
- 完了確認は**実 DB（両 DB の `\d item_edits` 等）**で（LN-018・LN-026）。psql 出力を handoff に貼る

## 7. 完了条件

- `DEBUG=false CI=true make check` all green（既存 BE 424 / FE 166 ＋新規。CV-016）
- 両 DB に migration 適用済み・`\d` 実出力
- `docs/t301-handoff.md`: 冒頭に触ったファイル一覧 → 「レビュー対応」表（項目 / 変更 file:line / RED を確認したテスト名・コマンド・件数 / 変異 1 行）→ 既存テスト変更の理由（§5 順 7）→ `make check` 実出力 → 末尾に固定文字列 **「再レビュー依頼」**
- ツール登録・`/agent/*` に変更が無い（`test_api_path_separation.py` / `test_single_source_of_truth.py` を消さない・弱めない）。commit は Claude
