# T-201 引き継ぎ（2026-09-12）

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
