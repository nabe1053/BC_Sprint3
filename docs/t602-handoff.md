# T-602 handoff

Status: IMPLEMENTING。ユーザーの「次のチケットに取り組んでください」により、T-503 DONE可の後に着手。memory編集・git add/commit禁止を継続する。

## 変更予定ファイル（着手前）

- backend: 新規 `app/api/ui/{endpoints,schemas}/exports.py`、既存 `app/services/export_service.py`、`app/api/dependencies.py`、`app/api/errors.py`、`app/api/ui/router.py`、`app/main.py`。
- tests: 新規 `tests/unit/test_export_api.py`、`tests/integration/test_api_exports.py`。既存 `test_export_service.py`、`test_api_path_separation_live.py`へ追加。
- frontend: `orval.config.ts`、`src/shared/api/mutator.ts`、新規 `src/shared/api/__tests__/binary-client.test.ts`。OpenAPI/orval生成物は正規再生成のみ。
- docs: `t602-instructions.md`・本handoff・test-resultsの証跡。memory/設計書/適用済みmigration/Agent/T-503 UIは変更しない。

## 前提・実契約

T-601の独立ゲートBE786、T-503の最終独立ゲートBE786/FE407・29 suitesを基準とする。ExportResult(record,content)、ExportWithIntegrityの10属性、版一括根拠の既存EvidenceResponse11属性＋itemId/fileNameを利用する。exportsは既存UI_ONLY_SEGMENTSに含まれ、evidenceはAGENT POSTがあるので単純segment禁止には追加しない。

指示書の決定表を実装前に作成済み。決定・RV/LNのmemory転記は未採番案としてこのhandoffへ記録する。


## 実装と決定表の対応

| 決定 | 実装箇所 | 結果 |
|---|---|---|
| ① | `backend/app/api/ui/endpoints/exports.py:17` / `schemas/exports.py:10` / `api/dependencies.py:34` / `ui/router.py` | UI専用3本を実Serviceへ結線 |
| ② | `endpoints/exports.py:44` | 正のpath ID、非空bodyを共通400で拒否、Service未呼出し |
| ③④ | `endpoints/exports.py:22,44` | 200は保存済みbytes、xlsx media type・2ヘッダ・OpenAPI binary schema |
| ⑤ | `schemas/exports.py:10` / `endpoints/exports.py:59` | 実dataclass10属性のcamelCase投影、順序をServiceから維持 |
| ⑥⑦ | `schemas/exports.py:27` / `endpoints/exports.py:69` / `services/export_service.py:91` | 既存11属性にitemId/fileNameを追加した13属性。Service→Repository一括委譲 |
| ⑧⑨ | `api/errors.py:46` / API単体・統合テスト | 不存在404・未確定出力409・未確定読取200・不正path422の共通形 |
| ⑩ | `tests/unit/test_api_path_separation_live.py` | 必須3経路とUI GET/AGENT POSTのmethod境界。UI_ONLY_SEGMENTS既存exportsは維持、evidence追加なし |
| ⑪ | `frontend/orval.config.ts:18` / `shared/api/mutator.ts:56` | 出力operationだけbinaryInstance。requestInstanceでJSONエラー処理を共用し、成功Blobを返す |
| ⑫ | `backend/app/main.py:34` | 既存許可originを保持して2ヘッダをCORS公開。実HTTPレスポンスで検査 |
| ⑬ | 実DB・実ファイル統合テスト | T-601をそのまま利用。draft/未解決でも出力可、初回・2回目の保全、modified/missingを確認。新規migrationなし |
| ⑭ | 下記「T-603へ渡す契約」 | 実生成名・型・ヘッダ・10/13属性を固定 |

## レビュー対応・RED→GREEN

| 対象 | 変更内容・テスト | REDとGREENの実結果 |
|---|---|---|
| Service | `tests/unit/test_export_service.py` の一括根拠委譲・例外伝播2ケース | `make -f Makefile -f /tmp/export-api-checks.mk export-api-service`: RED 2 failed /8 passed → GREEN 10 passed |
| API/境界 | `tests/unit/test_export_api.py` と `test_api_path_separation_live.py` | `make ... export-api-unit`: RED 21 failed /1 passed（経路未登録）→ GREEN 22 passed。HTTP本文/ヘッダ/全キー/空配列/コードとService引数をassert |
| 実DB | `tests/integration/test_api_exports.py` の実DI・実xlsx・初回保全・版限定根拠・未確定/不存在 | `make ... export-api-integration`: RED 8 failed（未登録404）→ GREEN 8 passed |
| 生成client | `frontend/src/shared/api/__tests__/binary-client.test.ts` | `make ... export-api-client`: RED 1 failed /9 passed（非JSONのdataがundefined）→ GREEN 10 passed。実生成関数・mutator・fetch呼出しを通しBlob同一性/サイズ/2ヘッダ/POST bodyなし/JSON失敗1回をassert |

RED証跡: `docs/test-results/export-api-service-red-2026-09-13.log`、`export-api-unit-red-2026-09-13.log`、`export-api-integration-red-2026-09-13.log`、`export-api-client-red-2026-09-13.log`。最終対象GREENは `export-api-targeted-final-green-2026-09-13.log`（BE40件・FE10件）。最初のAPI実装時にDomainErrorのコンストラクタをコード指定可能と誤認し、非空body2件がE_DOMAIN_ERRORになった。既存のDraftErrorへ修正して共通コードを保持した経過は `export-api-targeted-green-2026-09-13.log` に残す。テスト期待の緩和なし。

既存テストの変更は追加のみ: ExportServiceへ2件、UI必須経路集合に3本とmethod境界1件。既存assertの削除・弱化なし。生成clientテストのBlob型は型アサーションではなく200への絞り込み後に `const received: Blob = result.data` として全体tscでも確認する。

## 実ファイルと境界の検証

- 実DIはget_dbとEXPORT_ROOTだけをテスト用に差し替える。実Service/Repository/ビルダ/Gatewayを経由して2回出力。HTTP bytes == 保存bytes、sha256 == contentHash、X-Export-Id == #39 exportIdを全件assert。
- 実xlsxをopenpyxlで再読込し5シート・訂正後L80・未解決1件・全セル非数式を確認。初回true→2回目false、別保存先、初回ファイルだけ変更→modified、削除→missing（テスト自身のtmp_path内だけを操作）。
- 2案件（2行/12行）それぞれに案件根拠と全行根拠をseed。行根拠を逆順INSERTしても案件→seq順、他案件の固有引用が混入しないことをassert。HTTP #40 のSELECT実測は2回/2回。
- 未確定版は出力409、既存T-601どおり履歴・根拠の読取は200。不明版は3経路ともE_NOT_FOUND 404。
- 実LLM・実業務資料・開発DBの業務データは使用していない。migration追加/編集なし。

## 変異テスト

.env* / storage / traces / cachesを除外した一時コピーで、root Makefileの一時targetを使用。本体コードは変更しない。

| 変異 | 検出 |
|---|---|
| errors.pyからE_VERSION_NOT_FINALIZED→409を除去 | 1 failed /21 passed |
| RepositoryのEvidence.version_id限定を除去 | 1 failed /7 passed（別案件混入） |
| CORSの2ヘッダ公開を除去 | 1 failed /21 passed |
| binaryInstanceのblob返却をundefinedへ | 1 failed /9 passed |

ログ: `docs/test-results/export-api-mutations-2026-09-13.log` と `export-api-mutation-{status,scope,cors,blob}-2026-09-13.log`。

## OpenAPI・orval差分

`make openapi orval fe-type` の正規経路で生成。OpenAPI schemaは84→88（ExportRecord / ExportsResponse / VersionEvidenceRecord / VersionEvidenceResponse の4追加）。既存84 schemaの変更0・削除0。

生成modelファイルは165→172。追加7: exportRecord.ts / exportRecordIntegrity.ts / exportRecordSendoffAtExport.ts / exportRecordStateAtExport.ts / exportsResponse.ts / versionEvidenceRecord.ts / versionEvidenceResponse.ts。削除0。ui.tsとmodel/index.tsは生成により更新。手編集なし。

## T-603へ渡す契約

| API | 実生成関数（`shared/api/generated/ui`） | 成功 |
|---|---|---|
| #38 POST /versions/{versionId}/exports | `createExportApiV1UiVersionsVersionIdExportsPost(versionId)` | `{data: Blob, status:200, headers:Headers}`。body引数なし。Content-DispositionのfilenameとX-Export-IdがCORS越しに参照可 |
| #39 GET同パス | `listExportsApiV1UiVersionsVersionIdExportsGet(versionId)` | `{data:{exports:ExportRecord[]},status:200,headers}` |
| #40 GET /versions/{versionId}/evidence | `listVersionEvidenceApiV1UiVersionsVersionIdEvidenceGet(versionId)` | `{data:{evidences:VersionEvidenceRecord[]},status:200,headers}` |

ExportRecordの10属性: exportId/fileName/storagePath/contentHash/exportedAt/stateAtExport/sendoffAtExport/unresolvedAtExport/isInitial/integrity。VersionEvidenceRecordの13属性: evidenceId/itemId/fileName/field/rawValue/adoptedValue/documentId/locator/quote/appliedCondition/conversionNote/changeReason/priorValue。itemId=nullが案件レベル。nullable出典補足はnullを維持する。

各非2xxは既存ApiErrorでcode/status/detailsを保持し、バイナリ成功とは分離される。FE mutationはT-603でもretry:falseを明示すること（再POSTは別の出力を作る）。本スライスではファイル保存用のa要素/objectURL、出力ボタン、履歴UI、elapsedSec露出を追加していない。

## 転記案（未適用）

決定案: 既存AD-030のバイナリ契約をOpenAPI binary schema＋operation専用mutator＋CORSの2ヘッダ露出で接続する。#40はUI GET・AGENT #17はPOSTであり、パス単語evidence全体を禁止しない。学び案: JSON専用mutatorは非JSON成功本文を捨てるため、Blob型の生成だけではダウンロードできない。実生成関数経由で本文までassertする。

memoryのAD/RV/LNは未採番・未転記。git add/commitなし。希望Statusは独立レビュー後に確定する。


## 正式ゲートの再実行理由

最初の `make check` はBE816件成功後、FEの新規binary-client.test.tsだけがPrettier checkで失敗した（`export-api-check-2026-09-13.log`）。再整形の差分はjest.fn().mockResolvedValueチェーンの改行だけで、assert/値/実装変更なし。`make ... export-api-format fe-lint` で整形・lintを成功確認（`export-api-format-fix-2026-09-13.log`）。正式ゲート全体を再実行する。
