# T-602 作業指示書 — G6 出力 API

対象: T-602（API #38・#39・#40）。依存T-601は独立レビューDONE可、T-503も第3回独立レビューでDONE可。ユーザーの「次のチケットに取り組んでください」により着手。memory編集・commitは禁止を継続する。

設計の正: `docs/requirements/05-api-ipo.md:115,135,234,522,588,689`（3本の経路・FLOW-07・バイナリ契約・履歴・AGENT非公開）、`docs/requirements/04-db.md` §3.5/§3.6/6章、`docs/requirements/02-requirement.md` FUNC-09・N05、`docs/requirements/03-spec.md` SCR-03出力・版履歴、`docs/requirements/06-scenario-test.md` TEST-15/X07/X08、`docs/t601-instructions.md` AD-030・`docs/t601-handoff.md:141` の実契約。

## 0. 決定表（実装前に確定）

下表は既定設計のAPI接続上の具体化で、AD-030を変更しない。memoryへのAD採番・転記はユーザー禁止により行わず、handoffに転記案を残す。

| # | 論点 | 決定 | 状態 |
|---|---|---|---|
| ① | 配置 | `api/ui/endpoints/exports.py`・`api/ui/schemas/exports.py`。既存UI routerへ登録し、`get_export_service` DIを追加 | 確定 |
| ② | #38入力 | 正のversionIdのみ、bodyなし。非空bodyは共通E_REQUEST_INVALID（400）で拒否し、Serviceを呼ばない。クライアント時刻・状態・記録者の入力口を作らない | 確定 |
| ③ | #38出力 | AD-030㉑通り200のxlsx bytes、Content-Disposition attachment filename、X-Export-Id。ExportResult.contentをそのまま返し、再生成・ファイル読直しをしない | 確定 |
| ④ | OpenAPI | 200はxlsx media typeだけ、schema string/format binary。2ヘッダを定義し、共通エラーモデルも維持 | 確定 |
| ⑤ | #39 | `{exports: ExportRecord[]}`。T-601 ExportWithIntegrityの10属性をcamelCaseへ投影。storagePath/contentHashも05 #39の既定通り含む。ORMのその他の列は出さない | 確定 |
| ⑥ | #40 | `{evidences: VersionEvidenceRecord[]}`。既存EvidenceResponseの全11属性にitemId（nullable）・fileNameを追加。案件レベルと全行の根拠をT-601の順序で返す | 確定 |
| ⑦ | 一括根拠の層 | ExportService.list_evidenceを薄い委譲として追加。endpointからRepositoryへ直結しない。既存Repositoryの版限定一括queryを利用し、行ごとの#25呼出しをしない | 確定 |
| ⑧ | 不存在・未確定 | #38不存在404/未確定409。#39/#40は存在する未確定版も読める（T-601実契約）、不存在404。空配列は200 | 確定 |
| ⑨ | error SSOT | E_VERSION_NOT_FINALIZED→409を既存errors.pyの表1箇所に追加。path形式はDraftRouteの422共通形 | 確定 |
| ⑩ | 名前空間 | exportsは既にUI_ONLY_SEGMENTS登録済み。evidenceは#17 AGENT POSTで使用するため追加禁止。代わりにmethod/path集合でUI GET #40、AGENT POST #17と逆経路不在を固定 | 確定 |
| ⑪ | 生成クライアント | OpenAPI/orvalを正規再生成。#38だけoperation overrideでbinaryInstanceを使用し、Blobとstatus/headersを返す。既存JSONのcustomInstanceとエラー処理を共用する | 確定 |
| ⑫ | ブラウザのヘッダ参照 | 既存CORSのexpose_headersへContent-Disposition/X-Export-Idを追加。許可originは変更しない。実HTTP応答で検査 | 確定 |
| ⑬ | 保存と例外 | T-601のロック・初回保全・整合性・後始末を利用。新規migrationなし。未解決・draftでも確定済みなら出力可。未知のI/O障害は成功へ丸めない | 確定 |
| ⑭ | 次FEへの契約 | #38の生成関数で受信するBlob、2ヘッダ、#39の10属性、#40の13属性をhandoffへ実生成名とともに記載。保存UI・履歴パネル・elapsedSecはT-603 | 確定 |

## 1. 範囲と範囲外

範囲: DTO、ExportServiceの読取委譲、DI・3エンドポイント・router・エラー表・CORS、OpenAPI/orval、バイナリ専用mutatorとそのテスト、API単体/実DB統合/パス境界検査。

範囲外: Agent全体、DTO以外の既存出力モデル/Repository/ビルダ/適用済みmigration、設計書、memory、既存T-503 UI、出力ボタン/保存UI/elapsedSec、追加API。既存未commit差分を保全し、テストファイル名にチケット番号を入れない。

## 2. DTO・API契約

- ExportRecord: exportId:int、fileName:str、storagePath:str、contentHash:str、exportedAt:datetime、stateAtExport:VersionState、sendoffAtExport:SendoffState、unresolvedAtExport:非負int、isInitial:bool、integrity:intact/modified/missing。**10属性**（T-601の実dataclassと一致）。
- VersionEvidenceRecord: evidenceId、field、rawValue、adoptedValue、documentId、locator、quote、appliedCondition、conversionNote、changeReason、priorValue、itemId、fileName。**13属性**。既存EvidenceResponseの11属性を継承する。
- #38のoperationIdは通常のFastAPI生成規則を使用し、再生成結果に合わせてorvalのoperation overrideを結線する。リトライなし。
- #39の順序はexportedAt/id昇順、#40は案件レベル→Item.seq→Evidence.id。状態・日時・原値・引用はAPI層で変更しない。

## 3. エラー・語彙

E_NOT_FOUND 404、E_VERSION_NOT_FINALIZED 409、E_REQUEST_INVALID 400（非空body）/422（path形式）。生入力をエラーへ反映しない。成功バイナリとエラーJSONをクライアントで区別し、非2xxは既存ApiErrorを1回だけ送出する。語彙はdomain既存Literalを再利用する。

## 4. 実装順序とRED→GREEN

| 順 | 実装 | REDとテストファイル |
|---|---|---|
| 1 | DTO（型）・Service委譲 | `tests/unit/test_export_service.py`へ根拠一括委譲と例外伝播を追加、RED→GREEN |
| 2 | API・DI・エラー・CORS | `tests/unit/test_export_api.py`へHTTP bytes/ヘッダ/本文なし/DTO全キー/空履歴/根拠nullable/404/409/422/OpenAPI/CORS。`tests/unit/test_api_path_separation_live.py`へ3経路とmethod分離を追加。RED→GREEN |
| 3 | 実DB・実ファイル | `tests/integration/test_api_exports.py`:2案件分離、実DI、xlsxを再読込して5シート・訂正後値・非数式・未解決件数、応答=保存bytes=hash、初回/2回目/履歴、modified/missing、#40案件/行根拠の順序と一定query数、未確定/不存在。RED確認後に結線を完成 |
| 4 | 統合・バイナリ受信 | 正規OpenAPI/orval→`frontend/src/shared/api/__tests__/binary-client.test.ts`で生成関数のPOST bodyなし・Blob同一・ヘッダ・JSON失敗1回・既存JSON/204維持をRED→GREEN。手動生成物編集禁止 |
| 5 | ゲート・変異 | root Makefileの追加一時targetでTDD。status409除去/一括根拠の版限定除去/バイナリ返却除去/CORS露出除去等を隔離コピーで検出。root `make check`を完走 |

## 5. 完了条件

`make check` green、生成前後のschema差分を明示、既存テストを消さず変更理由をhandoffへ記録、保護ハッシュ確認、handoffのレビュー対応/RED→GREEN/実出力/実生成契約/転記案/「再レビュー依頼」。新しい文脈の独立レビュアーがmake checkを1回再現し指摘ゼロになるまで修正する。commit・memory編集はしない。

## 6. 設計書との齟齬

API/DB要件の変更は不要。T-601のDTO・Repositoryと05 #38/#39/#40をそのまま公開する。#39のstoragePathは設計で明記されている保全メタデータとして返すが、ブラウザのパス入力・ファイル読戻しAPIは作らない。⑪⑫は既定バイナリ応答をブラウザへ届けるための統合実装。新ADのmemory転記は禁じられているためhandoff内の未採番案に留める。
