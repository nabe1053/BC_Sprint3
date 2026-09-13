# T-603 作業指示書 — G6 出力ボタン・版の履歴（FE）＋ #22 `elapsedSec` 追補

対象: T-603（G6 最終スライス）。依存 T-602（API #38/#39/#40）は実装完了・独立レビュー済み。
本スライスで **G6 完了＝初版完成**（Phase 2 の最後）。

設計の正:
- `docs/requirements/03-spec.md:165`（SCR-03 目的）・`:168`（Build 対応 ②「『現在の記録を出力』と再実行・生成所要は G6 で追加」）・
  `:178`（現在の記録を出力ボタン）・`:179`（版の履歴パネル）・`:193`〜`:201`（パネルの内容 5 要素）・
  `:215`〜`:217`（操作）・`:237`〜`:244`（エラー・例外 6 ケース）・`:466`〜`:468`（N04/N05/N06）
- `docs/requirements/02-requirement.md:198` FUNC-09 / `:268`（記録前の初期化）/ `:296`（写しの独立）
- `docs/requirements/05-api-ipo.md` #38・#39・#40・#22
- `docs/t602-handoff.md` 末尾「T-603 へ渡す契約」（実生成関数名・Blob・2 ヘッダ・10/13 属性）— **実契約はここが正**
- `docs/requirements/06-scenario-test.md:322` TEST-15・`:111` X07・`:112` X08
- `.claude/rules/design-guidelines.md`（UI ガードレール）・`.claude/rules/clean-architecture.md`（FE 層）

## 0. 決定表（実装前に確定）

| # | 論点 | 決定 | 状態 |
|---|---|---|---|
| ① | feature の置き場 | 新 feature を作らず既存 `frontend/src/features/versions/` に追加する。SCR-03 は `ItemListPage.tsx` が既にこの feature にあり、版の履歴（`VersionHistory.tsx`）も同 feature。`index.ts` の公開は現状のまま増やさない | 確定 |
| ② | 出力の起動経路 | `#38` は T-602 の binary mutator 経由で `{data: Blob, headers}` を返す実生成関数 `createExportApiV1UiVersionsVersionIdExportsPost(versionId)` を `features/versions/api.ts` で wrap する。生成コードは編集しない | 確定 |
| ③ | ファイル名の決定 | `Content-Disposition` の `filename` を**純粋関数** `parseExportFileName(headers)` として `model.ts` に置き、単体テストする。ヘッダが読めない/壊れている場合は `export.xlsx` にフォールバックし、握りつぶさず戻り値で区別できるようにする（`{name, fromHeader: boolean}`） | 確定 |
| ④ | ブラウザ保存の実装 | `URL.createObjectURL(blob)` → 一時 `<a download>` → `click()` → `URL.revokeObjectURL` を `features/versions/components/ExportButton.tsx` 内の小さな関数で行う。`shared/lib/` には置かない（`clean-architecture.md`: shared/lib は副作用なしの純粋関数） | 確定 |
| ⑤ | 二重出力の防止 | `useMutation({retry:false})`。実行中はボタンを `disabled` にし、`aria-busy` と「出力中…」を出す。**再 POST は別の出力レコードを作る**ため自動リトライを一切しない（T-602 handoff の指示） | 確定 |
| ⑥ | 出力履歴（#39）の表示 | 版の履歴パネル内に、版ごとに `exportedAt` / `fileName` / `integrity` / `unresolvedAtExport` / `isInitial` を出す。`integrity`（`intact`/`modified`/`missing`）は**ラベル文字**で表示し、色だけで伝えない（design-guidelines 状態色の規律）。`storagePath` / `contentHash` は画面に出さない（人が使わない内部値） | 確定 |
| ⑦ | `elapsedSec`（N06・生成所要） | **BE 追補**: `#22` の `VersionListItem` に `elapsed_sec: Decimal \| None` を追加する。材料は既存 `AgentRun.elapsed_sec`（`export_repository.py:72` と同じ `AgentRun.version_id` 相関）。`ApprovalService` の版一覧クエリに **SELECT を増やさず** 相関 subquery で足す。未記録は `null` → UI は「未記録」。表示は「生成所要 n 秒」＋「AI の待ち時間は人の作業時間に含めません」の注記（03-spec:197） | 確定 |
| ⑧ | 版ごとの出力 | 履歴一覧の各行に出力ボタン（03-spec:217）。押した版の `versionId` で `#38` を呼ぶ。**表示中の版に限定しない** | 確定 |
| ⑨ | 再実行・新版 | 既存 `features/agent-runs` の `AgentRunPanel` を **`index.ts` 経由で** 版の履歴パネルに再利用する（feature 間の直接 import 禁止を守る）。`AgentRunPanel` は引き継ぎ警告（carryOver）・二重起動防止を既に持つ。**新しい起動 UI を作らない** | 確定 |
| ⑩ | 出力ボタンの位置と階層 | SCR-03 見出し右。**primary は 1 画面 1 つ**（T-503 の「担当者確認済みにする」が primary）なので、出力ボタンは `variant="outlined"` | 確定 |
| ⑪ | 未生成時 | 版が 0 件のとき出力ボタンを `disabled`、履歴パネルは既存 `versions.history.empty`（「未生成。資料投入画面で案を作成してください」）を維持（03-spec:237） | 確定 |
| ⑫ | 注記（文言は i18n） | パネルに ①出力シートの説明（案件情報／Item List／根拠／確認事項／変更・確認記録の 5 シート）②「サンプル用の簡略書式。正式メーカー書式ではありません」（D01）③「.xlsx は書き出した時点の写しです。編集内容はアプリに取り込まれません」（X07）④未解決 > 0 のとき「未解決 n 件を含めて出力します」⑤Scope 2 枠「2 版を比較」（無効ボタン）＋「初版は版を別に保持して人が比較します」。**JSX 直書き禁止・すべて `ja.json`** | 確定 |
| ⑬ | `#40`（版一括根拠） | T-603 では**使わない**。SCR-04 は行単位 `#26` のまま。出力用の一括経路であり画面要件が無い（記録のみ） | 確定 |
| ⑭ | 3 状態 | 履歴パネル: loading（`common.loading`）/ error（原因＋再読込ボタン。既存 `versions.loadError`＋`versions.reload`）/ empty（⑪）。出力の失敗は `ApiError.code` ごとの文言（`E_VERSION_NOT_FINALIZED` / `E_NOT_FOUND` / 既定）を出し、「エラーが発生しました」で終わらせない | 確定 |
| ⑮ | デザイン値 | すべて `shared/theme/tokens.ts` 経由。hex 直書き・インライン style でのデザイン指定なし | 確定 |

> 研修者確認待ち: なし。⑦ の BE 追補は AD-029 ⑭ が「elapsedSec は T-603」と明記済みの予定変更なし。

## 1. 範囲と範囲外

**範囲**
- BE 追補: `app/api/ui/schemas/versions.py`（`VersionListItem.elapsed_sec`）・版一覧の Repository/Service（`elapsed_sec` の材料追加）
- OpenAPI 出力 → orval 再生成 → typecheck
- FE: `features/versions/{api,model,hooks}.ts`、`components/VersionHistory.tsx`（拡張）、新規 `components/ExportButton.tsx`、`ItemListPage.tsx`（見出し右に出力ボタン）、`shared/i18n/ja.json`

**範囲外**
- `#40` の UI 利用（⑬）・版の差分表示（FUNC-09 拡張・Scope 2）・SCR-06 への出力ボタン（03-spec:665 G02 は未対応事項のまま）
- Agent 側・migration・`shared/api/generated/` の手編集・memory 編集

## 2. 契約

`#38` `{data: Blob, status: 200, headers: Headers}`（body 引数なし）/ `#39` `{exports: ExportRecord[]}`（10 属性）/
`#22` `VersionListItem` に `elapsedSec: number | null` が増える（既存 13 キー → 14 キー。既存キーの変更・削除なし）。

## 3. エラー・語彙

`E_VERSION_NOT_FINALIZED`(409) / `E_NOT_FOUND`(404) / それ以外は既定文言。`integrity`: `intact` / `modified` / `missing`。

## 4. 実装順序と RED→GREEN

1. **BE**: `tests/unit/test_approval_service.py`（または版一覧の既存 unit）に `elapsed_sec` 期待を追加 → RED → Repository/Service/Schema を GREEN。
   `tests/integration/test_approval_queries.py` に「run 未記録は None・記録済みは値・SELECT 回数不変」を追加
2. **統合**: `make openapi orval fe-type`（model 増減を handoff に）
3. **FE model**: `features/versions/__tests__/export-model.test.ts` — `parseExportFileName` の正常・欠落・不正・RFC5987 → RED → GREEN
4. **FE api/hooks**: `export-api.test.ts` / `export-hooks.test.tsx` — `#38` が Blob を返す・`#39` が配列・retry なし → RED → GREEN
5. **FE components**: `export-components.test.tsx` — 出力ボタン（有効/無効/出力中/失敗文言）・履歴の 5 列・integrity ラベル・生成所要・注記 5 種・版ごと出力・再実行パネルの存在 → RED → GREEN
6. design-lint とデザイン規約の自己チェック（primary 1 つ・h1 1 つ・3 状態・Never リスト）

## 5. 完了条件

- `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（除外なし）
- `docs/t603-handoff.md` に 決定表の対応 / RED→GREEN の実件数 / OpenAPI・orval 差分 / 変異テスト / 転記案
- handoff 末尾に `## 再レビュー依頼（T-603）`

## 6. 設計書との齟齬（書き戻し）

- `03-spec.md:168` の Build 対応注記に「②の G6 分（出力・再実行・生成所要）は T-603 で実装済み」と追記
- `05-api-ipo.md` #22 の応答に `elapsedSec` を追記（N06 の根拠）
