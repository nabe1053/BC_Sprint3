# T-501 handoff

## 変更ファイル（着手時に範囲宣言済み）

- domain: `backend/app/domain/record_types.py`
- service: 新規 `backend/app/services/version_state.py` / `approval_service.py`、既存 `record_service.py`
- repository: `backend/app/repositories/record_repository.py`
- ORM/migration: 新規 `backend/app/models/approvals.py` / `backend/alembic/versions/approval_records.py`、`backend/app/models/__init__.py`
- tests: `tests/unit/test_record_inputs.py` / `test_record_service.py` / `test_single_source_of_truth.py` に追記、新規 `test_version_state.py` / `test_approval_service.py`。integration新規 `test_approval_schema.py` / `test_approval_repository.py` / `test_approval_queries.py`、既存 `test_record_repository.py` に追記。共通 `tests/fixtures/record_data.py` を拡張。
- 本handoffと `docs/test-results/approval-*` の検証出力。

§7「2026-09-13 T-403 handoff受領・T-501へ」と `docs/t501-instructions.md` / AD-028を確認して着手。Status: 実装・検証完了。T-501 の差分は上記 BE と handoff・検証ログに限定。

## 実装状況

T-501 のコード・対象テスト・最終ゲートを完了。R-2 は先に完了し、結果を `docs/t403-handoff.md` に記録済み。以下のパスは特記なき限り `backend/` 相対。

## AD-028 の反映

| 決定 | 反映箇所・振る舞い |
|---|---|
| ① | `app/services/version_state.py:9`: 全行の未取消 row_match と coverage を両方要求。未解決は遷移条件にしない |
| ② | `app/domain/record_types.py:139` / `app/services/approval_service.py:23`: recorder→戻し禁止→順序→未照合→coverage。未照合 details は ID 昇順・対応 row_code 同順 |
| ③ | `app/services/version_state.py:9`: draft→staff と staff→review だけ許可。同一・飛越・review→staff の直接操作は拒否 |
| ④ | `app/domain/record_types.py:139` / `version_state.py:9`: domain コードのみ。HTTP マッピングは未変更 |
| ⑤ | `app/services/approval_service.py:55`: bounce は staff のみ。draft と review のコードを区別 |
| ⑥ | `app/services/version_state.py:38` / `approval_service.py:55`: 未紐付けコメントを日時・ID 順で `row_code: comment` に連結。入力は記録者だけ |
| ⑦ | `app/repositories/record_repository.py:340`: INSERT と `bounce_id IS NULL` に限定した UPDATE を同一ロック・トランザクション内で実行 |
| ⑧ | `app/services/approval_service.py:46` / `:81`: comment・sendoff に業務状態制限なし。`record()` が確定版を要求 |
| ⑨ | `app/services/record_service.py:38`: 訂正保存後、review のときだけ同じ記録者・時刻の review→staff イベントを追加。undo/confirm/judge は追加なし |
| ⑩ | `app/repositories/record_repository.py:426` / `:450`: 履歴は削除せず、状態イベントと最新評価確認日時を返す |
| ⑪ | `app/models/approvals.py:15` / `alembic/versions/approval_records.py`: from_state 列挙・from≠to を同名 CHECK で実装 |
| ⑫ | `app/repositories/record_repository.py:292` / `tests/unit/test_single_source_of_truth.py:205`: 状態更新は保存メソッド内。初期化 `DraftRepository.complete` と合わせて代入箇所を AST で完全一致検査 |
| ⑬ | `app/repositories/record_repository.py:450`: 未取消訂正行数・未取消一致行数・item 数・coverage 有無・判断のある質問数。イベント等は加算なし |
| ⑭ | `app/services/approval_service.py:19` / `app/repositories/record_repository.py:43`: Service 新設、ロック所有者は既存 Repository のまま。`record()` は版を yield |
| ⑮ | `app/domain/record_types.py:189` / `app/services/version_state.py:34` / `record_service.py:174`: 未解決述語を domain に一元化し、Service の `unresolved_count` と summary から共用。Repository→Service の逆向き import を作らず #22 も同じ述語を利用 |
| ⑯ | `app/repositories/record_repository.py:450`: 最新 bounce と最新 review_checked 時刻を返す。「差し戻し中」の boolean 化は T-502 |
| ⑰ | `app/domain/record_types.py:147`: 空コメントは E_COMMENT_REQUIRED |
| ⑱ | `app/services/record_service.py:174`: summary の既存キーを維持。未解決の計算だけ共通関数へ |

§7 の AD-029 ⑤追補も反映: `latest_review_checked_at` は最新イベントが staff_checked に変わっても過去の評価確認日時を保持し、未評価は None。追加 SELECT なし。`tests/integration/test_approval_queries.py:205` で訂正→差し戻し後の保持を確認。

## レビュー対応

共通実行環境は `AGENT_MODE=local_dummy DEBUG=false CI=true`。RED/高速確認は root Makefile に `/tmp/approval-checks.mk` を追加して実行（例: `make -f Makefile -f /tmp/approval-checks.mk approval-state`）。pytest と jest は逐次実行。変異は `/tmp` の隔離コピーだけを変更し、実装ファイルは変更しない。

| 項目 | 変更 file:line | RED テスト・ターゲット・件数 | 検出する変異 1 行 |
|---|---|---|---|
| 入力と理由必須 | `app/domain/record_types.py:139` | `test_approval_input_codes_and_recorder_precedence` 等、`approval-inputs`: 9 failed / 10 passed | sendoff の `if self.decision != "undecided" and self.reason is None:` → `if False:` |
| 遷移順序・前提・details | `app/services/version_state.py:9` | `test_out_of_order_or_repeated_transition` / `test_unmatched_error_includes_ordered_ids_rows_and_missing_coverage` / `test_coverage_is_checked_after_all_matches`、`approval-state`: 12 failed | 順序ガード・未照合ガード・coverage ガードをそれぞれ無効化 |
| 未解決・差し戻し理由 | `app/services/version_state.py:34` | `test_unresolved_count_is_latest_resolution_not_judged_status` / `test_bounce_reason_is_ordered_by_server_time_and_id`、同上 | resolution 判定を status 判定へ／日時順を逆 ID 優先へ |
| 4 テーブル実制約 | `app/models/approvals.py:15` / 新 migration | `test_approval_constraints_are_enforced_in_postgres` 等、`approval-schema`: 未作成時 14 failed / 1 passed → 15 passed | raw INSERT で禁止状態・同一状態・空記録者・理由欠落・版外 item を注入し 23514/23503 を検証 |
| イベント/cache と実ロック | `app/repositories/record_repository.py:292` | `test_event_and_cached_state_commit_or_rollback_together` / `test_two_sessions_block_then_reject_repeated_transition`、`approval-repository`: 初回 5 failed / 5 passed | cache 代入削除／ロック再読込 populate_existing を False |
| コメントの一度限りの紐付け | `app/repositories/record_repository.py:340` | `test_bounce_links_comments_once_without_changing_state_or_events`、同上 | UPDATE の `bounce_id IS NULL` 条件を削除 |
| 一覧・carryOver・固定クエリ | `app/repositories/record_repository.py:364` | `test_record_collections_include_cancellations_and_keep_version_scope` / `test_query_count_is_constant_and_latest_records_use_time_then_id`、同上 | active edit 数を全行数へ／判断質問数を判断行数へ／一覧 ORDER BY を ID のみに |
| Service の検査順・サーバ時刻 | `app/services/approval_service.py:23` | `test_transition_error_priority` / `test_transition_records_current_unresolved_and_server_time` 等、`approval-service`: 15 failed / 4 passed → 19 passed | 上記遷移・理由のガード変異。Repository mock は保存時のロック保持を assert |
| 訂正に付随する降格 | `app/services/record_service.py:38` | `test_edit_only_downgrades_review_and_reuses_actor_time[review_checked]`: 1 failed / 23 passed、実 DB 追加時 2 failed / 10 passed | review 判定を `if False:` |
| 最新評価日時の保持 | `app/repositories/record_repository.py:484` | `test_latest_review_time_survives_bounce_and_corrective_downgrade`、`approval-repository`: KeyError 1 failed / 11 passed | review_checked の探索を staff_checked に変更 |
| 書込 SSOT | `tests/unit/test_single_source_of_truth.py:205` | 2 箇所化後に追加、正常系 10 passed。独立した追加 writer を注入して RED を確認 | `ApprovalService` 側に `version.current_state = "draft"` を追加 |

追加の境界検証: 版外 item・未確定版を全 4 操作で拒否、bounce の途中例外で INSERT と紐付けが両方 rollback、訂正イベント保存後の例外で訂正・イベント・cache が全部 rollback。数量訂正 2 行を editCount=2、取消 row_match を 0、同一質問への判断 2 行を judgementCount=1 と検証。一覧全 7 種と bounce 内コメントは、日時と挿入順が異なるデータでも `(recorded_at,id)` 順の ID 完全一致。

## 既存テスト変更の理由

`tests/unit/test_record_service.py` の mock `record()` は実 Repository と同じ版を yield するよう更新し、finally でロック状態を戻す。元の検証は削除していない。`tests/fixtures/record_data.py` の `seed_record_version(state=...)` は非 draft の初期状態に対応するイベントを入れ、テストデータの cache と履歴を一致させた。summary はキーを追加せず、同じ質問材料に対して既存 summary と遷移用カウンタが一致するテストを追加。

最初の全体 BE 実行は 1 failed / 692 passed。新規の未確定版テストが rollback 後の ORM 属性を同期参照して MissingGreenlet となったため、ID を事前保持するよう修正。実装のエラーを隠す除外や skip は追加していない。

## T-502 へ渡す契約

Service 入力は snake_case の dict（DTO から変換）。記録者は入力必須・trim、時刻はサーバ UTC。戻り値:

| メソッド | 戻り値 |
|---|---|
| `ApprovalService.transition(version_id, data)` | `VersionStateEvent` ORM 行 |
| `comment(version_id, data)` | `BounceComment` ORM 行（作成時 bounce_id=None） |
| `bounce(version_id, data)` | `Bounce` ORM 行。入力は recorded_by のみ、reason は未紐付けコメントから構成 |
| `decide_sendoff(version_id, data)` | `SendoffDecision` ORM 行 |
| `list_records(version_id)` | dict: `edits`, `confirmations`, `judgements`, `state_events`, `bounces`, `unlinked_comments`, `sendoff_decisions`。全記録を含む（取消済みも含む）。`bounces` 各要素は `{bounce: ORM行, comments: ORM行配列}`。各配列は `(recorded_at,id)` 昇順 |
| `list_versions_with_records(case_id)` | 確定版の version_no 降順の dict 配列。キーは `version`, `carry_over`, `unresolved_count`, `latest_state_event`, `latest_review_checked_at`, `latest_bounce`, `latest_sendoff_decision` |

`carry_over` は frozen `CarryOver(edit_count, row_match_confirmed, row_match_total, coverage_recorded, judgement_count)`。latest 3 行は ORM 行または None、latest_review_checked_at は datetime または None。版 1 件／4 件でも query 数固定（材料をまとめて取得）。`RecordService.edit` の戻り値は従来どおり ItemEdit 配列。

| 新コード | 推奨 HTTP |
|---|---|
| E_STAFF_CHECK_INCOMPLETE | 409 |
| E_COVERAGE_NOT_RECORDED | 409 |
| E_STATE_ORDER | 409 |
| E_STATE_ROLLBACK_FORBIDDEN | 422 |
| E_NO_BOUNCE_COMMENT | 409 |
| E_SENDOFF_REASON_REQUIRED | 400 |
| E_COMMENT_REQUIRED | 400 |

`errors.py` は未変更。未照合 details は camelCase の `unmatchedItemIds`（昇順）、`unmatchedRowCodes`（同順）、`coverageRecorded`（bool）。draft の bounce 拒否は同じ E_STAFF_CHECK_INCOMPLETE だが未照合配列の details は持たない。

「再確認が必要」は最新 review_checked イベントより後の staff_checked イベントから、「差し戻し中」は最新 bounce より後の review_checked がないことから T-502 が導出する。時系列材料を削除せず、T-501 は boolean や DTO を作らない。#36 の HTTP リクエストは `recordedBy` だけ。

## Migration 実出力

新規 `approval_records`（down_revision=`human_records`）を root `make migrate` で両 DB に適用。適用済みリビジョンの編集なし。

```text
── alembic upgrade head (octg_db / 開発)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade human_records -> approval_records, Create state events, bounce records and independent sendoff decisions.
── alembic upgrade head (octg_test / テスト)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade human_records -> approval_records, Create state events, bounce records and independent sendoff decisions.
```

### octg_db（開発）

`psql` の `\d version_state_events` / `\d bounces` / `\d bounce_comments` / `\d sendoff_decisions` 実出力（追加 Make ターゲット `approval-describe`）。

```text
                                          Table "public.version_state_events"
      Column      |           Type           | Collation | Nullable |                     Default                      
------------------+--------------------------+-----------+----------+--------------------------------------------------
 id               | bigint                   |           | not null | nextval('version_state_events_id_seq'::regclass)
 created_at       | timestamp with time zone |           | not null | now()
 recorded_by      | text                     |           | not null | 
 recorded_at      | timestamp with time zone |           | not null | 
 version_id       | bigint                   |           | not null | 
 from_state       | text                     |           | not null | 
 to_state         | text                     |           | not null | 
 unresolved_count | integer                  |           | not null | 
Indexes:
    "version_state_events_pkey" PRIMARY KEY, btree (id)
    "ix_version_state_events_version_id" btree (version_id)
Check constraints:
    "ck_version_state_events_from_state" CHECK (from_state = ANY (ARRAY['draft'::text, 'staff_checked'::text, 'review_checked'::text]))
    "ck_version_state_events_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_version_state_events_to_state" CHECK (to_state = ANY (ARRAY['staff_checked'::text, 'review_checked'::text]))
    "ck_version_state_events_transition" CHECK (from_state <> to_state)
Foreign-key constraints:
    "fk_version_state_events_version" FOREIGN KEY (version_id) REFERENCES versions(id)

                                       Table "public.bounces"
   Column    |           Type           | Collation | Nullable |               Default               
-------------+--------------------------+-----------+----------+-------------------------------------
 id          | bigint                   |           | not null | nextval('bounces_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 reason      | text                     |           | not null | 
Indexes:
    "bounces_pkey" PRIMARY KEY, btree (id)
    "ix_bounces_version_id" btree (version_id)
Check constraints:
    "ck_bounces_reason" CHECK (TRIM(BOTH FROM reason) <> ''::text)
    "ck_bounces_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_bounces_version" FOREIGN KEY (version_id) REFERENCES versions(id)
Referenced by:
    TABLE "bounce_comments" CONSTRAINT "fk_bounce_comments_bounce" FOREIGN KEY (bounce_id) REFERENCES bounces(id)

                                       Table "public.bounce_comments"
   Column    |           Type           | Collation | Nullable |                   Default                   
-------------+--------------------------+-----------+----------+---------------------------------------------
 id          | bigint                   |           | not null | nextval('bounce_comments_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 item_id     | bigint                   |           | not null | 
 bounce_id   | bigint                   |           |          | 
 comment     | text                     |           | not null | 
Indexes:
    "bounce_comments_pkey" PRIMARY KEY, btree (id)
    "ix_bounce_comments_bounce_id" btree (bounce_id)
    "ix_bounce_comments_item_id" btree (item_id)
    "ix_bounce_comments_version_id" btree (version_id)
Check constraints:
    "ck_bounce_comments_comment" CHECK (TRIM(BOTH FROM comment) <> ''::text)
    "ck_bounce_comments_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_bounce_comments_bounce" FOREIGN KEY (bounce_id) REFERENCES bounces(id)
    "fk_bounce_comments_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_bounce_comments_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_bounce_comments_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.sendoff_decisions"
   Column    |           Type           | Collation | Nullable |                    Default                    
-------------+--------------------------+-----------+----------+-----------------------------------------------
 id          | bigint                   |           | not null | nextval('sendoff_decisions_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 decision    | text                     |           | not null | 
 reason      | text                     |           |          | 
Indexes:
    "sendoff_decisions_pkey" PRIMARY KEY, btree (id)
    "ix_sendoff_decisions_version_id" btree (version_id)
Check constraints:
    "ck_sendoff_decisions_decision" CHECK (decision = ANY (ARRAY['undecided'::text, 'hold'::text, 'approved'::text]))
    "ck_sendoff_decisions_reason" CHECK (decision = 'undecided'::text OR reason IS NOT NULL AND TRIM(BOTH FROM reason) <> ''::text)
    "ck_sendoff_decisions_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_sendoff_decisions_version" FOREIGN KEY (version_id) REFERENCES versions(id)

```

### octg_test（テスト）

`psql` の `\d version_state_events` / `\d bounces` / `\d bounce_comments` / `\d sendoff_decisions` 実出力（追加 Make ターゲット `approval-describe`）。

```text
                                          Table "public.version_state_events"
      Column      |           Type           | Collation | Nullable |                     Default                      
------------------+--------------------------+-----------+----------+--------------------------------------------------
 id               | bigint                   |           | not null | nextval('version_state_events_id_seq'::regclass)
 created_at       | timestamp with time zone |           | not null | now()
 recorded_by      | text                     |           | not null | 
 recorded_at      | timestamp with time zone |           | not null | 
 version_id       | bigint                   |           | not null | 
 from_state       | text                     |           | not null | 
 to_state         | text                     |           | not null | 
 unresolved_count | integer                  |           | not null | 
Indexes:
    "version_state_events_pkey" PRIMARY KEY, btree (id)
    "ix_version_state_events_version_id" btree (version_id)
Check constraints:
    "ck_version_state_events_from_state" CHECK (from_state = ANY (ARRAY['draft'::text, 'staff_checked'::text, 'review_checked'::text]))
    "ck_version_state_events_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_version_state_events_to_state" CHECK (to_state = ANY (ARRAY['staff_checked'::text, 'review_checked'::text]))
    "ck_version_state_events_transition" CHECK (from_state <> to_state)
Foreign-key constraints:
    "fk_version_state_events_version" FOREIGN KEY (version_id) REFERENCES versions(id)

                                       Table "public.bounces"
   Column    |           Type           | Collation | Nullable |               Default               
-------------+--------------------------+-----------+----------+-------------------------------------
 id          | bigint                   |           | not null | nextval('bounces_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 reason      | text                     |           | not null | 
Indexes:
    "bounces_pkey" PRIMARY KEY, btree (id)
    "ix_bounces_version_id" btree (version_id)
Check constraints:
    "ck_bounces_reason" CHECK (TRIM(BOTH FROM reason) <> ''::text)
    "ck_bounces_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_bounces_version" FOREIGN KEY (version_id) REFERENCES versions(id)
Referenced by:
    TABLE "bounce_comments" CONSTRAINT "fk_bounce_comments_bounce" FOREIGN KEY (bounce_id) REFERENCES bounces(id)

                                       Table "public.bounce_comments"
   Column    |           Type           | Collation | Nullable |                   Default                   
-------------+--------------------------+-----------+----------+---------------------------------------------
 id          | bigint                   |           | not null | nextval('bounce_comments_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 item_id     | bigint                   |           | not null | 
 bounce_id   | bigint                   |           |          | 
 comment     | text                     |           | not null | 
Indexes:
    "bounce_comments_pkey" PRIMARY KEY, btree (id)
    "ix_bounce_comments_bounce_id" btree (bounce_id)
    "ix_bounce_comments_item_id" btree (item_id)
    "ix_bounce_comments_version_id" btree (version_id)
Check constraints:
    "ck_bounce_comments_comment" CHECK (TRIM(BOTH FROM comment) <> ''::text)
    "ck_bounce_comments_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_bounce_comments_bounce" FOREIGN KEY (bounce_id) REFERENCES bounces(id)
    "fk_bounce_comments_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_bounce_comments_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_bounce_comments_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.sendoff_decisions"
   Column    |           Type           | Collation | Nullable |                    Default                    
-------------+--------------------------+-----------+----------+-----------------------------------------------
 id          | bigint                   |           | not null | nextval('sendoff_decisions_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null | 
 recorded_at | timestamp with time zone |           | not null | 
 version_id  | bigint                   |           | not null | 
 decision    | text                     |           | not null | 
 reason      | text                     |           |          | 
Indexes:
    "sendoff_decisions_pkey" PRIMARY KEY, btree (id)
    "ix_sendoff_decisions_version_id" btree (version_id)
Check constraints:
    "ck_sendoff_decisions_decision" CHECK (decision = ANY (ARRAY['undecided'::text, 'hold'::text, 'approved'::text]))
    "ck_sendoff_decisions_reason" CHECK (decision = 'undecided'::text OR reason IS NOT NULL AND TRIM(BOTH FROM reason) <> ''::text)
    "ck_sendoff_decisions_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
Foreign-key constraints:
    "fk_sendoff_decisions_version" FOREIGN KEY (version_id) REFERENCES versions(id)

```

`approval-heads`（`uv run alembic heads`）: `approval_records (head)` の単一 head。

## 最終検証

`AGENT_MODE=local_dummy DEBUG=false CI=true make check` の実出力抜粋。全文は `docs/test-results/approval-final-check-2026-09-13.log`。

```text
694 passed, 166 warnings in 76.25s (0:01:16)
✅ check-be: backend green
All matched files use Prettier code style!
Test Suites: 24 passed, 24 total
Tests:       327 passed, 327 total
Snapshots:   0 total
Time:        21.021 s, estimated 25 s
✅ check: all green
```

BE 625 → **694 passed**（+69）、FE **24 suites / 327 passed**。root ゲート内で両 DB migration・索引検証・ruff・全 pytest・OpenAPI/orval・tsc・ESLint/Prettier・全 jest を逐次実施。既存の 166 warnings はゲート実出力に保存。

対象最終確認は `approval-service` **24 passed**、`approval-repository` **17 passed**。`approval-schema` は **15 passed**。15 種類の変異をすべて検出。SSOT 変異の初回コピーでは参照ドキュメント不足による別の失敗も出たため、docs の参照を揃えて当該変異だけ再実行し **1 failed / 9 passed**（意図した追加 writer の検出のみ）を確認した。

```text
record-order: detected 1 failed, 16 passed, 1 warning in 9.95s
order: detected 5 failed, 7 passed in 0.07s
unmatched: detected 1 failed, 11 passed in 0.06s
coverage: detected 2 failed, 10 passed in 0.06s
resolution: detected 1 failed, 11 passed in 0.06s
bounce-order: detected 1 failed, 11 passed in 0.07s
sendoff-reason: detected 1 failed, 18 passed in 0.07s
cache: detected 4 failed, 13 passed, 1 warning in 10.42s
lock-refresh: detected 1 failed, 16 passed, 1 warning in 9.86s
bounce-once: detected 1 failed, 16 passed, 1 warning in 10.59s
active-edits: detected 1 failed, 16 passed, 1 warning in 10.77s
judgement-count: detected 1 failed, 16 passed, 1 warning in 10.01s
review-time: detected 1 failed, 16 passed, 1 warning in 11.75s
edit-downgrade: detected 1 failed, 23 passed in 0.28s
ssot: detected 1 failed, 9 passed in 0.45s
```

検証ログは `docs/test-results/approval-*-2026-09-13.log`。API・AGENT・OpenAPI の着手時ハッシュと一致。OpenAPI schema は 72、Orval 生成モデルは **146** のまま。適用済み migration・`run_repository._has_records`・ルート契約・`.claude/memory.md` に実装変更なし。commit は行っていない。

## 再レビュー依頼（T-501）

## 独立レビュー（T-501・第1回）

RV 候補:

- T-501 第1回・フレッシュ文脈の独立レビュー: **P1 0 / P2 0 / P3 0、DONE 可**。AD-028 の18決定と最新評価確認日時の追補を実コード・設計書・テストで照合。
- `AGENT_MODE=local_dummy DEBUG=false CI=true make check` を独立に1回実行して exit 0。BE **694 passed / 166 warnings**、FE **24 suites / 327 passed** を再現。ログ: `/tmp/approval-independent-review-check.log`。
- 実 PostgreSQL 2セッションの block 観測・解放後拒否、イベント/cache と訂正の rollback、bounce_id 一度限り、carryOver・未解決述語・既存テスト不変を確認。OpenAPI/API/Agent の保護対象44ファイルは着手時 SHA-256 と一致。

判定根拠（以下は `backend/` 相対）:

| 決定 | 独立照合した file:line |
|---|---|
| ① | `app/services/version_state.py:17`、`app/repositories/record_repository.py:273`: 未取消 row_match 全件と coverage を要求。未解決は条件に含めない |
| ② | `app/domain/record_types.py:139`、`app/services/approval_service.py:24`、`app/services/version_state.py:12`: recorder・戻し禁止・順序・未照合・coverage の順。details のキーと昇順対応も一致 |
| ③ | `app/services/version_state.py:12`: draft→staff / staff→review のみ受理。`tests/unit/test_version_state.py:50` が同一・飛越・逆行を検査 |
| ④ | `app/domain/record_types.py:140`、`app/services/version_state.py:16`: domain コードのみ追加。`app/api/errors.py` は無変更 |
| ⑤ | `app/services/approval_service.py:64`: review 版の bounce は E_STATE_ORDER。`tests/unit/test_approval_service.py:114` の状態別拒否で検証 |
| ⑥ | `app/domain/record_types.py:153`、`app/services/approval_service.py:69`、`app/services/version_state.py:38`: recorded_by のみ受け、未紐付けコメントを日時・ID順に連結 |
| ⑦ | `app/repositories/record_repository.py:340`: bounce INSERT と NULL 条件付き UPDATE。`tests/integration/test_approval_repository.py:122` で既紐付け行の不変を検証 |
| ⑧ | `app/services/approval_service.py:46`、`:81`、`app/repositories/record_repository.py:38`: 確定版の任意状態で comment/sendoff、未確定版は拒否 |
| ⑨ | `app/services/record_service.py:102`: edit のみ review→staff を同時刻・同記録者で保存。`tests/unit/test_record_service.py:135`、`tests/integration/test_record_repository.py:217` が他操作と rollback を検査 |
| ⑩ | `app/repositories/record_repository.py:426`、`:484`: 全状態イベントと最新評価確認日時を保持。訂正後も過去の評価記録を削除しない |
| ⑪ | `app/models/approvals.py:23`、`alembic/versions/approval_records.py:28`: from_state 列挙・from≠to を同名 CHECK で保持 |
| ⑫ | `app/repositories/record_repository.py:316`、`tests/unit/test_single_source_of_truth.py:205`: current_state 代入は complete と save_state_event の2箇所 |
| ⑬ | `app/repositories/record_repository.py:469`: 未取消訂正行数・row_match 行数/items 数・coverage・判断を持つ質問数。`tests/integration/test_approval_queries.py:235` で数量訂正2行・取消・同一質問の複数判断を検査。`run_repository._has_records` は無変更 |
| ⑭ | `app/services/approval_service.py:19`、`app/repositories/record_repository.py:43`: 新Serviceと既存Repository拡張。版ロック所有者は1つで yield version |
| ⑮ | `app/domain/record_types.py:189`、`app/services/version_state.py:34`、`app/services/record_service.py:201`、`app/repositories/record_repository.py:480`: 未解決述語はdomainの1定義を共用。RepositoryからServiceへの逆依存なし |
| ⑯ | `app/repositories/record_repository.py:481`、`:484`、`:492`: 最新状態・最新review日時・最新bounceを返す。boolean導出は後続のまま |
| ⑰ | `app/domain/record_types.py:148`: 空コメントに E_COMMENT_REQUIRED |
| ⑱ | `app/services/record_service.py:201`、`:215`: summary は既存キーを保持し、未解決件数の計算だけ共通化 |
| 追補 | `app/repositories/record_repository.py:484`、`tests/integration/test_approval_queries.py:205`: latest_review_checked_at は未評価で None、訂正→差し戻し後も直近の評価日時を維持。版数による追加SELECTなし |

TDD・検証の確認:

- REDログの件数はhandoffの記載と一致。入力・新規Service・純粋関数は未実装による import/属性エラー、訂正・最新評価日時は実挙動の assertion/KeyError によるRED。15変異の保存ログと対応assertも確認した（独立レビューでは変異を再実行していない）。
- 変更された既存テスト4ファイルは、HEADとのAST比較で既存テスト関数削除0・既存assert変更0。共有fixtureの変更は版yieldと履歴整合のためで、除外・skip・テスト間importの追加なし。
- `tests/integration/test_approval_repository.py:48` は実2セッションを使い、stale identity mapを事前投入。`:98` で `pg_blocking_pids` に保持側PIDが現れることを確認し、commit後の E_STATE_ORDER・イベントID集合・cache値までassertする。今回の全体ゲートで通過。
- 両DBのmigrationは既定ゲートで正常終了。追加の読取専用確認でも、開発・テストとも `alembic_version=approval_records`、対象4テーブルの存在を確認。制約は15件の実DBテストで検証。
- BE整形は180ファイル変更なし。OpenAPIは72 schemas、Orvalは146モデル。`/tmp/approval-protected.json` のAPI・Agent・OpenAPI全44対象が現行SHA-256と一致。生成OpenAPIのSHA-256は `9ddf6e8e8dc9fd5e744557a5417e1a815b78c351c3ce0491cc6ec1c8ad542bba`。
- 差分に外部送信・ログ出力の追加なし。提出されたapprovalログでキー形式・秘密鍵・Bearer値の検出なし。`.env*` は読取・表示・編集していない。実モデル呼出し・commit・コード編集なし。

指摘: **P1なし / P2なし / P3なし**。

**DONE 可。**

## 独立レビュー後の記録（ユーザー指示を優先）

B レビューは指摘 P1/P2/P3 各 0、DONE 可。実装と独立検証で BE 694 / FE 327 を再現。独立検証の永続ログ: `docs/test-results/approval-independent-review-check-2026-09-14.log`。レビュー前後で backend 対象ファイルのハッシュ一致。

最新 CODEX-INSTRUCTIONS は C フェーズへの memory 転記・commit を移譲しているが、会話内のユーザー明示指示「.claude/memory.md は読むだけ・編集禁止」「commit はしません」を優先する。以下は未適用の転記案としてこの handoff に記録し、memory・index・commit には反映しない。

- 希望 Status: T-501 DONE（独立レビュー指摘なし、両 gate green）。
- RV-045 候補（現在 RV 最大44、実適用時再採番）: 上記独立レビューの3行要約。
- LN 候補: rollback 後のテストは ORM 属性の暗黙 IO に依存せず、事前に保持した ID で非同期に再取得する。既存 LN と重複する場合は追加不要。
- AD の追加なし、未解決指摘なし。

T-501 の実装・独立レビューは完了。以後のコード作業は §7 の T-502 に切替。未コミット T-501 差分を保全し、各 handoff と差分スナップショットでスライス境界を記録する。
