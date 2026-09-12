# T-401 handoff

§7 **2026-09-13 10:40版**の明示指示に従い、T-303提出後に実装。Status: REVIEWING。**BE598件 / FE261件（19 suites）PASS**。AD-025の10決定に従い、読取専用の照合集計を新規8ファイルで実装した。commit・memory編集なし。

## 変更ファイル（すべて新規）

- `backend/app/domain/inventory_types.py`
- `backend/app/services/inventory_reconciliation.py`
- `backend/app/repositories/inventory_repository.py`
- `backend/app/services/inventory_service.py`
- `backend/tests/fixtures/inventory_data.py`
- `backend/tests/unit/test_inventory_reconciliation.py`
- `backend/tests/unit/test_inventory_service.py`
- `backend/tests/integration/test_inventory_repository.py`
- 本handoffと`docs/test-results/inventory-*`の証跡。

既存BEコード・既存テスト・共有ファイル・agent・draft_validation・API/DTO・UI・migrationを編集していない。`git diff --name-only -- backend`は空（追加8ファイルはuntracked）。T-303のFE差分を保全した。API接続/DTO/DIはT-402の範囲として残している。

## レビュー対応

| 項目 | 変更内容（file:line） | REDテスト名・件数 / 変異 |
|---|---|---|
| AD-025 戻り値契約 | `domain/inventory_types.py:25,42,54,68`。frozen dataclassのEntryView/ItemView/InventorySummary/Reconciliation。statusとjudgementは別Literal。件数に加えて対象IDはfrozensetで保持し、件数はlenで利用可能。coverageはRowMatch | 型定義のみ。以下純粋関数・Serviceの応答をassert |
| ① S06構造 | `services/inventory_reconciliation.py:12`。entry/link/itemを版で絞り、by_entry/by_itemから8→11、分割・除外を導出 | `test_s06_sets_match_eight_to_eleven_three_splits_four_excluded`。原要素12/原明細8/出力11、split={6,7,8}、excluded={9,10,11,12}、残り集合∅を完全一致。原明細数を全要素数へ変える変異で1 FAIL |
| ② 欠落と不整合の分離 | 同。unmapped∧link0だけmissing/unmapped集合。linkありunmappedはinconsistentのみ | `test_unmapped_without_links_is_missing_but_linked_unmapped_is_only_inconsistent`。link0条件を除く変異で1 FAIL |
| ③ 余分 | 同。linkを持たない版内itemをorphan集合、hasSource=false | `test_output_without_link_is_orphan`。orphan集合を空にする変異で1 FAIL |
| ④ 多重対応 | 同。2つ以上のentryからlinkされたitem ID集合 | `test_two_entries_mapped_to_one_item_are_multi_mapped`。しきい値2→3で1 FAIL |
| ⑤ 保存statusの不一致 | 同。mapped∧link≠1、split∧link<2、excluded/unmapped∧link>0をinconsistentへ。保存statusを上書きしない | `test_saved_status_conflicting_with_structure_is_inconsistent`の3ケース。mappedの不一致検査を外す変異で1 FAIL / 2 PASS |
| ⑥ 版外・存在しない参照 | 同。版外itemをitems/linkedItemsへ含めず、参照entryをinconsistentへ。存在しないentryへのlinkも例外を出さない | `test_outside_version_links_are_inconsistent_without_importing_foreign_items`、`test_unknown_entry_link_is_reported_without_fabricating_a_source`。版外検査で不整合集合への追加を外す変異で1 FAIL |
| ⑦ 表示順 | 同。entries/itemsとも(seq,id)昇順。linkの登録順・行IDの文字列から分割を推測しない | `test_reverse_input_is_sorted_by_seq_then_id_on_both_sides`。seq同値も含め逆順入力で検証。entryソートを逆順へ変える変異で1 FAIL |
| ⑧ 空 | 同。空入力は全0・空集合・空tuple | `test_empty_inputs_return_zero_counts_and_empty_sets`。空時Noneへ変える変異で1 FAIL |
| ⑨ S02 | 同。6 mapped・小計/合計/見出しexcluded、欠落∅ | `test_s02_totals_and_headings_are_excluded_not_missing`。excluded集合を空にする変異で1 FAIL |
| Repository読取 | `repositories/inventory_repository.py:13`。version=RecordRepository.versionを借用。版内entries、entryにjoinしたlinks＋Item.version_id、版内items、資料名、未取消coverageを取得。継承・書込メソッドなし | `test_real_s06_sets_names_and_version_isolation`、`test_unfinalized_inventory_version_is_not_found`、`test_cross_version_link_is_reported_and_foreign_item_is_not_exposed`。実DB2版を作り集合・並び・資料名・未確定404相当code・版外linkを検証 |
| Service・coverage | `services/inventory_service.py:11`。純粋関数の結果へ資料名とRowMatchだけを付与。SQLAlchemy/HTTP/時計なし。unmappedがあっても拒否しない | unit3件: `test_service_delegates_version_and_attaches_document_name_with_null_coverage`、`test_service_preserves_unfinalized_version_not_found`、`test_service_attaches_only_coverage_response_fields`。実DBの`test_coverage_record_and_undo_are_reflected_without_blocking_missing_entries`で登録→応答担当者/サーバー日時→取消→nullを確認 |

純粋関数の初回REDは未実装moduleで1 collection ERROR。Repository/Serviceの初回REDは未実装moduleでunit/integration各1 collection ERROR。実装後は**純粋12＋Service3＝unit15 PASS、実DB4 PASS**。既存テストの変更・削除なし。HTTPは本スライスの範囲外で、実応答契約の検証はT-402で行う。

## 不整合を扱う際の補足

構造的なlinkCount/分割集合は保存linkの数を根拠とするため、status不一致と重なる場合がある。版外linkも件数の根拠には残し、inconsistentを併記するが、版外明細のID/rowCodeをlinkedItems/itemsへ展開しない。純粋関数へ存在しないentryのlinkが渡された場合、そのentry IDをinconsistentに含め、存在しない出典情報は捏造しない。hasSourceは指示どおりlinkの有無であり、この異常系ではtrue・sourceEntriesは空となる。実DBはentryのFKがあり、通常は発生しない。

保存status・表示文言・basisを保持し、行IDの5a/5b等からsplitを推定しない。coverageの記録条件を追加せず、既存T-301 APIの登録/取消を読取に反映するだけ。

## 検証・実出力

```sh
cp docs/test-results/inventory-checks-2026-09-13.mk /tmp/inventory-checks.mk
cp docs/test-results/inventory-mutation-2026-09-13.txt /tmp/inventory-mutation.py
cp docs/test-results/inventory-mutations-2026-09-13.txt /tmp/inventory-mutations.py
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/inventory-checks.mk inventory-unit inventory-integration
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/inventory-checks.mk inventory-mutations
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/inventory-checks.mk inventory-heads check
```

補助Makefileはinventory専用の対象のみを追加し、root Makefileのcheckを変更・除外しない。実行前に他pytestの不在を確認。変異は子プロセス内でのみ置換し、共有ソースは変更しない。9変異すべて対象assertionで1 FAILを確認した（status-mismatchのみ他2 PASSも含む）。

```text
human_records (head)
598 passed, 166 warnings
✅ check-be: backend green
Test Suites: 19 passed, 19 total
Tests:       261 passed, 261 total
Time:        10.792 s
✅ check: all green
```

[純粋RED](test-results/inventory-reconciliation-red-2026-09-13.log) / [読取RED](test-results/inventory-read-red-2026-09-13.log) / [対象GREEN](test-results/inventory-green-2026-09-13.log) / [変異9種](test-results/inventory-mutations-2026-09-13.log) / [全体ゲート・head](test-results/inventory-regression-2026-09-13.log)。全体ゲートはruff・BE全件・OpenAPI/orval・tsc・eslint・FE全件を含み、除外なし。新規migrationはなく、headはhuman_records単一。

## 再レビュー依頼（T-401）

読取専用の照合集計を提出します。BE598件・FE261件、指定9観点の変異がすべて検証できました。commitはしていません。T-402の具体指示は§7の更新を待ちます。
