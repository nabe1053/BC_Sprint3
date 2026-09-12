# T-103 作業指示書（orchestrator → Codex）— 2026-09-12

対象スライス: **T-103【FE】案件一覧（SCR-01）・資料投入（SCR-02）画面**（memory §3 Status=FIXING）
入力: `docs/reviews/g1-review-2026-09-12.md`（RV-019・P1 5 / P2 8 / P3 5 ＋ 未完成 9）
着手前に読むもの: `docs/reviews/CODEX-INSTRUCTIONS.md` / `.claude/rules/design-guidelines.md` /
`.claude/rules/clean-architecture.md`（Frontend 層→dir）/ `docs/requirements/03-spec.md` SCR-01・SCR-02・3章 /
`docs/requirements/mocks/mockup.html` の `#SCR-01` `#SCR-02`

> **着手タイミング**: WIP=1（CODEX-INSTRUCTIONS §2）。T-201 / T-203 のレビュー対応を抱えている間は着手しない。
> この指示書は「手が空いたときに何をどう直すか」を確定させておくためのもの。

---

## 0. 前提（決定済み。蒸し返さない）

| ID | 決定 |
|----|------|
| **AD-013** | SCR-01 の「表示状態」「送付可否」は **T-103 では常に「—」＋注記**。操作は**「投入画面へ」（SCR-02）のみ**。`openButton`（→SCR-03）は G3 で追加 |
| **AD-009** | ルートは `/cases`（SCR-01）と `/cases/{caseId}/intake`（SCR-02）。`src/app/page.tsx` は `/cases` へリダイレクト |
| **AD-008** | SCR-02 は Build では**実 API を使う**。「固定サンプルで案を作成」（＝エージェント起動）は **T-204 の範囲。T-103 では作らない** |
| **AD-005** | 415（未対応形式）は**記録が残る**ので一覧を invalidate する。413（上限超過）は**記録が残らない**ので invalidate しない |
| **AD-003** | 入力上限は仮値（資料50件 / 20MB / PDF 200ページ / xlsx 50シート）。画面に「仮上限。D02 の確定値ではない」と明記する |

骨格（層配置・依存方向・orval wrap・`ApiError` を error 型に据える形）は**正しい。方針転換は不要**。

---

## 1. P1（契約違反・バグ。components 着手前に片付ける）

### P1-1 413 の `details.limit` の値がバックエンド契約と違う

- **現象**: テストが `"fileSizeMb"` を期待している
  （`features/documents/__tests__/hooks.test.tsx:96,117` / `features/documents/components/__tests__/IntakePage.test.tsx:163,173`）
- **正**（`backend/app/services/document_intake_service.py:142-208` で確認済み・05-api-ipo 0.4）:

  | `limit` | `max` の意味 | `actual` の意味 |
  |---------|-------------|----------------|
  | `file_size` | 上限 MB（整数） | 実サイズ MB（小数第2位まで） |
  | `document_count` | 案件あたりの上限件数 | 投入後の件数 |
  | `pdf_pages` | 上限ページ数 | 実ページ数 |
  | `xlsx_sheets` | 上限シート数 | 実シート数 |

- **やること**: **テストの期待値を snake_case の4値に直す**（BE は直さない）。
  キー名を変えたいなら先に `05-api-ipo.md` 6章を直してから BE/FE を合わせる（設計が正）
- **完了確認**: 4値それぞれのケースがテストにあること（1値だけ直して終わりにしない）

### P1-2 `documents.limitExceeded.detail` が内部識別子をそのまま画面に出す

- **現象**: `ja.json` の `"{{limit}}の上限{{max}}に対し{{actual}}でした"` に `file_size` が入ると
  「file_size の上限20に対し25でした」になる。**単位も無い**
- **反する条項**: 03-spec SCR-02「超過内容を具体的に通知」／ X09 ／ AD-003
- **やること**: `documents.limitExceeded.limitLabel.{file_size|document_count|pdf_pages|xlsx_sheets}` を追加し、
  **翻訳済みラベル＋単位**で文面を組み立てる。例:
  - `file_size` →「1ファイルのサイズ」・単位 MB
  - `document_count` →「1案件あたりの資料件数」・単位 件
  - `pdf_pages` →「PDF のページ数」・単位 ページ
  - `xlsx_sheets` →「xlsx のシート数」・単位 シート
- **完了確認**: 画面文言に `file_size` 等の識別子が出ないことをテストで固定する

### P1-3 本番 QueryClient の `mutations: { retry: 1 }` が記録系 POST を自動再送する

- **現象**: `src/app/providers.tsx:146`。`customInstance` は非 2xx をすべて throw するため、
  **415 でも retry が走り `documents` に2行残る**（AD-005 で 415 は記録が残るため）
- **反する条項**: 05-api-ipo 0.2「記録系 POST は毎回新しい行を作る。**UI 側で二重送信を防ぐ**」
- **やること**: 既定を **`mutations: { retry: false }`** にする
- **注意**: テスト側 `shared/testing/test-utils.tsx:19` は既に `retry: false` なので、
  **テストでは検出できない**。`providers.tsx` の既定値そのものを検証するテストを1本足すこと
- T-103 の diff 外だが、**記録系 POST を初めて画面に載せるのが T-103** なのでここで決着させる

### P1-4 SCR-01 の「表示状態・送付可否」— **AD-013 で決定済み**

- T-103 は両列を**常に「—」**とし、**注記「版の状態は G3 以降に表示します」**を添える
- `i18n` のキーを起こし、JSX に直書きしない
- G3（T-302）で #1 を `versions` から拡張する。**T-103 で #1 を拡張しない**

### P1-5 「案件を開く」の遷移先 — **AD-013 で決定済み**

- **「投入画面へ」（`cases.list.intakeLink` → `/cases/{caseId}/intake`）のみ**を出す
- `cases.list.openButton` は **G3 で追加**。今は**キーごと残さない**か、使わない旨をコメントする
  （ラベルと遷移先の不一致・死にキーを残さない）

---

## 2. P2（品質・テスト。P1 と同時に閉じてよい）

| # | 内容 | やること |
|---|------|---------|
| P2-1 | `features/documents/hooks.ts:38-42` に `console.log("[DEBUG] …")` | 削除 |
| P2-2 | 失敗中の2テストの原因は**テストインフラ**（`cases/__tests__/hooks.test.tsx:94`・`documents/__tests__/hooks.test.tsx:157`）。`renderHookWithProviders` を2回呼ぶと React ルートが2つになり、別ルートに invalidate 結果が届かない | `renderHookWithProviders(() => ({ list: useDocuments(id), intake: useIntakeDocument(id) }))` の形にまとめるか `queryClient.getQueryData()` で検証。`test-utils.tsx` に理由をコメント。**hooks 実装を触らない**（実装は正しい） |
| P2-3 | orval ユニオン応答の絞り込みを各 `api.ts` で個別キャスト（`cases/api.ts:21`・`documents/api.ts:14,22`。typecheck エラーの原因） | `shared/api/unwrap.ts` に `unwrapSuccess()` を1つ作り `response.status` で narrowing。以後の feature も同じ関数を使う（CV-015: 1箇所に集約） |
| P2-4 | `Object.assign(new Error(), {...})` で `ApiError` を偽装（`IntakePage.test.tsx:160-166,184-189`・`CaseListPage.test.tsx:154-156`） | `new ApiError(413, { code, message, details })` を使う。hooks は `instanceof ApiError` で分岐するため、偽装は誤った実装を誘導する |
| P2-5 | `cases.list.footnote` に SCR-01 注記②の核心が無い | 「上司の評価確認は原資料への適合確認であり、**対外送付の承認ではありません**」を追加（FUNC-10） |
| P2-6 | SCR-02 の必須表示に対応する i18n キーが未定義（仮上限の注記・「上記は表示例です」等の混同防止注記・案件メタ・二重投入の説明） | **components 着手前に** 03-spec の UI 要素表と1対1でキーを起こす（後付けで JSX 直書きになるのを防ぐ） |
| P2-7 | `@types/jest@^30` と `jest@^29.7` のメジャー不一致（`package.json:37`） | `@types/jest@^29` に揃える |
| P2-8 | `orval.t202.config.ts` / `tsconfig.t202.json` が CV-017 に抵触 | **T-103 では触らない**。C-1 で整理する（無断削除しない） |

---

## 3. P3（軽微。手が空いたら）

- P3-1 `cases/hooks.ts:25,33` `CreateCaseInput` を使用箇所より前に宣言
- P3-2 query key の形を揃える（`casesQueryKey` 定数 vs `documentsQueryKey(caseId)` 関数）
- P3-3 `test-utils.tsx:24-36` に「ThemeProvider を含めないのでトークン経由はテストで検証されない」旨をコメント
- P3-4 コンポーネントテストの日本語直値 assert を `i18n.t()` 経由に寄せるか、意図をコメント
- P3-5 `documents.readStatus.encrypted` は AD-006 で当面到達しない表示。注記があると誤解がない

---

## 4. 未完成部分（T-103 の完了に必要）

1. `features/cases/components/CaseListPage.tsx`（`"use client"`）
2. `features/documents/components/IntakePage.tsx`（`"use client"`・props `{ caseId: number }`）
3. `features/cases/index.ts` / `features/documents/index.ts`（app から直接 components を import させない）
4. `src/app/(portal)/cases/page.tsx`（**薄い Server Component**）
5. `src/app/(portal)/cases/[caseId]/intake/page.tsx`（同上）
6. `src/app/page.tsx` の `redirect("/dashboard")` → `/cases`（AD-009）
7. **3状態の実体**: 空（次の行動へ誘導）／ローディング（skeleton か明示メッセージ）／
   エラー（**原因と直し方**。「エラーが発生しました」だけは禁止）
8. SCR-02 の未定義 i18n（P2-6）と SCR-01 のテーブル列見出し
9. モック `#SCR-01` / `#SCR-02` との突き合わせ

### 画面側で必ず守ること（design-guidelines / N03）

- **読取結果は5区分をそれぞれ別の文言**で出す（`success` / `partial` / `unreadable` / `encrypted` / `unsupported`）。
  **`partial` を「成功」と表示しない**
- **状態は必ずラベル文字を持つ**（色だけで伝えない）。進捗ステータスは「n/4 段階名」の文字
- **primary（塗り）ボタンは1画面に1つまで**／**h1 は1画面1つ**
- SCR-02 冒頭に「外部リンクを取得しない」バナー（AE06）
- **デザイン値のハードコード禁止**（`tokens.ts` / theme 経由。PostToolUse の design-lint が検出）
- **JSX に日本語直書き禁止**（`t()` 経由）
- 415 は「投入の事実は記録された」と分かる表示、同一ファイル2回投入で**2行残る**（X03）

---

## 5. 完了条件（これを満たすまで再レビューを依頼しない）

1. **`make check-fe` が green**（`--confcutdir` や専用 tsconfig で範囲を切った実行を「検証した」と呼ばない）
2. `node .claude/scripts/design-lint.mjs` が**違反ゼロ**
3. `docs/t103-handoff.md` を新規作成し、以下を書く（CODEX-INSTRUCTIONS §6）:
   - **レビュー対応表**: 指摘番号 / 変更内容（ファイル:行）/ **RED を確認したテスト名と実行コマンド・件数**
   - 既存テストを変更・削除した場合は**その理由**（P1-1・P2-2・P2-4 は既存テストの修正になるので必ず書く）
   - テストの強度は「変異させたら落ちるか」で示す（例: `retry: false` を `1` に戻したら P1-3 のテストが落ちる）
   - 判断に迷った点・設計書の不足（勝手に決めず記載）
   - 希望 Status（memory へ転記するのは Claude）
4. 「再レビュー依頼」の記入

> **やらないこと**: `.claude/memory.md` の編集／レビュー／commit／`orval.t202.config.ts` 等の無断削除／
> T-204 の範囲（エージェント起動ボタン・ポーリング UI）の先取り実装
