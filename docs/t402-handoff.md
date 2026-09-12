# T-402 handoff

§7 **2026-09-13 12:50版**の「O-2提出後、更新を待たず着手可」に従い、O-2の提出後に着手。`docs/t402-instructions.md` / AD-026 と T-401 の確定済み実型を確認した。希望Status: REVIEWING。**全体 `make check` は BE625 / FE266、全件成功**。commit・memory編集なし。

## 変更ファイル

本体（新規）:

- `backend/app/api/ui/schemas/inventory.py`: 6 DTO、6種類のID配列の整列・重複除去。domain の InventoryStatus / Judgement と既存 RowMatchResponse を再利用。
- `backend/app/api/ui/endpoints/inventory.py`: #27 GET。正整数path、既存 DraftRoute / ERROR_RESPONSES、Service呼出し→DTO変換のみ。
- `backend/tests/unit/test_inventory_api.py`: Service mockのHTTP/DTOテスト25件。
- `backend/tests/integration/test_api_inventory.py`: HTTP→実DI→Service→Repository→PostgreSQLの1件。

共有ファイル（指示書の許可範囲）:

- `backend/app/api/dependencies.py:38`: `get_inventory_service` の組立のみ追加。
- `backend/app/api/ui/router.py:16,24`: inventory import/includeのみ追加。
- `backend/tests/unit/test_api_path_separation_live.py:18,28`: expected GET追加＋同パス異メソッド検査1件追加。既存assertは維持。

本handoff、`docs/test-results/inventory-api-*` の実行出力と再現用補助ファイルも追加した。T-401のdomain/Service/Repository、AGENT #19、migration、main.py、errors.py、route_contract.pyは変更していない。frontend/srcの手編集なし（生成は下記Makeのみ）。[保護対象の前後ハッシュ比較](test-results/inventory-api-boundaries-2026-09-13.log)も変更0。既存未コミットFE・tsbuildinfoを保全した。

## レビュー対応表

| 契約・確認観点 | 実装・テスト | RED → GREEN の実結果 |
|---|---|---|
| #27 読取のみ・委譲・応答形 | endpoint `get_inventory`。unit `test_inventory_s06_http_contract_and_field_whitelists` で200、`assert_awaited_once_with(1)`、トップ3キー、summary10キーを完全一致 | unit初回はDI/schema未実装とGET未登録で **18 FAIL / 1 PASS / 8 ERROR** → 対象2ファイル **27 PASS** |
| S06の件数・ID集合 | summary `(12,8,11)`、split `[6,7,8]`、excluded `[9,10,11,12]`、残り4配列空、coverage nullを完全一致 | HTTP200のbodyで検査。実DBはseedの実IDを期待値に使用 |
| 6つのID配列は昇順・重複なし | DTOのbefore-validator 1箇所 `sorted(set(value))`。6パラメータでfrozenset `{8,3,5}` と重複list `[8,3,8,5]` → `[3,5,8]` | `sorted` を `list` にする1行変異で **7 FAIL / 20 PASS**（6配列＋S06応答）。全6パラメータのassert失敗をドライバでも確認 |
| DTOの公開フィールド・camelCase | entries13キー、linkedItems2、items8、sourceEntries4を完全一致。全階層のキーを再帰走査。全階層にprivate/version_idを混入 | HTTP200でhidden/private/versionIdの非露出。資料名 `<b>x</b>.pdf` はそのまま返す |
| `summary.coverage` / CV-015 | 既存RowMatchResponseを使用。null／3フィールドありの両方、timezoneあり | unitでトップにcoverageなし、3キー完全一致。OpenAPI `$ref` も既存型を指す |
| 語彙・NOT NULL・下限 | domain Literalをimport。judgement全5語彙。position/excerptはstr、seq≥1、linkCount≥0、summary件数≥0 | judgement5種は成功、語彙外・不正status・position/excerpt null・seq0・linkCount負数はValidationError。OpenAPIでposition/excerpt requiredかつstringを確認 |
| 404 / 422 | 既存DraftRouteに委譲、新規エラーコードなし | unit E_NOT_FOUND→404＋code/message/details完全一致。ID0/-1→422 E_REQUEST_INVALID、Service呼出しなし |
| UI/AGENTメソッド分離（AD-026②③） | 実アプリの(method,path)でUI GET追加・AGENT GETなし・UI POSTなし・AGENT POSTあり | unit実HTTPの越境2件はいずれも405、reconcile未呼出し。405本文は既定のまま（TODO-032、今回は変更しない） |
| 実DI/DB・別版非混入・確認/取消 | integrationはget_dbだけoverrideし、正規get_inventory_serviceを通す。S06を2版＋未確定版にseed | 追加RED **1 FAIL（404≠200）** → **1 PASS**。3件数・全ID集合・(seq,id)順・資料名/資料ID・他版除外、coverage記録→表示→取消→null、未確定/不存在版404 |

限定テストは開発中のフィードバック。提出根拠は除外なしの全体ゲート。

## OpenAPI / orval

[OpenAPI確認](test-results/inventory-api-schema-2026-09-13.log): `/api/v1/ui/versions/{versionId}/inventory` は **GETのみ、tag ui**。operationIdは `get_inventory_api_v1_ui_versions__versionId__inventory_get`。AGENT同パスは **POSTのみ**。Orval関数 `getInventoryApiV1UiVersionsVersionIdInventoryGet` の生成を確認。

[モデル前後比較](test-results/inventory-api-models-2026-09-13.log): **138 → 146、追加8、消失0**。

```text
inventoryEntryResponse.ts
inventoryEntryResponseJudgement.ts
inventoryEntryResponseStatus.ts
inventoryItemResponse.ts
inventoryResponse.ts
inventorySummaryResponse.ts
linkedItemResponse.ts
sourceEntryResponse.ts
```

生成物はMakeのopenapi/orvalによる。O-2で追加されたPrettierゲートを含め全体成功。frontendソースや生成APIの手修正なし。

## 実行コマンドと実出力

```sh
# 高速フィードバック（Makefileはリポジトリ直下、追加ターゲットだけ/tmp）
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/inventory-api-checks.mk inventory-api-unit
AGENT_MODE=local_dummy DEBUG=false CI=true make -f Makefile -f /tmp/inventory-api-checks.mk inventory-api-integration
make -f Makefile -f /tmp/inventory-api-checks.mk inventory-api-mutation
# 最終ゲート
AGENT_MODE=local_dummy DEBUG=false CI=true make check
```

pytestの並行実行を避け、各実行の終了を確認して順次実施。全体ゲートのBE終了後、FE検証中にDB未使用の変異検証を実施した。変異ドライバは当初失敗件数を6と仮定していたが、S06応答も検出し実際は7件失敗したため、全6パラメータの失敗を直接検査するよう修正して再実行した（製品コード/テストは弱めていない）。

[全体ゲート出力](test-results/inventory-api-regression-2026-09-13.log):

```text
4 files reformatted, 168 files left unchanged
625 passed, 166 warnings in 42.60s
✅ check-be: backend green
OpenAPI schema exported to: openapi.json
🎉 api - Your OpenAPI spec has been converted into ready to use orval!
All matched files use Prettier code style!
Test Suites: 19 passed, 19 total
Tests:       266 passed, 266 total
Snapshots:   0 total
Time:        18.485 s
Ran all test suites.
✅ check: all green
```

`make check`内の既存migration手順は開発/テスト両DBで成功。新規migrationなし。既存索引チェックも両DB PASS。実モデルは呼んでいない。BEは基準598＋unit26（API25＋分離1）＋integration1＝625。FEはO-2提出時266を維持。

[unit RED](test-results/inventory-api-unit-red-2026-09-13.log) / [integration RED](test-results/inventory-api-integration-red-2026-09-13.log) / [GREEN](test-results/inventory-api-green-2026-09-13.log) / [変異実出力](test-results/inventory-api-mutation-2026-09-13.log) / [変異検出結果](test-results/inventory-api-mutation-result-2026-09-13.log)。補助Makefileと変異ドライバは `test-results/inventory-api-checks-2026-09-13.mk` / `inventory-api-mutation-2026-09-13.txt` に保存（再現時はコマンドに合わせ/tmpへ配置）。

## 再レビュー依頼（T-402）
