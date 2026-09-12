# T-401 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-401【BE】G4 インベントリ・対応関係・照合集計**（memory §3・依存 T-201 DONE。T-303 が並行の場合 `frontend/` は触らない）。
設計の正: 04-db.md §3.3 `source_inventory_entries`/`inventory_links`（:650-681）・§3.6、05-api-ipo.md #27（AD-025 の応答形を書き戻し済み）・FLOW-04、03-spec.md SCR-05（:300-361）、02 FUNC-03（受入基準「原項番で対応付け」）・FUNC-06・FUNC-08、06 TEST-11・S06「8→11／除外4／対応なし0」。

## 0. orchestrator 決定（AD-025・確定）

| # | 事項 | 決定 |
|---|---|---|
| ① | 対応要件 | FUNC-03 / FUNC-06 / FUNC-08（「FUNC-05 網羅性照合」は誤記。02 の FUNC-05 は表記整理） |
| ② | unmapped>0 の扱い | **何も拒否しない**。SCR-05 注記「対応なし 0 件は網羅性の保証ではない」が正。coverage 記録の条件は確認者名のみ（T-301 済）。表示順・強調は UI |
| ③ | 集計の根拠 | **構造定義（04-db:681）**で出す: 分割＝1 entry に link≥2、欠落＝unmapped∧link0、余分＝link なし item。保存 `status` と構造の不一致は `inconsistent` に別出し。実モデルの status 使い方（脚注を split・注記を unmapped）の是正はプロンプト側 → TODO-028（T-401 範囲外） |
| ④ | 原明細数 | `status ≠ 'excluded'` の entry 数。総要素数は別項目 |
| ⑤ | #27 応答形 | 05 #27 に書き戻し済み（本書 §2 が詳細） |
| ⑥ | `inventory_links` に版・複合 FK が無い | **migration は作らない**。Repository が `Item.version_id` で join し、版外 link は `inconsistent` に数える（二重防御）。複合 FK 追加は TODO-029（設計判断） |
| ⑦ | 網羅性確認の記録の表示 | #27 応答に `coverage: {confirmationId, recordedBy, recordedAt} \| null`（`RecordRepository.active_confirmation` を借用） |
| ⑧ | tickets.md の範囲 | 保存は T-201・記録は T-301 で済み。T-401 は**照合集計のみ**（tickets 訂正済み） |
| ⑨ | 並び順 | BE は `(seq, id)` 順。unmapped 先頭表示は UI |
| ⑩ | 多重対応 | `multiMappedItemIds` を集計に含める |

## 1. 範囲と範囲外

**範囲（BE のみ・読取専用）**: 版の `source_inventory_entries`＋`inventory_links`＋`items`（＋`documents.file_name`・未取消 coverage）を読み、純粋関数で資料側表・明細側表・集計を導出する Repository / Service。未確定版は `E_NOT_FOUND`（`RecordRepository.version` を借用）。
**範囲外**: API endpoint / DTO / OpenAPI（T-402。#19 は AGENT 側で実装済み）、UI（T-403）、coverage の記録・取消（T-301 #31/#32）、`app/agent/`、版状態遷移（T-501）、**migration なし**、`draft_validation.py` 不変、共有ファイル（`main.py` / `errors.py` / `models/__init__.py` / `dependencies.py` / `alembic/`）不変。DI は T-402 で追加。

## 2. Service の戻り値契約（DTO は T-402）

**summary**: `sourceEntryCount` / `sourceItemCount`（status≠excluded）/ `outputRowCount` / `splitEntryIds`（link≥2）/ `excludedEntryIds` / `unmappedEntryIds`（unmapped∧link0）/ `orphanItemIds`（link なし item）/ `multiMappedItemIds`（2 entry 以上から link）/ `inconsistentEntryIds`（mapped∧link≠1・split∧link<2・excluded|unmapped∧link>0・版外 item への link）/ `coverage`。**ID 集合を持ち件数は len()**（RV-017 P3）。
**entries[]**（`(seq,id)` 順）: `entryId, documentId, documentFileName, position, sourceNo, seq, excerpt, status（保存値・4 値 Literal）, statusDetail, basis, linkedItems:[{itemId,rowCode}], linkCount, judgement: mapped|split|excluded|missing|inconsistent`。
**items[]**（`(seq,id)` 順）: `itemId, rowCode, sourceNo, seq, groupCode, candidateLabel, sourceEntries:[{entryId,documentId,position,sourceNo}], hasSource`。出典の有無は **link の有無**（値の出典は SCR-04）。`apply_edits` 不要（対象列は編集不可）。

## 3. 純粋関数 `reconcile(entries, links, items, *, version_id) -> Reconciliation`（`app/services/inventory_reconciliation.py`）

- duck-typing（ORM / SimpleNamespace）。SQLAlchemy・datetime・HTTP を import しない。`Reconciliation` / `EntryView` / `ItemView` / `InventorySummary` は `app/domain/inventory_types.py` の frozen dataclass、`Judgement = Literal[...]`
- `by_entry` / `by_item` を links から作る → entry ごとの `judgement` → item の `hasSource` → 集合。版外 link・存在しない entry への link は例外にせず `inconsistent`（読取で 500 を出さない）
- RED（`tests/unit/test_inventory_reconciliation.py`・各 1 変異で落ちる）: ①S06 形（mapped 5・split 3×2・excluded 4・11 items → 8/11/split 3/除外 4/unmapped ∅/orphan ∅ を**集合一致**）②unmapped∧link0 → unmapped、unmapped∧link1 → inconsistent のみ ③link なし item → orphan ④2 entry → 同一 item → multiMapped ⑤mapped∧link0 / split∧link1 / excluded∧link1 → inconsistent ⑥版外 item link → inconsistent・items 集合不変 ⑦seq 逆順入力でも `(seq,id)` 昇順 ⑧空入力で全 0・例外なし ⑨S02 形（6 mapped・小計/合計/見出し excluded・unmapped ∅）

## 4. Repository / Service

- `app/repositories/inventory_repository.py`（新規・読取専用）: `version = RecordRepository.version`（借用・継承しない・CV-015）。`load(version_id) -> (entries, links, items, documents, coverage)`。書込メソッドなし。
- `app/services/inventory_service.py`（新規）: `InventoryService(repository).reconcile(version_id)`。ORM を触らない（CV-005）。coverage は `RowMatch` 型（`record_types.py`）で付与。
- RED: unit（Repository mock。未確定版 `E_NOT_FOUND` 透過・coverage null・version_id が渡る）/ integration（実 DB `db_session`。`seed_record_version`＋`Document`＋entries/links 直接 INSERT → S06 形の集合一致・別版が混ざらない・未確定版 `E_NOT_FOUND`・`documentFileName`・coverage 記録→非 null / undo→null）。共有ビルダは `tests/fixtures/inventory_data.py`（CV-021）。

## 5. 実装順序・完了条件

1. `domain/inventory_types.py` → 2. `services/inventory_reconciliation.py`（RED 9 本）→ 3. `tests/fixtures/inventory_data.py` → 4. `repositories/inventory_repository.py`（integration）→ 5. `services/inventory_service.py`（unit）。
- 新規ファイルのみ（CV-017）。既存テスト・共有ファイルに変更が出たら理由を handoff に。`UI_ONLY_SEGMENTS` は触らない（`inventory` は #19 AGENT POST と #27 UI GET が同パス。T-402 が両 router 登録で解く）
- 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（除外なし）/ `alembic heads` が `human_records` 単一のまま / `docs/t401-handoff.md`（触ったファイル → レビュー対応表（項目 / file:line / RED テスト名・件数 / 変異 1 行）→ 実出力）→ 末尾見出し **`## 再レビュー依頼（T-401）`**。commit は Claude。pytest は Claude と同時に走らせない（CV-023）
