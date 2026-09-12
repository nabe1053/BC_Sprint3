# T-301 handoff

**T-205 L-3〜L-6 と同一コミット単位（`run_repository._has_records` が `models/records.py` に依存）**。§7 **2026-09-13 04:40版**の指示で再開・完了。希望 Status: **REVIEWING**。

明細の現在値算出、人の記録5種、参照4種のRepository/Serviceを実装。**除外なしのmake check: BE518件 / FE166件がPASS**。T-301の追加テストは46件。commitはしていない。

## 変更ファイル

- `backend/app/domain/record_types.py`
- `backend/app/services/item_current_values.py` / `record_service.py`
- `backend/app/models/records.py` / `__init__.py`
- `backend/alembic/versions/human_records.py`
- `backend/app/repositories/record_repository.py` / `run_repository.py`
- `backend/tests/fixtures/record_data.py`
- `backend/tests/unit/test_record_inputs.py` / `test_item_current_values.py` / `test_record_service.py`
- `backend/tests/integration/test_record_schema.py` / `test_record_repository.py` / `test_record_queries.py` / `test_runs.py`
- 本handoffと `docs/test-results/` の証跡

T-301でT-205のコード/hunk、API・DTO・HTTP対応表・画面は変更していない。`run_repository.py`は承認済みの`_has_records` ORM化と必要importのみ。T-205由来のfinish/turns保持やエージェント実装を保全。`.claude/memory.md`は未編集。

## レビュー対応

| 項目 | 変更 file:line | REDテスト・コマンド・件数 | 変異検証 |
|---|---|---|---|
| 入力・業務コード | `backend/app/domain/record_types.py:43,93,98,114`。16項目の編集語彙、reason→recorder→field順、数量単位、値/状態の整合、取消者必須。時刻は入力に置かない | `test_edit_business_validation`ほか。下記record-unit: domain/current計14 FAIL→14 PASS | 空記録者を許す変異で4 FAIL |
| 現在値・履歴 | `services/item_current_values.py:6`。未取消訂正を(recorded_at,id)昇順で適用。全履歴を保持しitems/*_rawを変更しない。状態だけの訂正は対応値・単位をNoneへ | `test_current_values_use_ordered_active_edits_and_keep_all_history`、`test_undo_restores_original_and_raw_fields_are_never_overwritten`、`test_state_only_removes_value_and_units_then_quantity_pair_restores_numeric`ほか。record-unitのREDに含む | 取消も適用2 FAIL / 同時刻ID順逆転2 FAIL / 状態変更時に値を残す1 FAIL |
| ORM・migration | `models/records.py:33,78,125` / `alembic/versions/human_records.py:11`。3表・複合FK・CHECK・部分UNIQUEを同名で定義。取消者のCHECKはSQLのNULL通過を防ぐIS NOT NULLも含む | `test_item_edit_constraints_in_postgres`、`test_confirmation_unique_excludes_undone_rows`ほか。record-schema: 未作成表で10 FAIL→10 PASS、追加のNULL/語彙/メタデータ一致を含め最終18 PASS。SQLSTATE 23514/23503/23505を実DBで確認 | 型・制約は実DBで直接拒否を検証。下に両DBの実出力 |
| 記録・取消・直列化 | `repositories/record_repository.py:36` / `services/record_service.py:35,101,113,134`。確定版ロック下で追記、old値は直前の有効訂正後、数量2行同一transaction、取消はundone_at/byのみ、サーバ採時。active確認の23505は制約名限定翻訳＋事前チェック | `test_quantity_pair_records_current_old_values_once_in_same_transaction`、`test_unique_translation_is_limited_to_active_confirmation_constraint`、`test_version_lock_serializes_current_old_value_across_sessions`ほか。record-write: 8 FAIL→8 PASS、版ロック追加後9 PASS | 数量単位行を落とす1 FAIL / 全23505を同コードへ丸める1 FAIL / 版ロック除去1 FAIL |
| 参照・集計 | `repositories/record_repository.py:131,156,188,203` / `services/record_service.py:142,154`。現在値＋取消含む履歴、最新判断、根拠、件数の材料を提供。未確定版はE_NOT_FOUND | `test_summary_sets_current_values_history_latest_judgements_and_evidence`と未確定版4件。record-read: 5 FAIL→5 PASS。照合・訂正・未解決・質問対象・TBA・択一はID集合で一致検査 | judgedを解決済み扱い1 FAIL / 同時刻の古い判断採用1 FAIL / 未確定版を許可4 FAIL |
| carry-over既存追従 | `repositories/run_repository.py:37` / `tests/integration/test_runs.py:180` / `tests/fixtures/record_data.py`。仮テーブルCREATEから実ORM行INSERTへ。未取消訂正/確認と判断の存在検査は維持 | `test_carryover_checks_real_schema_and_does_not_copy`。record-carryover: 4 FAIL→4 PASS（作業中の絞込は23 deselected。最終全体ゲートは除外なし） | 関数名とassert 3→3を保持。下記差分証跡 |

## 検証入口・RED/GREEN証跡

```sh
cp docs/test-results/record-checks-2026-09-13.mk /tmp/record-checks.mk
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-unit
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-schema
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-write
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-read
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-carryover
```

これらは作業中の対象テスト入口。完了判定は下記の全体ゲート。

| 対象 | RED | GREEN |
|---|---|---|
| 入力・現在値 | [14 FAIL](test-results/record-domain-red-2026-09-13.log) | [14 PASS](test-results/record-domain-green-2026-09-13.log) |
| DB制約 | [10 FAIL](test-results/record-schema-red-2026-09-13.log) | [初期10 PASS](test-results/record-schema-green-2026-09-13.log)、[追加後18 PASS](test-results/record-boundaries-green-2026-09-13.log) |
| Repository/Service書込 | [8 FAIL](test-results/record-write-red-2026-09-13.log) | [最終9 PASS](test-results/record-write-green-2026-09-13.log) |
| 参照・集計 | [5 FAIL](test-results/record-read-red-2026-09-13.log) | [5 PASS](test-results/record-read-green-2026-09-13.log) |
| carry-over | [4 FAIL](test-results/record-carryover-red-2026-09-13.log) | [4 PASS](test-results/record-carryover-green-2026-09-13.log) |

`record-boundaries-green.log`は制約18 PASSの後に、テスト側がrollback後のORM IDを読んだMissingGreenlet 1 FAIL / 8 PASSを含む。rollback前にIDを保存するようテストを修正し、record-write-greenで9 PASSを確認した。assertを削って通していない。

### 変異検証 10/10

```sh
cp docs/test-results/record-mutation-2026-09-13.txt /tmp/record-mutation.py
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-mutations
```

[実出力](test-results/record-mutations-2026-09-13.log)。子プロセス内のT-301モジュールのみ変異し、共有ソース・実DBのDDLは変更しない。版ロック検証は実PostgreSQLの2セッションで`pg_blocking_pids`を確認し、解放後のold_value=L80を確認している。

### 既存テスト変更の理由・振る舞い保全

実表導入により旧テストのCREATE TABLEがDuplicateTableで衝突したため、承認済み§0⑨に従いORMへ移行した。モデルの外部キーを満たすItemも同版へ作成し、記録ビルダは共有fixtureへ配置した。

[carry-overテストと_has_recordsの差分](test-results/record-carryover-2026-09-13.diff)を保存。関数名`test_carryover_checks_real_schema_and_does_not_copy`は同一、4パラメータケースを保持、assert数は**3→3**。既存関数名も全件保持。原テストの「未取消訂正/確認/判断があれば注意を要求」「取消訂正だけなら要求しない」「旧記録を新しい版へコピーしない」の検査を保持した。T-205 L-4のturnsテスト追加、L-6のMAX_TURNS追従は別変更として保全。

## T-302へ渡す契約

- `RecordService.edit(version_id, data)`は記録行の配列を返す（数量はvalue/unitの2行）。`undo_edit` / `confirm` / `undo_confirmation` / `judge`を提供。
- 取消入力は`recorded_by`必須。`recorded_at` / `undone_at`をDTO入力に追加しない。版外訂正はE_NOT_FOUND、版外の一致確認はE_TARGET_INVALID。未確定版はE_NOT_FOUND。
- `list_items_with_edits`は`CurrentItem(values, history)`の配列。historyは取消済みも含む。`list_questions_with_latest`は`{question, latest}`の配列（最新判断なしはNone）。`list_item_evidence`は対象行の根拠配列。
- `summary`はitem_ids / matched_item_ids / edited_item_ids / question_item_ids / tba_item_ids / unresolved_question_ids、choice_groupsと対応する件数を提供。`edit_count`は未取消訂正の**記録行数**、`edited_item_count`は訂正のある**明細の種類数**。DTOの表示用件数は05-api-ipoに従って選ぶ。coverage_confirmedも提供。
- `review_checked`からの状態イベントは実装しない（指示書§0⑤・T-501）。AGENTの13ツールへ人の記録を追加していない。

## 全体ゲート

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

[実出力](test-results/record-regression-2026-09-13.log):

```text
518 passed, 124 warnings in 32.92s
Test Suites: 15 passed, 15 total
Tests:       166 passed, 166 total
Time:        7.414 s
✅ check: all green
```

除外なし。両DB migration・実索引確認・ruff・OpenAPI/orval・型検査・lintもPASS。API契約/FE成果物の機能変更はなし。T-205の実モデル評価はClaude担当。

## migrationと両DBの実スキーマ

着手時に既存単一headを確認し、新規`human_records`を`add_run_step_locator_index`の後へ追加。[初回make migrate実出力](test-results/record-migrate-2026-09-13.log)に両DBのupgradeを保存。適用済みリビジョンは未編集。最終make checkでも両DBのhead適用と索引を確認。

```sh
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/record-checks.mk record-describe
```

以下は両DBの`psql -X`で`SELECT current_database()`と`\d item_edits` / `\d confirmations` / `\d question_judgements`を実行した出力（行末の空白だけ除去）。[出力ファイル](test-results/record-schema-describe-2026-09-13.log)。

```text
 current_database
------------------
 octg_db
(1 row)

                                       Table "public.item_edits"
   Column    |           Type           | Collation | Nullable |                Default
-------------+--------------------------+-----------+----------+----------------------------------------
 id          | bigint                   |           | not null | nextval('item_edits_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 undone_at   | timestamp with time zone |           |          |
 undone_by   | text                     |           |          |
 version_id  | bigint                   |           | not null |
 item_id     | bigint                   |           | not null |
 field       | text                     |           | not null |
 old_value   | text                     |           |          |
 old_state   | text                     |           |          |
 new_value   | text                     |           |          |
 new_state   | text                     |           |          |
 reason      | text                     |           | not null |
Indexes:
    "item_edits_pkey" PRIMARY KEY, btree (id)
    "ix_item_edits_item_id" btree (item_id)
    "ix_item_edits_version_id" btree (version_id)
Check constraints:
    "ck_item_edits_field" CHECK (field = ANY (ARRAY['kind'::text, 'usage_note'::text, 'od_value'::text, 'od_unit'::text, 'wall_value'::text, 'wall_unit'::text, 'weight_value'::text, 'weight_unit'::text, 'grade'::text, 'connection'::text, 'range_class'::text, 'length_value'::text, 'length_unit'::text, 'qty_value'::text, 'qty_unit'::text, 'note'::text]))
    "ck_item_edits_reason" CHECK (TRIM(BOTH FROM reason) <> ''::text)
    "ck_item_edits_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_item_edits_state" CHECK (new_state = ANY (ARRAY['stated'::text, 'tba'::text, 'not_stated'::text, 'not_applicable'::text, 'numeric'::text]))
    "ck_item_edits_undo_recorder" CHECK (undone_at IS NULL OR undone_by IS NOT NULL AND TRIM(BOTH FROM undone_by) <> ''::text)
    "ck_item_edits_value_or_state" CHECK (new_value IS NOT NULL OR new_state IS NOT NULL)
Foreign-key constraints:
    "fk_item_edits_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_item_edits_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_item_edits_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.confirmations"
   Column    |           Type           | Collation | Nullable |                  Default
-------------+--------------------------+-----------+----------+-------------------------------------------
 id          | bigint                   |           | not null | nextval('confirmations_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 undone_at   | timestamp with time zone |           |          |
 undone_by   | text                     |           |          |
 version_id  | bigint                   |           | not null |
 item_id     | bigint                   |           |          |
 kind        | text                     |           | not null |
Indexes:
    "confirmations_pkey" PRIMARY KEY, btree (id)
    "ix_confirmations_item_id" btree (item_id)
    "ix_confirmations_version_id" btree (version_id)
    "uq_confirmations_coverage_active" UNIQUE, btree (version_id) WHERE kind = 'coverage'::text AND undone_at IS NULL
    "uq_confirmations_row_match_active" UNIQUE, btree (version_id, item_id) WHERE kind = 'row_match'::text AND undone_at IS NULL
Check constraints:
    "ck_confirmations_kind" CHECK (kind = ANY (ARRAY['row_match'::text, 'coverage'::text]))
    "ck_confirmations_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_confirmations_target" CHECK (kind = 'row_match'::text AND item_id IS NOT NULL OR kind = 'coverage'::text AND item_id IS NULL)
    "ck_confirmations_undo_recorder" CHECK (undone_at IS NULL OR undone_by IS NOT NULL AND TRIM(BOTH FROM undone_by) <> ''::text)
Foreign-key constraints:
    "fk_confirmations_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_confirmations_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_confirmations_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.question_judgements"
   Column    |           Type           | Collation | Nullable |                     Default
-------------+--------------------------+-----------+----------+-------------------------------------------------
 id          | bigint                   |           | not null | nextval('question_judgements_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 question_id | bigint                   |           | not null |
 status      | text                     |           | not null |
 resolution  | text                     |           | not null |
 note        | text                     |           |          |
Indexes:
    "question_judgements_pkey" PRIMARY KEY, btree (id)
    "ix_question_judgements_question_id" btree (question_id)
Check constraints:
    "ck_question_judgements_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_question_judgements_resolution" CHECK (resolution = ANY (ARRAY['unresolved'::text, 'resolved'::text]))
    "ck_question_judgements_status" CHECK (status = ANY (ARRAY['open'::text, 'in_progress'::text, 'judged'::text]))
Foreign-key constraints:
    "fk_question_judgements_question" FOREIGN KEY (question_id) REFERENCES questions(id)

 current_database
------------------
 octg_test
(1 row)

                                       Table "public.item_edits"
   Column    |           Type           | Collation | Nullable |                Default
-------------+--------------------------+-----------+----------+----------------------------------------
 id          | bigint                   |           | not null | nextval('item_edits_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 undone_at   | timestamp with time zone |           |          |
 undone_by   | text                     |           |          |
 version_id  | bigint                   |           | not null |
 item_id     | bigint                   |           | not null |
 field       | text                     |           | not null |
 old_value   | text                     |           |          |
 old_state   | text                     |           |          |
 new_value   | text                     |           |          |
 new_state   | text                     |           |          |
 reason      | text                     |           | not null |
Indexes:
    "item_edits_pkey" PRIMARY KEY, btree (id)
    "ix_item_edits_item_id" btree (item_id)
    "ix_item_edits_version_id" btree (version_id)
Check constraints:
    "ck_item_edits_field" CHECK (field = ANY (ARRAY['kind'::text, 'usage_note'::text, 'od_value'::text, 'od_unit'::text, 'wall_value'::text, 'wall_unit'::text, 'weight_value'::text, 'weight_unit'::text, 'grade'::text, 'connection'::text, 'range_class'::text, 'length_value'::text, 'length_unit'::text, 'qty_value'::text, 'qty_unit'::text, 'note'::text]))
    "ck_item_edits_reason" CHECK (TRIM(BOTH FROM reason) <> ''::text)
    "ck_item_edits_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_item_edits_state" CHECK (new_state = ANY (ARRAY['stated'::text, 'tba'::text, 'not_stated'::text, 'not_applicable'::text, 'numeric'::text]))
    "ck_item_edits_undo_recorder" CHECK (undone_at IS NULL OR undone_by IS NOT NULL AND TRIM(BOTH FROM undone_by) <> ''::text)
    "ck_item_edits_value_or_state" CHECK (new_value IS NOT NULL OR new_state IS NOT NULL)
Foreign-key constraints:
    "fk_item_edits_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_item_edits_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_item_edits_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.confirmations"
   Column    |           Type           | Collation | Nullable |                  Default
-------------+--------------------------+-----------+----------+-------------------------------------------
 id          | bigint                   |           | not null | nextval('confirmations_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 undone_at   | timestamp with time zone |           |          |
 undone_by   | text                     |           |          |
 version_id  | bigint                   |           | not null |
 item_id     | bigint                   |           |          |
 kind        | text                     |           | not null |
Indexes:
    "confirmations_pkey" PRIMARY KEY, btree (id)
    "ix_confirmations_item_id" btree (item_id)
    "ix_confirmations_version_id" btree (version_id)
    "uq_confirmations_coverage_active" UNIQUE, btree (version_id) WHERE kind = 'coverage'::text AND undone_at IS NULL
    "uq_confirmations_row_match_active" UNIQUE, btree (version_id, item_id) WHERE kind = 'row_match'::text AND undone_at IS NULL
Check constraints:
    "ck_confirmations_kind" CHECK (kind = ANY (ARRAY['row_match'::text, 'coverage'::text]))
    "ck_confirmations_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_confirmations_target" CHECK (kind = 'row_match'::text AND item_id IS NOT NULL OR kind = 'coverage'::text AND item_id IS NULL)
    "ck_confirmations_undo_recorder" CHECK (undone_at IS NULL OR undone_by IS NOT NULL AND TRIM(BOTH FROM undone_by) <> ''::text)
Foreign-key constraints:
    "fk_confirmations_item" FOREIGN KEY (item_id) REFERENCES items(id)
    "fk_confirmations_version" FOREIGN KEY (version_id) REFERENCES versions(id)
    "fk_confirmations_version_item" FOREIGN KEY (version_id, item_id) REFERENCES items(version_id, id)

                                       Table "public.question_judgements"
   Column    |           Type           | Collation | Nullable |                     Default
-------------+--------------------------+-----------+----------+-------------------------------------------------
 id          | bigint                   |           | not null | nextval('question_judgements_id_seq'::regclass)
 created_at  | timestamp with time zone |           | not null | now()
 recorded_by | text                     |           | not null |
 recorded_at | timestamp with time zone |           | not null |
 question_id | bigint                   |           | not null |
 status      | text                     |           | not null |
 resolution  | text                     |           | not null |
 note        | text                     |           |          |
Indexes:
    "question_judgements_pkey" PRIMARY KEY, btree (id)
    "ix_question_judgements_question_id" btree (question_id)
Check constraints:
    "ck_question_judgements_recorder" CHECK (TRIM(BOTH FROM recorded_by) <> ''::text)
    "ck_question_judgements_resolution" CHECK (resolution = ANY (ARRAY['unresolved'::text, 'resolved'::text]))
    "ck_question_judgements_status" CHECK (status = ANY (ARRAY['open'::text, 'in_progress'::text, 'judged'::text]))
Foreign-key constraints:
    "fk_question_judgements_question" FOREIGN KEY (question_id) REFERENCES questions(id)

```

## 中断・再開の履歴

### 一時中断（§7 2026-09-13 01:40・L-3優先）

- 入力・現在値14件: RED 14 FAIL → GREEN 14 PASS。
- ORM3表と新規 `human_records` migrationを追加し、`make migrate` でoctg_db / octg_testの両方へ適用済み。適用済みの旧リビジョンは未編集。
- 実PostgreSQL制約10件: 相手のpytest終了後の再実行でRED 10 FAIL（未作成テーブル）→ GREEN 10 PASS。
- Repository・Serviceの書込8件: RED 8 FAIL → GREEN 8 PASS。ここを安全な区切りとして中断。
- 未完: 読取Repository/Service・件数の集合検査、追加の制約/並行更新確認、既存carry-overのORM移行、両DBのpsql出力、変異検証、全体ゲート。
- 既存 `tests/integration/test_runs.py::test_carryover_checks_real_schema_and_does_not_copy` は、新表導入後に仮テーブルCREATEが衝突して4件REDを確認済み。L-3ゲートではこの4ケースだけを除外し件数を報告する。T-301再開時に同テスト名・assert数を保ってORMへ移行する。
- 開発中のMake入口 `/tmp/record-checks.mk`、証跡 `/tmp/record-{domain,schema,write}-{red,green}.log`、`/tmp/record-carryover-red.log`、`/tmp/record-migrate.log`。既存carry-overの変更前コードとAST集計は `/tmp/record-carryover-before.py` / `.json`。

### 再開後の区切り（§7 02:20・L-4優先で再中断）

- carry-overの4件をORMへ移行しGREEN（同ファイル23件はこの絞込では未実行）。`RunRepository._has_records` もORMへ移行した。
- 読取Repository/Serviceを追加し、RED5件 → GREEN5件。件数の対象ID集合・取消を含む履歴・同時刻の最新判断ID順・根拠・未確定版拒否を検証。
- 制約追加検証を含めschema18件、Service/Repository書込と実PostgreSQL2セッションの版ロック検証を含め9件がGREEN。`record-boundaries-green.log` の一度のテスト側MissingGreenletはrollback前にIDを保存して解消し、`record-write-green.log`で9件PASSを再確認。
- 未完は変異検証、両DBのpsql出力、既存テストのAST比較、除外なしの全体ゲート、最終handoff。中断前の4件の既知REDは解消済み。

作業中の注意: 最初のDB制約RED実行は別セッションの `pytest tests/` と重なり、未作成テーブルによる9 FAILに加えてTRUNCATEのdeadlock 1 ERRORが出た。deadlockは制約REDの根拠に使わず、相手のpytest終了後に再実行する（LN-027）。


04:40版で再開後、未完だった変異検証・両DBの実出力・AST比較・全体ゲート・最終handoffを完了。既存未コミット変更を保全し、`.claude/memory.md`は編集していない。commitはせず、§7更新まで待機する。

再レビュー依頼
