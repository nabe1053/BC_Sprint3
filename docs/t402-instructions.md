# T-402 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-402【API】G4 照合 API #27（UI GET）＋ #19 との同パス整理**（memory §3・依存 T-401 DONE `949d043`）。T-303 O-2 が FE で並行のときは `frontend/src` を触らない（CV-023）。
設計の正: 05-api-ipo.md #27（AD-025 応答形）・#19・0.2〜0.4・6 章・7.1（AD-026 注記追記済み）、04-db §3.3、03-spec SCR-05、`docs/t401-instructions.md` §2、T-401 の実型 `app/domain/inventory_types.py`。

## 0. orchestrator 決定（AD-026・確定）

| # | 事項 | 決定 |
|---|---|---|
| 1 | `coverage` の位置 | **`summary.coverage`**（05・domain と一致）。トップレベルには置かない |
| 2 | 同パス異メソッドの越境 | Starlette は **405**。テストの期待は 405（`/agent/…/inventory` GET・`/ui/…/inventory` POST とも）。405 の本文が共通エラー形でない点は許容し TODO-032（`main.py` ハンドラは共有ファイルなので T-402 範囲外） |
| 3 | `UI_ONLY_SEGMENTS` に `inventory` を入れない | 05 0.3 に理由を追記済み。`route_contract.py` / `test_api_path_separation.py` は**変更禁止**。`(method, path)` 検査は `test_api_path_separation_live.py` に追補 |
| 4 | `position` / `excerpt` の null 可否 | DTO は **`str`**（DB NOT NULL・CV-010）。domain の `str | None` は T-401 側の記録（TODO-031 ⑤） |
| 5 | `Literal` の出所 | **domain から import**（`InventoryStatus` / `Judgement`。内側の層なので合法・CV-015） |
| 6 | tickets T-402 | #27 のみ＋同パス整理（訂正済み） |
| 7 | 資料名の返し方 | #27 は `documentFileName` を返す（一覧系で資料名が主表示なら API が返す。#25 は行単位の補助なので FE 解決）。記録のみ |
| 8 | 05 #27 の並び表記 | `(seq, id)` 順に統一（書き戻し済み） |
| 9 | 着手順序 | T-401 は DONE・commit 済み。着手時に §0 の実型を再確認するだけ |
| 10 | `test_api_path_separation_live.py` の改名（TODO-027 ①） | C-3 に残す。今回は追記のみ |
| 11 | 未確定版のコード | `E_NOT_FOUND`（T-301/302/401 と統一）。`E_VERSION_NOT_FINALIZED` は使わない |

## 1. 範囲と範囲外

**範囲（API 層のみ・読取専用）**: `app/api/ui/schemas/inventory.py`（新規 DTO）/ `app/api/ui/endpoints/inventory.py`（新規。`GET /versions/{versionId}/inventory`。`route_class=DraftRoute, responses=ERROR_RESPONSES`、`Id = Annotated[int, Path(gt=0)]`）/ `app/api/dependencies.py` に `get_inventory_service(session) -> InventoryService(InventoryRepository(session))`（共有・handoff に明記）/ `app/api/ui/router.py` に include（共有・明記）/ `tests/unit/test_api_path_separation_live.py` への追補 / 統合ポイント。
**範囲外**: UI（T-403）、T-401 の Service/Repository/domain 変更、AGENT 側 #19、`errors.py`（新コードなし）、`route_contract.py`・`test_api_path_separation.py`・`app/agent/**`・migration・`main.py`・`frontend/src`。

## 2. DTO（`CamelModel`・CV-010/011/012。クラス名は既存 `InventoryRequest` / `InventoryBatchRequest` / `InventoryCreated` / `EntryCreated` / `RowMatchResponse` と衝突させない）

| クラス | フィールド |
|---|---|
| `LinkedItemResponse` | `item_id: int, row_code: str` |
| `SourceEntryResponse` | `entry_id: int, document_id: int, position: str, source_no: str \| None` |
| `InventoryEntryResponse` | `entry_id, document_id, document_file_name: str \| None, position: str, source_no: str \| None, seq: int(ge=1), excerpt: str, status: InventoryStatus, status_detail: str \| None, basis: str \| None, linked_items: list[LinkedItemResponse], link_count: int(ge=0), judgement: Judgement` |
| `InventoryItemResponse` | `item_id, row_code: str, source_no: str, seq: int(ge=1), group_code: str \| None, candidate_label: str \| None, source_entries: list[SourceEntryResponse], has_source: bool` |
| `InventorySummaryResponse` | `source_entry_count / source_item_count / output_row_count: int(ge=0)`、`split_entry_ids / excluded_entry_ids / unmapped_entry_ids / orphan_item_ids / multi_mapped_item_ids / inconsistent_entry_ids: list[int]`、`coverage: RowMatchResponse \| None` |
| `InventoryResponse` | `summary, entries: list[InventoryEntryResponse], items: list[InventoryItemResponse]` |

- 6 つの `*_ids` は `@field_validator(mode="before")` で `sorted(set(value))`（frozenset の順は不定。DTO 1 箇所・endpoint は薄く・CV-009）。`*Count` の重複フィールドは足さない（件数は FE が `.length`）
- `coverage` は `ui/schemas/versions.py` の `RowMatchResponse` を再利用（複製しない・CV-015）
- `documentFileName` は資料由来の文字列をそのまま返す（エスケープは FE/React）。`versionId` は含めない
- 注記（TODO-031 ④）: `inconsistentEntryIds` は `entries[]` の部分集合とは限らない（Repository 経由では常に部分集合）

## 3. パス分離の追補（`tests/unit/test_api_path_separation_live.py`）

- `expected` に `("GET", "/versions/{versionId}/inventory")` を追加
- 新規 `test_inventory_path_is_method_split_between_agent_and_ui`: `("GET", "/api/v1/agent/versions/{versionId}/inventory") not in paths` ∧ `("POST", "/api/v1/ui/versions/{versionId}/inventory") not in paths` ∧ `("POST", "/api/v1/agent/versions/{versionId}/inventory") in paths`（#19 が消えていない）
- 実 HTTP: `GET /api/v1/agent/versions/1/inventory` → **405**、`POST /api/v1/ui/versions/1/inventory` → **405**、いずれも `service.reconcile.assert_not_awaited()`

## 4. エラー変換

未確定版・存在しない版 → `DraftError("E_NOT_FOUND")` → 404（既存表）。`versionId <= 0` → 422 `E_REQUEST_INVALID`（既存）。新コード・`errors.py` 変更なし。status リテラルを `errors.py` 以外に書かない。

## 5. テスト

- **unit `tests/unit/test_inventory_api.py`**（`test_record_api.py` の型・Service mock。戻り値は `reconcile(*s06(), version_id=1)` に `dataclasses.replace` で資料名/coverage を付与）: ①200・`assert_awaited_once_with(1)`・トップ `{summary, entries, items}` ②`summary` 10 キーちょうど・S06 で `(12,8,11)`・`splitEntryIds==[6,7,8]`・`excludedEntryIds==[9,10,11,12]`・他 4 配列 `[]` ③**昇順**（`frozenset({8,3,5})`→`[3,5,8]`。`sorted` を外す変異で落ちる）④`coverage` null / 非 null（3 キーのみ・tz 付き）⑤`entries[0]` 13 キー・`linkedItems[0]` 2 キー・`items[0]` 8 キー・`sourceEntries[0]` 4 キー ⑥`judgement` 5 語彙が通り語彙外は `ValidationError` ⑦応答 JSON を再帰走査して `_` を含むキーなし ⑧余分属性非露出（`private="hidden"` 混入 → 出ない・`versionId` も出ない）⑨`documentFileName="<b>x</b>.pdf"` がそのまま ⑩`DraftError("E_NOT_FOUND", …, {"versionId":1})` → 404・`{code,message,details}` ⑪`versions/0` → 422 ⑫405 ×2（§3）
- **integration `tests/integration/test_api_inventory.py`（実 HTTP 1 本）**: `seed_inventory(db_session)` → GET 200 → 3 件数 `(12,8,11)`・split/excluded の ID 配列が seed の実 ID と一致・他 4 配列 `[]`・`coverage null`・entries が `(seq,id)` 順・`documentFileName` 集合・items の ID 集合 == seed 11 件 → `RecordService.confirm(coverage)` → 再 GET で `coverage.recordedBy`・`confirmationId` 一致 → `undo_confirmation` → null。未確定版 → 404。別版の seed が混入しない
- 変異 1 行: DTO の `sorted` を外す → ③が落ちる

## 6. 統合ポイント・完了条件

- `make check`（OpenAPI → orval → typecheck 内包）。OpenAPI に `/api/v1/ui/versions/{versionId}/inventory` GET が tag `ui` で 1 件（関数名は `get_inventory` に固定 → orval `getInventoryApiV1UiVersionsVersionIdInventoryGet`）。`/api/v1/agent/versions/{versionId}/inventory` は POST のみのまま
- orval model 138 → 追加（`inventoryResponse` / `inventorySummaryResponse` / `inventoryEntryResponse`（＋status/judgement enum）/ `inventoryItemResponse` / `linkedItemResponse` / `sourceEntryResponse` 見込み）・**消失 0** を `ls | sort` の前後差分で
- 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（基準 BE 598 / FE 261＋O-2 分）。T-303 O-2 の未コミット FE で fe-lint（prettier・CV-026）が赤なら `frontend/` を直さず原因を handoff に（CV-023 ②）。pytest は Claude と同時に走らせない
- `docs/t402-handoff.md`: 触ったファイル（本体 / 共有 `dependencies.py`・`ui/router.py`・`test_api_path_separation_live.py`）→ レビュー対応表 → OpenAPI パス・orval 前後件数と追加名 → 実出力 → 末尾見出し **`## 再レビュー依頼（T-402）`**。commit は Claude。`app/agent/**`・`errors.py`・`route_contract.py`・`frontend/src` に diff なし
