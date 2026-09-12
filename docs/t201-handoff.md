# T-201 引き継ぎ（2026-09-12）

## 最新：レビュー対応（RV-021、2026-09-12）

CODEX-INSTRUCTIONS §7のタスクBをT-203修正と同サイクルで実施した。**check-beに実索引検査を組み込み、pytestの前に両DBのスキーマを検査する。最終BE全体404件PASS、両DBの索引検査PASS。**

| 指摘番号 | 変更ファイル:行 | REDを確認した検査・コマンド・件数 | 変異内容1行／強度確認 |
|---|---|---|---|
| RV-021 P2（DONE条件） | Makefile:35、backend/tests/unit/test_regression_gate.py:6 | `DEBUG=false make agent-test`で **1 failed, 77 passed**。検査を失敗させたのに旧check-beがPYTEST_MUST_NOT_RUNとgreenを出すことを実測。組込み後は失敗時にpytestへ進まない | check-run-step-index依存を外すと同テストが落ちる。実DBの索引を削除せず、一時Makefileの検査レシピだけexit 17に置換 |
| P3-4 | MakefileのDB_CONTAINER/DB_USER/DEV_DATABASEとINDEX_*変数、backend/scripts/check_t201_postgres.py:20、tests/unit/test_live_index_check_configuration.py:7 | 設定注入テスト追加時 **2 failed, 77 passed**（P2＋P3-4）。旧コードがoctg_db/octg_testへ接続することを検出。修正後、注入したcontainer/user/dev/testへ向く | 接続先を旧直書きへ戻すと渡されたcommandの完全な接続先assertが落ちる。パスワードはpsql引数や出力へ渡さない |
| P3-1 | 変更なし（任意修正を見送り） | add_run_step_locator_indexは両DBへ適用済み。LN-018とユーザーの「適用済みリビジョンを編集しない」を維持 | downgradeをpassにする任意提案は適用済みrevision編集になるため未実施。今回downgradeは実行していない |
| P3-2 / P3-3 / P3-5 | 下記残件に記録 | 指示どおり記録のみ | 任意強化は今回のDONE条件に含めない |

実索引検査は既存の読取専用SQLを使用する。MakefileからDockerコンテナ・ユーザー・開発DB名を渡し、テストDB名は既存TEST_DBのURLから解析する。設定ファイルを読まず、接続URLをログへ出さない。ローカルDocker向けのチェッカーであり、任意のリモートDB接続機構を追加したものではない。

pg_indexesを読む検査はMakefileゲートの中で、pytestより先に実行される。fixtureのcreate_allによる修復後だけを調べる検査にはしていない。別のpytest用索引検査を重複追加する代わりに、「索引検査失敗時にpytestを開始しない」実行テストを追加した。

### 最終差分の実出力

全ログ: [g2-regression-2026-09-12-2.log](test-results/g2-regression-2026-09-12-2.log)。T-203の14ケース評価と変異試験は [t203-handoff.md](t203-handoff.md) 冒頭に記録。

```text
$ DEBUG=false make check-be
── alembic upgrade head (octg_db / 開発)
── alembic upgrade head (octg_test / テスト)
octg_db: PASS
BEGIN
DO
 database | indexdef
 octg_db | CREATE INDEX ix_agent_run_steps_document_locator ON public.agent_run_steps USING btree (document_id, locator)
(1 row)
ROLLBACK
octg_test: PASS
BEGIN
DO
 database | indexdef
 octg_test | CREATE INDEX ix_agent_run_steps_document_locator ON public.agent_run_steps USING btree (document_id, locator)
(1 row)
ROLLBACK
1 file reformatted, 130 files left unchanged
404 passed, 124 warnings in 18.60s
✅ check-be: backend green
exit 0
```

上記の表は列揃え空白のみ縮めた抜粋。適用済みheadからの追加migrationはなく、既存revisionは変更していない。

### 記録のみの残件

- P3-2: t201_artifactsと新リビジョンに同じ索引定義がある。新規DBと既存DBを収束させる履歴としてLN-018を優先し、後から旧revisionを変更しない。
- P3-3: ASC/DESC・opclassまでの検査は未追加。既存の有効/ready/非UNIQUE/非部分/非式/btree/列順の検査を維持。
- P3-5: `--index-only`と既定動作の整理は未実施。既定は実索引＋合成制約検査、--index-onlyは実索引のみという従来動作を維持する。
- memoryは編集しない。G1の未コミット変更を保全し、T-204/C-1/G3へは進まない。

**再レビュー依頼。希望Status: T-201 DONE（RV-021の条件P2を充足。memoryへの反映はClaude担当）。** 再レビュー用の証拠を提出して、ここで停止する。

## 更新：全体回帰の承認後（2026-09-12）

ユーザーの保留解除後、T-203を含むBE全体392件PASS。`DEBUG=false make check-run-step-index`もoctg_db / octg_test両方PASSし、`ix_agent_run_steps_document_locator`のbtree `(document_id, locator)`を再確認した。適用済みリビジョンや索引実装への変更はない。フルゲートはG1の型検査・Jest失敗で不合格。詳細は `docs/t203-handoff.md` 最新節を参照。下記は前タスクA時点の記録であり、その後のT-203着手と全体回帰はユーザーの明示指示による。

## 最新: §7タスクA / RV-017 残P2対応（2026-09-12）

**再レビュー依頼。希望Status: REVIEWING。** 今回はタスクA（実DBの走査索引欠損）だけを修正した。タスクB・C以降、T-202の修正、T-203には着手していない。以下のRV-016節は過去の履歴であり、索引の適用・回帰結果は本節を優先する。

### レビュー対応

| 指摘番号 | 変更内容（ファイル:行） | REDを確認した検査と実行コマンド・件数 |
|---|---|---|
| RV-017 残P2 / §7タスクA | `backend/alembic/versions/add_run_step_locator_index.py:14`を新設。`down_revision = "t202_run_metadata"`から`op.create_index(..., if_not_exists=True)`で索引を追加。既存索引がある開発DBでも適用できる | `check_live_scan_index` / `make check-run-step-index`: 適用前はoctg_db PASS・octg_test FAIL（実際の欠損を検出）。適用後は両DBの2検査PASS |
| 同・false greenの解消 | `backend/scripts/check_t201_postgres.py:57`に実publicスキーマの読取専用検査。`pg_index`で索引名・表・列順・btree・非UNIQUE・非部分・有効/readyを確認。`Makefile:72`に実行入口を追加 | 同じ検査のRED → GREEN。実DBをDROPする変異は行わず、既存の欠損状態をREDとして使用 |
| 同・既存テストの変更理由 | `backend/tests/t201/test_draft_repository.py:162`を`test_scan_index_exists_in_model`へ改名。実適用を保証しない旧migrationのmock検査を外し、ORMの索引契約だけに限定。実DB検査は上記スクリプトへ移した | `DEBUG=false make check-be`: **356 passed, 124 warnings in 15.78s**。テスト件数の削減・skip/xfail追加なし |

指示書§7には旧リビジョンの追記取消もあるが、今回のユーザー直接指示「適用済みリビジョンは編集せず」を優先し、`t201_artifacts.py`と`t202_run_metadata.py`は変更していない。旧リビジョン内のcreate_indexはそのままなので、新規リビジョンではIF NOT EXISTSを使用する。適用後の実スキーマ検査で、同名索引があるだけではなく期待する定義であることまで確認した。既存索引の削除・再作成やstampは行っていない。

`check_t201_postgres.py`の既存合成スキーマ経路には、旧リビジョンが要求するagent_run_stepsの架空テーブル定義だけを補った。この合成経路は今回実行しておらず、適用完了の根拠にはしていない。

### RED（適用前の実DB）

両DBのalembic_versionは`t202_run_metadata`だった。実行: `make check-run-step-index`（exit 2）。

```text
octg_db: PASS
BEGIN
DO
 database |                                                   indexdef
----------+---------------------------------------------------------------------------------------------------------------
 octg_db  | CREATE INDEX ix_agent_run_steps_document_locator ON public.agent_run_steps USING btree (document_id, locator)
(1 row)

ROLLBACK

octg_test: FAIL
ERROR:  Missing or invalid ix_agent_run_steps_document_locator
CONTEXT:  PL/pgSQL function inline_code_block line 16 at RAISE

make: *** [Makefile:21: check-run-step-index] Error 1
```

### migrationと品質ゲート

最初の`make migrate`は既存プロセス環境の`DEBUG=release`によるPydantic真偽値エラーでDB適用前に失敗した。`.env`や永続設定を変更せず、コマンド環境だけ`DEBUG=false`として再実行した。以下は認証情報を出力しないラッパー経由で実行した`DEBUG=false make migrate`の出力（exit 0）。

```text
── alembic upgrade head (octg_db / 開発)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade t202_run_metadata -> add_run_step_locator_index, Converge existing databases on the document/locator scan index.
── alembic upgrade head (octg_test / テスト)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade t202_run_metadata -> add_run_step_locator_index, Converge existing databases on the document/locator scan index.
```

BEのみの変更に対する規約§1の品質ゲート: `DEBUG=false make check-be`（exit 0）。実出力抜粋（既存のPydantic alias / Starlette非推奨警告の詳細だけ省略）:

```text
 Container octg_postgres Running
── alembic upgrade head (octg_db / 開発)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
── alembic upgrade head (octg_test / テスト)
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
124 files left unchanged
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
....................................................................     [100%]
356 passed, 124 warnings in 15.78s
✅ check-be: backend green
```

全体BE回帰を実行済み。FEを含む`make check`はBEのみのタスクのため実行していない。`make check-run-step-index`の再実行もoctg_db PASS / octg_test PASS。`git diff --check`はPASS。

### 適用後のpsql実出力

実行: `docker exec octg_postgres psql -X -w -v ON_ERROR_STOP=1 -U postgres -d octg_test -c '\d agent_run_steps' -c 'SELECT version_num FROM alembic_version;'`（exit 0、行末空白のみ省略）。

```text
                                         Table "public.agent_run_steps"
     Column     |           Type           | Collation | Nullable |                   Default
----------------+--------------------------+-----------+----------+---------------------------------------------
 agent_run_id   | bigint                   |           | not null |
 parent_step_id | bigint                   |           |          |
 seq            | integer                  |           | not null |
 tool_name      | text                     |           | not null |
 args_digest    | text                     |           | not null |
 args_summary   | text                     |           |          |
 locator        | text                     |           |          |
 document_id    | bigint                   |           |          |
 result_status  | text                     |           | not null |
 duration_ms    | integer                  |           |          |
 id             | bigint                   |           | not null | nextval('agent_run_steps_id_seq'::regclass)
 created_at     | timestamp with time zone |           | not null | now()
 trace_event    | jsonb                    |           |          |
Indexes:
    "agent_run_steps_pkey" PRIMARY KEY, btree (id)
    "ix_agent_run_steps_agent_run_id" btree (agent_run_id)
    "ix_agent_run_steps_document_locator" btree (document_id, locator)
    "uq_agent_run_steps_run_seq" UNIQUE CONSTRAINT, btree (agent_run_id, seq)
Check constraints:
    "ck_agent_run_steps_result_status" CHECK (result_status = ANY (ARRAY['ok'::text, 'error'::text, 'unreadable'::text]))
Foreign-key constraints:
    "agent_run_steps_agent_run_id_fkey" FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id)
    "agent_run_steps_document_id_fkey" FOREIGN KEY (document_id) REFERENCES documents(id)
    "agent_run_steps_parent_step_id_fkey" FOREIGN KEY (parent_step_id) REFERENCES agent_run_steps(id)
Referenced by:
    TABLE "agent_run_steps" CONSTRAINT "agent_run_steps_parent_step_id_fkey" FOREIGN KEY (parent_step_id) REFERENCES agent_run_steps(id)

        version_num
----------------------------
 add_run_step_locator_index
(1 row)
```

実行: `docker exec octg_postgres psql -X -w -v ON_ERROR_STOP=1 -U postgres -d octg_db -c '\d agent_run_steps' -c 'SELECT version_num FROM alembic_version;'`（exit 0、行末空白のみ省略）。

```text
                                         Table "public.agent_run_steps"
     Column     |           Type           | Collation | Nullable |                   Default
----------------+--------------------------+-----------+----------+---------------------------------------------
 agent_run_id   | bigint                   |           | not null |
 parent_step_id | bigint                   |           |          |
 seq            | integer                  |           | not null |
 tool_name      | text                     |           | not null |
 args_digest    | text                     |           | not null |
 args_summary   | text                     |           |          |
 locator        | text                     |           |          |
 document_id    | bigint                   |           |          |
 result_status  | text                     |           | not null |
 duration_ms    | integer                  |           |          |
 id             | bigint                   |           | not null | nextval('agent_run_steps_id_seq'::regclass)
 created_at     | timestamp with time zone |           | not null | now()
 trace_event    | jsonb                    |           |          |
Indexes:
    "agent_run_steps_pkey" PRIMARY KEY, btree (id)
    "ix_agent_run_steps_agent_run_id" btree (agent_run_id)
    "ix_agent_run_steps_document_locator" btree (document_id, locator)
    "uq_agent_run_steps_run_seq" UNIQUE CONSTRAINT, btree (agent_run_id, seq)
Check constraints:
    "ck_agent_run_steps_result_status" CHECK (result_status = ANY (ARRAY['ok'::text, 'error'::text, 'unreadable'::text]))
Foreign-key constraints:
    "agent_run_steps_agent_run_id_fkey" FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id)
    "agent_run_steps_document_id_fkey" FOREIGN KEY (document_id) REFERENCES documents(id)
    "agent_run_steps_parent_step_id_fkey" FOREIGN KEY (parent_step_id) REFERENCES agent_run_steps(id)
Referenced by:
    TABLE "agent_run_steps" CONSTRAINT "agent_run_steps_parent_step_id_fkey" FOREIGN KEY (parent_step_id) REFERENCES agent_run_steps(id)

        version_num
----------------------------
 add_run_step_locator_index
(1 row)
```

### 保全・停止位置

`.claude/memory.md`と適用済み2リビジョンは作業前後のSHA-256一致を確認。G1の既存未コミット変更・未追跡ファイルは保全し、FEファイルは編集していない。今回の変更は新規リビジョン、実スキーマ検査スクリプト、モデル契約テスト、Makefileの検査入口、本handoffの5ファイルのみ。コミット・レビューの代行・タスクB以降への着手は行わない。

**再レビュー依頼。タスクAの作業をここで停止する。**



## 最新: RV-016対応・再レビュー依頼（VS Code引継ぎ後）

**希望Status: REVIEWING（修正済み・再レビュー待ち、全体回帰/実DB検証は保留）。DONEではない。** 下の「現在の状態」「独立レビュー」「検証の再現」は追加レビュー前の履歴であり、最新判定は本節を優先する。今回、独立レビュアーによる確認は未実施。実装者の検証を独立レビューとは扱わず、Claudeメインセッションへ再レビューを依頼する。

### レビュー対応と証拠

| 指摘 | 変更・再現テスト | 実結果 |
|---|---|---|
| P2-1 走査済み・相殺の正常系不足 | `backend/tests/t201/test_draft_repository.py`: `test_successful_read_marks_only_requested_range`（read_document/ok、read_emailのemail:postscript:2）、`test_scoped_issue_excuses_only_matching_range`（受付時issue、当該runのissue）。他範囲は未走査のまま残ることも確認 | 現コードで4件GREEN。メモリ上でscannedのaddを無効化すると2件RED、excusedのaddを無効化すると2件RED。ソースファイルや実DBは変異させない |
| P2-2 明細の明示状態不足 | `backend/tests/t201/test_draft_validation.py`: `test_every_item_explicit_state_requires_own_evidence`。qty/od/wall/weight/grade/connection/length/due/place × tba/not_applicable。欠落項目・itemIdを確認し、該当根拠追加後は違反0件を確認 | 18件GREEN。明示状態の判定をメモリ上で無効化すると18件RED |
| P2-3 版行ロック未検証 | `backend/app/repositories/draft_repository.py:edit`のdocstringと04-dbへSQLiteの限界を明記。`test_edit_refreshes_finalization_from_database`は読込済みidentity mapを古くした状態から確定済み拒否を検証 | 1件GREEN、populate_existing無効化で1件RED。初稿は未ロード属性のため変異を検出できず、明示refresh後に古くする形へ修正。PostgreSQLの2セッション直列化・ロック待機は**未検証**。memoryへの転記はClaude担当 |
| P2-4 走査索引未作成 | `backend/app/models/agent_runs.py`と`backend/alembic/versions/t201_artifacts.py`に`ix_agent_run_steps_document_locator(document_id, locator)`を追加。`test_scan_index_exists_in_model_and_migration`はORM定義とmigrationのcreate_index引数を検証 | 索引追加前RED → GREEN。migrationのコードだけを変更し、適用していない |
| P3 source疑似項目・両端のdetail・不要な防御 | `backend/app/services/draft_validation.py`: 必須kind根拠と重複するsource疑似項目を除去。missing_unitをend_a.od等で返す。snapshot.endsを直接参照 | `test_missing_kind_evidence_does_not_invent_source_field` / `test_end_missing_unit_identifies_od_field`で2件RED → GREEN |
| P3 終了済みrunへの遅延書込 | `test_stopped_run_rejects_draft_write`をT-201側にも追加 | GREEN。E_RUN_NOT_ACTIVE、header未保存を確認 |
| P3 文書・format | 04-dbに空pageの除外、not_statedでは項目別根拠を要求しない判断を追記。draft_repositoryをRuff format | PASS |
| P3 email_parts一意制約 | 既存資料への影響とG1投入処理との調整が必要なため未追加。04-dbへ残件を記録 | 保留。今回のG2からG1スキーマを変更しない |

T-202の共通エラー統合に伴い`draft_errors.py`は新しい`domain/errors.py`のDomainErrorを継承し、`draft_types.py`はPydanticCustomErrorで業務コードを保持する。T-201の入力・Serviceテストも通過している。

### 実行コマンドと最終結果

backendディレクトリで実行。既存root conftest・通常設定を読み込まず、SQLiteメモリDBと架空データのみを使用。

```sh
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t201 tests/t201 -q --tb=short --disable-warnings
# 104 passed in 0.71s
.venv/bin/python -B scripts/check_g2_mutations_isolated.py scanned
# 2 failed / Mutation scanned: DETECTED
.venv/bin/python -B scripts/check_g2_mutations_isolated.py excused
# 2 failed / Mutation excused: DETECTED
.venv/bin/python -B scripts/check_g2_mutations_isolated.py explicit
# 18 failed / Mutation explicit: DETECTED
.venv/bin/python -B scripts/check_g2_mutations_isolated.py refresh
# 1 failed / Mutation refresh: DETECTED
```

変異コマンドのpytest失敗は意図したRED。スクリプトは変異検出時に終了コード0を返す。新規の`backend/scripts/check_g2_mutations_isolated.py`で再現可能。通常のソースはGREENのまま保全する。今回変更したPython25ファイルのRuff check/formatと`git diff --check`もPASS（一覧はT-202 handoff参照）。

### 未実施・保全

全体回帰、実DBへのmigration適用、別テストDB初期化、PostgreSQL検証スクリプトの再実行、独立レビューは未実施。以前の合成スキーマ検証は実スキーマ適用やロック並行性の証明にはならない。`.claude/memory.md`は未編集。G1の画面・依存・設定と既存未コミット成果物を保全。コミット・プッシュ・ファイル削除は行っていない。T-203へは進まない。

## 現在の状態

成果物の保存・版管理・完了条件判定を実装済み。T-201単独の77テスト、変更範囲のlint・format、PostgreSQLの前進マイグレーションと15種類の制約検証が成功。
全体回帰テストは未実行。ユーザーが「全体回帰テストは保留する」と明示したため、既存設定の読み込み・別テストDBの作成や初期化は行わず、進捗はREVIEWING（独立レビュー済・全体回帰保留）にしている。
このタスクがユーザーの「T-101が完了したらT-201から進める」「再開してください」の指示に基づくT-201担当。G1側memoryのTODO-004が指している変更はこのタスクの成果物。

## 独立レビュー

最終レビューで前回のDecimal例外・TBA/両端/案件明示状態の根拠・根拠重複コードの修正が確認され、残存コード指摘なし。reviewerは76件を独立再実行。続くcamelCase対応の差分も別途レビューされ、Serviceテスト9件成功・指摘なし。最終の全77件はメインセッションで実行済み。

## 実装

- `backend/app/domain/draft_types.py`: 原値・明示状態・Decimalの入力契約。未知フィールド、換算用フィールド、合計数量、浮動小数点・非有限数値を拒否。数値変換例外を検証エラーに統一。
- `backend/app/models/drafts.py` / `backend/alembic/versions/t201_artifacts.py`: 案件情報・明細・両端・根拠・確認事項・インベントリ・対応関係の7テーブル。状態と値のCHECK、複合FK、根拠の部分UNIQUEを定義。
- `backend/app/repositories/draft_repository.py`: 案件内の版連番・系譜、保存処理、走査状況の取得。案件・版の混在を拒否し、全書込と確定処理を同じ版行ロックで直列化。確定状態はロック取得時に再取得。
- `backend/app/services/draft_validation.py`: 設計の7種類の違反を検出。TBA・適用なしなどの明示状態、案件情報、両端の径・接続・BOX/PINも項目ごとの根拠を要求。
- `backend/app/services/draft_service.py`: 入力検証と確定。GET相当の検証は読み取りのみ。確定時にロック内で再検証し、明細0件・インベントリ未登録・残存違反を拒否。関連issueがあればis_complete=false。エラーdetailsはG1のCV-011に合わせcamelCase。

## メール走査の契約（TODO-002・TODO-003）

`04-db.md` §3.3「T-201補足」に明記。メールをdocument_pagesに重複保存せず、email_partsを `email:<part_role>:<seq>` で識別する。完全なread_email応答の成功トレースだけ `email:*` で全パーツを覆う。seqは出現順であり新旧判定には使わない。
検索・一覧・別実行のトレースは走査の代替にしない。受付時または当該実行の範囲一致issueだけを相殺する。reference_missingや資料全体のNULL locatorで読取可能な範囲を丸ごと相殺しない。添付一覧の走査は添付内容の読取を意味しない。

## 検証の再現

backendディレクトリで実行する。

```bash
.venv/bin/python -B -m pytest -p no:cacheprovider --confcutdir=tests/t201 tests/t201 -q
.venv/bin/python -B scripts/check_t201_postgres.py
```

前者は既存設定ファイルとルートのconftestを読み込まない独立テスト。Repositoryはメモリ内SQLiteで検証するためPostgreSQLの同時実行そのものは保証しない。
後者は既存のローカルoctg_postgres / octg_test内に独立スキーマを作り、全DDLと架空データを単一トランザクションで検証後ロールバックする。既存テーブルのデータには触れない。PostgreSQLのnumeric精度・CHECK・複合FK・部分UNIQUEを確認済み。
通常の全体回帰テスト、開発DBへのマイグレーション適用、実エージェントの評価は未実施。新しいマイグレーションの親は540727e02dcb。適用は全体回帰テストの実行条件確定後に行う。

## T-202以降への接続

T-201はBEのみ。HTTPエンドポイント・OpenAPI・生成クライアント・UIは追加していない。
T-202では既存のcamelCase専用リクエスト規約とHTTPエラー応答へ接続する。内部のdomain入力型はPython用snake_caseも受け付けるので、HTTPの境界でcamelCase専用DTOを使用する。
T-202/T-203で1実行1版・同一案件と規則版を保持し、上記メールlocator契約で成功トレースを保存する。
コミット・プッシュは行っていない。待機用自動実行 t-101-t-201 はT-201着手時に停止済み。

## 運用指示（2026-09-12 研修者決定）

**memory.md は読むだけ・編集禁止。**修正結果・学び・Status 希望はこの handoff に書く。詳細と修正対象は `docs/reviews/CODEX-INSTRUCTIONS.md` と `docs/reviews/g2-review-2026-09-12.md`。

## 今回の提出状態（RV-021対応後）

冒頭の最新節を優先する。check-beへの実索引検査組込みと両DBの索引検査PASS、BE全体404件PASSを確認済み。

**再レビュー依頼。希望Status: T-201 DONE（RV-021の条件P2を充足）。** 判定・memory更新はClaude担当とし、ここで停止する。
