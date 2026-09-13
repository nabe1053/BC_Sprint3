# T-603 handoff — G6 出力ボタン・版の履歴（FE）＋ #22 `elapsedSec` 追補

Status: **DONE**。独立レビュー 3 回目（RV-048）で P1/P2 0・DONE 可。P3 2 件は記録のみ（TODO-046）。指示書は `docs/t603-instructions.md`。
実施者: Claude メインセッション（Codex 停止のため研修者の指示で引き継ぎ）。

## 変更ファイル

- BE: `backend/app/repositories/record_repository.py`（`elapsed_sec` の材料）・`app/api/ui/schemas/versions.py`（`VersionListItem.elapsed_sec`）・`app/api/ui/endpoints/versions.py`（写し 1 行）
- BE tests: `tests/fixtures/approval_data.py` / `tests/unit/test_approval_api.py` / `tests/unit/test_record_api.py` / `tests/integration/test_approval_queries.py`
- FE: `features/versions/{api,model,hooks}.ts`・新規 `components/ExportButton.tsx`・`components/VersionHistory.tsx`（拡張）・`components/ItemListPage.tsx`（見出し右）・`features/agent-runs/components/AgentRunPanel.tsx`（`emphasis` prop）・`shared/i18n/ja.json`
- FE tests: 新規 `__tests__/export-{model,api,hooks,components}.test.*`、既存 `__tests__/components.test.tsx` / `approval-refresh.test.tsx` / `testing/fixtures.ts` に追従

## 決定表の対応（`docs/t603-instructions.md` §0）

| 決定 | 反映 | 確認 |
|---|---|---|
| ① feature 再利用 | `features/versions/` に追加。新 feature なし・`index.ts` 不変 | — |
| ② 起動経路 | `api.ts: createExport()` が生成関数 `createExportApiV1UiVersionsVersionIdExportsPost` を wrap。生成コード無編集 | `export-api.test.ts`（実URL・POST・body なし） |
| ③ ファイル名 | `model.ts: parseExportFileName(headers)` を純粋関数化。`{name, fromHeader}` で既定名への転落を区別 | `export-model.test.ts` 6 ケース |
| ④ 保存の実装 | `ExportButton.tsx` の `saveBlob()`（`createObjectURL` → `<a download>` → `revokeObjectURL`）。`shared/lib` に置かない | `export-components.test.tsx`（click と revoke を assert） |
| ⑤ 二重出力の防止 | `useCreateExport` は `retry:false`。実行中は `disabled` ＋ `aria-busy` ＋「出力中…」 | hooks/components テスト |
| ⑥ 出力履歴（#39） | 版の履歴パネル内の「この版の出力履歴」（表示中の版のみ・1 クエリ）。`integrity` は**ラベル文字**。`storagePath`/`contentHash` は画面に出さない | components テスト |
| ⑦ `elapsedSec` | `#22` に `elapsed_sec: Decimal \| None` を追加。材料は `AgentRun.version_id` の**版数に依らない 1 回の SELECT**（`in_`）。未記録は `null` →「未記録」。注記「AI の待ち時間は人の作業時間に含めません」 | `test_approval_queries.py`（記録済み/未記録）・`test_approval_api.py`（キー集合＋値）・SELECT 数一定テストは既存のまま green |
| ⑧ 版ごとの出力 | 履歴一覧の各行に「版 n を出力」 | components テスト |
| ⑨ 再実行・新版 | `@/features/agent-runs` の `AgentRunPanel` を index 経由で再利用（新しい起動 UI を作らない） | components テスト（panel の存在） |
| ⑩ 位置と階層 | 見出し右・`variant="outlined"`。**primary は T-503 の「担当者確認済みにする」1 つのまま** | 既存 `components.test.tsx` の「primary は 0/1」テストが green |
| ⑪ 未生成時 | 版 0 件で出力ボタン `disabled`、既存 `versions.history.empty` を維持 | components テスト |
| ⑫ 注記 | 出力シート説明 / D01 簡略書式 / 写しの独立 / 未解決件数 / Scope 2「2 版を比較」（無効）＋注記。**全文 `ja.json`**（JSX 直書きなし） | components テスト・design-lint |
| ⑬ `#40` | 未使用（記録のみ） | — |
| ⑭ 3 状態 | 履歴: loading / error（再読込ボタン）/ empty。出力失敗は code 別文言（notFinalized / notFound / failed） | components テスト 6 本 |
| ⑮ デザイン値 | すべて `tokens.ts` 経由 | `node .claude/scripts/design-lint.mjs` → 違反なし |

## 指示書からの逸脱（1 件）

**`AgentRunPanel` に `emphasis?: "primary" \| "secondary"` を追加した**（既定 `primary` で SCR-02 は不変）。
理由: 03-spec が版の履歴パネルに「固定データで再実行・新版」ボタンを求める一方、`AgentRunPanel` の起動ボタンは
`variant="contained"`（primary）であり、そのまま SCR-03 に置くと design-guidelines「primary は 1 画面 1 つ」に反する
（既存テスト `components.test.tsx`「primary は 0/1」が実際に RED になった）。SCR-03 からは `emphasis="secondary"` で置く。
共有コンポーネントの見た目を呼び出し側が選べるようにしただけで、起動ロジック・ガードレール・二重起動防止は不変。

## RED → GREEN の実結果

| 対象 | RED | GREEN |
|---|---|---|
| BE `#22` unit | `test_approval_api.py` 2 failed / 35 passed（`elapsedSec` 欠落） | 43 passed（unit + integration 併走） |
| BE repository integration | `test_approval_queries.py` 1 failed（`KeyError: 'elapsed_sec'`） | 同上 |
| FE model | `export-model.test.ts` 6 failed / 6 | 6 passed |
| FE api | `export-api.test.ts` 4 failed / 4 | 4 passed |
| FE hooks | `export-hooks.test.tsx` 3 failed / 3 | 3 passed |
| FE components | `export-components.test.tsx` 11 failed / 11 | 11 passed |

既存テストの追従（削除・弱化なし・理由つき）:
- `tests/unit/test_record_api.py` / `tests/fixtures/approval_data.py` / `tests/integration/test_approval_queries.py`: 版一覧行に必須キー `elapsed_sec` が増えたことへの追従
- `frontend/.../testing/fixtures.ts` ・`__tests__/components.test.tsx`: `VersionListItem` の必須フィールド追加＋版の履歴が `#39` も読むことへの追従（`useExports`/`useCreateExport` の mock 追加）
- `__tests__/approval-refresh.test.tsx`: `/versions/9/exports` のスタブ追加＋**明示 timeout 30000**。全体並列実行で jest 既定 5000ms を超えて落ちていた（T-602 レビューの P3 指摘と同一事象）

## OpenAPI・orval 差分

`make openapi orval` の正規経路。`VersionListItem` に `elapsedSec: string \| null` が 1 つ増加（**schema の増減なし・既存フィールドの変更/削除なし**）。
Decimal は既存規約どおり**文字列**で出し、丸めない（CLAUDE.md 決定事項2）。生成ファイルの手編集なし。

## 完了条件

`AGENT_MODE=local_dummy DEBUG=false CI=true make check` → **✅ all green（BE 817 passed / FE 441 passed・34 suites）**。
`node .claude/scripts/design-lint.mjs` → 違反なし。

## 転記案（未適用・memory）

- AD 案: `#22` に `elapsedSec`（N06 の根拠）を追加。材料は `AgentRun.version_id` の 1 回の SELECT。Decimal は文字列で丸めない。
- AD 案: 共有 `AgentRunPanel` は `emphasis` で強調度を選べる。「primary は 1 画面 1 つ」を呼び出し側が守るため。
- LN 案: 版一覧の行は「必須キーの集合」をテストで固定しているため、1 フィールド追加で unit/integration/FE fixture の 4 箇所が同時に RED になる。これは契約が効いている証拠で、optional に弱めない。
- LN 案: 画面に読取を 1 本足すと、実 fetch をスタブする結合テストが「Unexpected request」で落ちる。スタブの網羅は画面の読取一覧と対応させる。

## 再レビュー依頼（T-603）

---

## レビュー対応（RV-046・1 回目）

共通: 修正後に `AGENT_MODE=local_dummy DEBUG=false CI=true make check` → **all green（BE 817 / FE 444・34 suites）**、design-lint 違反なし。

| 指摘 | 対応 | 変更 file | 検証 |
|---|---|---|---|
| P2-1 `unresolvedNote` が未使用 | 未解決 > 0 のとき「未解決 n 件を含めて出力します」を版の履歴パネルに表示 | `VersionHistory.tsx` | `export-components.test.tsx`「未解決があれば…併記する」 |
| P2-2 未生成（⑪）が `loadError` に畳まれる | **修正せず記録（TODO-044）**。下記「設計書間の齟齬」参照 | — | — |
| P2-3 既存テストが `ItemListPage` 経由から `VersionHistory` 単体へ弱まった | **事実誤認**。当該テスト（`components.test.tsx`「版履歴部品は空と取得失敗を区別する」）は T-503 で既に単体描画。T-603 の差分は mock 追加とフィクスチャ追従のみ（`git diff` で確認可） | — | — |
| P2-4 二重出力が `isPending` 依存・同一版のボタンが 2 つ | `useCreateExport(versionId)` に版ごとの `mutationKey` を持たせ、`ExportButton` は `useIsMutating` で進行中を**版単位で共有**。さらに `lock` ref で再描画前の連打も遮断 | `hooks.ts`・`ExportButton.tsx` | 既存 hooks/components テスト |
| P2-5 履歴読取の失敗に POST 用文言を流用 | `versions.export.history.loadError` を新設して分離 | `VersionHistory.tsx`・`ja.json` | `export-components.test.tsx`「出力履歴の読取失敗は出力失敗と別の文言」 |
| P2-6 `retry:false` が変異検知できない | 既定 `mutations.retry:3` の QueryClient で検証するよう変更 | `export-hooks.test.tsx` | 同テスト |
| P2-7 見出し右の出力ボタンが画面テストで未固定 | `components.test.tsx` に「見出し内に出力ボタン 1 つ・`.MuiButton-contained` は 1 のまま」を追加 | `components.test.tsx` | 同テスト |
| P2-8 送付可否の併記が無い（03-spec:199） | 「いま出力すると 評価状態「…」・送付可否「…」として書き出されます」を追加 | `VersionHistory.tsx`・`ja.json` | `export-components.test.tsx` |
| P3-1 出力履歴行に列ラベルが無く未使用キーがある | 各値に列ラベルを併記し、`versions.export.history.*` を実際に使用 | `VersionHistory.tsx` | `export-components.test.tsx` |
| P3-2 `versions.history.rerun` が未使用 | キーを削除 | `ja.json` | — |
| P3-3 `api.ts` の不要なキャストと誤コメント | キャストとコメントを削除（生成型は `headers: Headers` を持つ） | `api.ts` | typecheck |
| P3-4 `exportId` が利用先ゼロ | 戻り値から削除 | `api.ts`・`export-api.test.ts` | typecheck |
| P3-5 逸脱の申告漏れ（決定 ⑥） | 下記「指示書からの逸脱」に 2 件目として追記 | 本 handoff | — |
| P3-6 `timeout 30000` は遅さのマスク | 記録のみ（TODO-045）。原因は画面の読取本数増で、T-602 レビューの P3 と同一事象 | — | — |
| P3-7 `integrityLabelKey(integrity: string)` の型が緩い | 記録のみ（TODO-045）。`unknown` フォールバックがあり実害なし | — | — |

### 指示書からの逸脱（2 件）

1. **`AgentRunPanel` に `emphasis` prop を追加**（既述。design-guidelines「primary は 1 画面 1 つ」を満たすため）
2. **決定 ⑥「版ごとに出力履歴を出す」→ 表示中の版のみ**にした。理由: `#39` は版単位の API であり版ごとに出すと N クエリになる。
   03-spec の版一覧の列は「版ごとの**出力ボタン**」であって履歴ではないため、設計書とは矛盾しない（RV-046 P3-5 の指摘どおり申告漏れだったので追記）。

### 設計書間の齟齬（研修者判断へ・TODO-044）

03-spec:237 は「未生成（生成版が無い）: 担当者確認済み・出力ボタンを無効化し、版の履歴に『未生成。…』」を求める。
一方 AD-024 ① で SCR-03 のルートは `/cases/{caseId}/versions/{versionId}` と決まっており、確定版が 1 つも無い状態は
T-503 が既存テスト「G5 版一覧に現在版が無い場合は**取得失敗**として操作を出さない」で**取得失敗に畳む**契約にしている。
両立しないため、T-603 では **T-503 の既存契約を弱めない**ことを優先し、`notGenerated` の判定だけをコードに残して
表示の変更はしていない（RV-046 P2-2 は未対応）。どちらを正とするかは設計判断のため研修者に上げる。

## レビュー対応（RV-047・2 回目）

共通: 修正後に `make check` → **all green（BE 817 / FE 446・35 suites）**、design-lint 違反なし。

| 指摘 | 対応 | 変更 file | 検証 |
|---|---|---|---|
| **P2** 二重出力の防止機構にテストが無い（`../hooks` を丸ごと mock していて実配線が動いていない） | **新規 `__tests__/export-wiring.test.tsx`**。`../hooks` を mock せず `../api` だけ mock し、同一版の `ExportButton` を 2 つ描画 → 片方クリックで**両方が「出力中…」かつ disabled・`api.createExport` は 1 回**。別版は巻き込まれないことも固定 | `export-wiring.test.tsx`（新規） | **変異確認済み**: `hooks.ts` の `mutationKey` を外すと当該テストが FAIL（実行して確認・ファイルは復元） |
| P3-1 `notGenerated` が到達不能な死んだ条件 | コメントに「**現契約ではこの分岐は到達しない**」と明記。テスト名を「disabled prop が渡れば無効になる（未生成の実経路は TODO-044）」に改め、実経路を検査していると誤読させない | `ItemListPage.tsx`・`export-components.test.tsx` | — |
| P3-2 `unresolvedAtExport` が未使用で 2 種類の「未解決」が同文言 | 出力履歴行を「出力時の未解決: n」に変更。テストも一意テキストで固定 | `VersionHistory.tsx`・`export-components.test.tsx` | 同テスト |
| P3-3 版一覧行の作成日時・状態に列ラベルが無い | 「作成日時: …」「状態: …」を併記（既存キーを使用） | `VersionHistory.tsx` | 同テスト |
| P3-4 `revokeObjectURL` の同期実行 | `setTimeout(..., 0)` で遅延解放 | `ExportButton.tsx` | 既存テスト（`waitFor` で最終的な呼出しを確認） |
| P3-5 `elapsed_sec` の SELECT が版ごと 1 行を仮定 | `.order_by(AgentRun.id)` を追加し、重複時は最新が勝つことを決定的にした（一意制約の追加は migration 変更になるため行わない） | `record_repository.py` | BE ゲート green |

## 再レビュー依頼（T-603・3 回目）
