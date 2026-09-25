# API・IPO一覧（詳細設計）: OCTG 引合 Item List 作成エージェント

> Vモデル: 詳細設計 / 対応する検証: 単体テスト
> 先に API の全体像（一覧・認証）を示し、その上で業務フローごとのデータの流れ（Input/Process/Output）がどの API で実現されるかを整理する。
> 認証・認可の方針は ②`02-requirement.md` 4章（N02）が正。テーブルは ④`04-db.md`、エージェントのツールは `agent-plan.md` が正。
> **正確な型・JSON構造・バリデーションは orval スキーマを SSOT とする。**本書は契約の「意味」（フィールドの意味・エラーの意味論）を定義する。

## 0. 前提

### 0.1 認証・権限の扱い

02 N02 のとおり **認証は無い**（ローカル単一利用者の PoC）。したがって API一覧の「認証」欄はすべて **不要**、「必要権限」欄は**アクセス制御ではなく呼び出し元の区分**を示す。

| 区分 | 意味 |
|------|------|
| `UI` | 画面（人の操作）から呼ぶ。**エージェントのツール一覧に登録しない** |
| `AGENT` | AGENT-01 のツールとして登録する。人の画面からは呼ばない |
| `UI/AGENT` | 両方から呼ぶ（参照系） |

**この区分は「ツール登録」＋「パス分離」で担保する（パス分離は実装済み）。**API 側に認可の仕組みが無いため、「エージェントが人の記録（④D層）を書けない」保証は、①エージェント実行時に渡すツール一覧に `UI` 区分の API を含めないこと、②**`UI` 区分の API がエージェントから到達できないパスに置かれていること**の2重で成立させる（7.1）。これは PoC の割り切りであり、複数利用者・本番運用では API 側の認可が別途必要になる。

### 0.2 通信・形式

> **422 の形（2026-09-13 追記・TODO-005 の明文化）**: 422 も `{code, message, details}` 形で返し `code` を必ず持つ（`E_REQUEST_INVALID` / `E_FIELD_NOT_EDITABLE`）。業務コードの HTTP status は `app/api/errors.py` の対応表 1 箇所で決め、構造違反（path/query 形式・snake_case キー）は 422、それ以外は表の値（既定 400）。

| 項目 | 決定 |
|------|------|
| 形式 | JSON over HTTP。ローカルホストのみで待ち受ける（外部公開しない・N02） |
| 文字列 | 資料由来の文字列は**そのまま返す**。先頭 `=` 等の数式化回避は .xlsx 出力時に行う（N05） |
| 日時 | ISO 8601（タイムゾーンつき）。API が日時を補完しない |
| エラー | `{ code, message, details }` の共通形。`code` は本書 6章の一覧を SSOT とする |
| ページネーション | 明細は1案件あたり最大十数行のため**導入しない**。資料の全文検索（`/search`）のみ `limit` を持つ |
| 冪等性 | ④の追記型に合わせ、記録系 POST は**毎回新しい行を作る**（同じ内容の再送は重複記録になる）。UI 側で二重送信を防ぐ |

### 0.3 パス（実装済みのパス分離）

本書 1章のパスは**版プレフィックスと区分プレフィックスを省いた相対表記**である。実際のパスは区分に応じて次のようになる（`backend/app/main.py` の `API_V1` 定数1箇所で版を管理し、`app/api/agent/router.py` / `app/api/ui/router.py` が区分プレフィックスを持つ）。

| 区分 | 実際のパス | 例 |
|------|-----------|----|
| `AGENT` | `/api/v1/agent/...` | 16 → `POST /api/v1/agent/versions/{versionId}/items` |
| `UI` | `/api/v1/ui/...` | 29 → `POST /api/v1/ui/versions/{versionId}/edits` |
| `UI/AGENT`（参照系 4・6・7・11・20） | **両方に同一ハンドラを登録する** | 4 → `GET /api/v1/agent/cases/{caseId}/documents` と `GET /api/v1/ui/cases/{caseId}/documents` |

**`UI/AGENT` を両方に登録する理由**: エージェントに渡すベースURLを `/api/v1/agent` の1つに限定できるため（`/ui/*` を知らせない）。参照系は副作用が無いので二重登録による害はなく、逆に片側だけに置くと、UI が `/agent/*` を叩く（境界が曖昧になる）か、エージェントに `/ui/*` のベースURLを渡す（分離が無意味になる）かのどちらかになる。**OpenAPI には両パスが出るが、生成される orval フックは UI 側（`/ui/*`）を使う。**

この分離は `backend/tests/unit/test_api_path_separation.py` が機械的に検査する（版プレフィックスの一元化／全業務 API が `agent` か `ui` に属すること／人の記録（F群）と出力（G群）が `/agent/*` 配下に無いこと）。**このテストを消さない。** 同一パスに AGENT の POST と UI の GET が共存する経路（#19/#27 `/versions/{versionId}/inventory`）はパス単位の検査では区別できないため、`(method, path)` 単位の存在検査（`tests/unit/test_api_path_separation_live.py`）で「AGENT に GET を出さない／UI に POST を出さない」を守る（2026-09-13・AD-026）。

### 0.4 フィールド命名・列挙値・範囲指定（T-102 で確定）

> **数値の表現（2026-09-13 追記・AD-022）**: `numeric` 列の値（`qtyValue`・`odValue` 等）は応答・要求とも **JSON 文字列**（例 `"150"`、`"13.375"`）。浮動小数点を経由しない（CLAUDE.md 決定事項2）。取消 API（#30/#32）は新規行を作らない UPDATE のため **200** を返す。

| 項目 | 決定 |
|------|------|
| JSON のフィールド名 | **camelCase**（`caseId` / `caseCode` / `documentId` / `readStatus` / `partRole` / `issueType`）。本書1章以降の表記に合わせる。DB の列名（snake_case）をそのまま外に出さない |
| #1 の進捗ステータスの値 | `intake`（①資料投入＝確定版なし）/ `draft_review`（②案の確認＝確定版あり）/ `staff_checked`（③）/ `review_checked`（④）。**③④は `versions.current_state` と同じ語彙**、①②は UI の表示区分（状態遷移の記録対象にしない） |
| #6 の範囲指定 | `fromSeq` / `toSeq`（`document_pages.seq`。1始まり・両端を含む・省略時は資料全体）。**locator は形式ごとに表記が違う（`p.N` / シート名 / `body:N`）ため範囲指定には使わない**。応答は locator と `readStatus` をページごとに返す |
| #9 のリクエスト本文 | `locator`（省略＝資料全体）/ `issueType`（④`document_issues.issue_type` の語彙）/ `detail`（**空不可**・`E_DETAIL_REQUIRED`） |
| 原本の保存先 | `documents.storage_path` は `{STORAGE_ROOT}/{caseId}/{uuid4}{拡張子}`。`STORAGE_ROOT` はアプリ設定（既定 `backend/storage`・git 管理外）。**元のファイル名をパスに使わない**（衝突と混入を防ぐ）。#10 は `STORAGE_ROOT` 配下であることを検証してから返す |

## 1. API一覧

### A. 案件・資料（FUNC-01, FUNC-02）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 1 | `/cases` | GET | 案件一覧（進捗ステータス・表示状態・送付可否つき。**初版 G1 実装は `progressStatus` のみ**。表示状態は G3（T-302）で `latestVersionId` として付与済み。送付可否は G5（T-502）で `latestSendoff`（最新版の最新 `sendoff_decisions.decision`・null 可）として付与する — memory AD-013 / AD-029 ⑬）。**2026-09-24 改訂（F-15・memory AD-036 ②）**: 最新の確定版について `latestStateEvent`（#22 と同じ `StateEventRecord`・記録者/日時つき・無ければ null）・`questionTotal`（案件レベルを含む確認事項の総数）・`unresolvedCount`（#22 と同じ未解決の定義）を付与する。版が無い案件は 3 項目とも null。記録の一覧は行の展開時に #28 を版ごとに取得する。SELECT 回数は案件数に依らず一定（5 回） | 不要 | UI |
| 2 | `/cases` | POST | 案件を作成する | 不要 | UI |
| 3 | `/cases/{caseId}` | GET | 案件の基本情報 | 不要 | UI |
| 4 | `/cases/{caseId}/documents` | GET | 資料一覧と読取状態（**案件ID・案件名を併せて返す**）。各資料に `pageCount`（PDF=ページ数／xlsx=シート数／判定できなければ null）と `unreadableLocators`（受付時に記録した読取不能範囲。例 `["p.2"]`）を含める（2026-09-24 追記・シナリオテスト TEST-01 #2・TEST-02 #1） | 不要 | UI/AGENT |
| 5 | `/cases/{caseId}/documents` | POST | 資料を投入する（受付・形式判定・テキスト抽出） | 不要 | UI |
| 6 | `/documents/{documentId}/content` | GET | 本文・表セル値をページ／シート範囲で取得 | 不要 | UI/AGENT |
| 7 | `/documents/{documentId}/email` | GET | .eml の構造（ヘッダ・本文・引用部・添付一覧） | 不要 | UI/AGENT |
| 8 | `/cases/{caseId}/search` | GET | 案件内の参照解決（「本文3.2項による」等） | 不要 | AGENT |
| 9 | `/documents/{documentId}/issues` | POST | 読取不能・未走査の範囲を記録する | 不要 | AGENT |
| 10 | `/documents/{documentId}/file` | GET | 原資料そのものを開く（読取専用・SCR-05） | 不要 | UI |

### B. 規則（FUNC-05, FUNC-06, N04）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 11 | `/rule-sets/{ruleVersion}` | GET | 表記・単位・分割規則 R01〜R08 と論理項目定義（`ruleVersion` に `current` を指定すると ④`rule_sets.is_current = true` の版を返す） | 不要 | UI/AGENT |

### C. エージェントの起動・監視（agent-plan）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 12 | `/cases/{caseId}/agent-runs` | POST | AGENT-01 を起動して案を作成する | 不要 | UI |
| 13 | `/agent-runs/{runId}` | GET | 実行の進捗・結果・停止理由を取得する | 不要 | UI |
| 14 | `/agent-runs/{runId}/steps` | GET | ツール呼び出しトレース（外部送信をしていない証跡） | 不要 | UI |
| 14a | `/cases/{caseId}/agent-runs/active` | GET | 案件の実行中 run の ID（無ければ `runId: null`）。画面を離れた・再読込した後に進捗表示（#13 のポーリング）へ戻るために使う（2026-09-24 追加・TEST-04 #1・TODO-013） | 不要 | UI |

### D. 成果物の書き込み（AGENT-01 のツール・④C層）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 15 | `/versions/{versionId}/header` | POST | 案件情報を原文の粒度で登録する | 不要 | AGENT |
| 16 | `/versions/{versionId}/items` | POST | 明細行を登録する（原項番・出典・状態が必須） | 不要 | AGENT |
| 17 | `/versions/{versionId}/evidence` | POST | 項目ごとの根拠を登録する（対象行は body の `itemId`。**省略＝案件レベルの根拠**） | 不要 | AGENT |
| 18 | `/versions/{versionId}/questions` | POST | 確認事項を対象つきで登録する | 不要 | AGENT |
| 19 | `/versions/{versionId}/inventory` | POST | 原明細インベントリと対応関係を登録する | 不要 | AGENT |
| 20 | `/versions/{versionId}/validation` | GET | 完了条件の機械判定を実行し違反一覧を返す | 不要 | UI/AGENT |
| 21 | `/versions/{versionId}/finalize` | POST | 版を「作成案」として確定する | 不要 | AGENT |

### E. 成果物の参照（画面）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 22 | `/cases/{caseId}/versions` | GET | 版の履歴（版・生成所要・状態・未解決件数）。**生成所要 `elapsedSec` は G6 T-603 で付与済み**（`agent_runs.elapsed_sec` を `version_id` で結線。未記録は `null`。Decimal は丸めず文字列。Build AD-029 ⑭）。G5 では `carryOver`・`latestStateEvent`・`latestBounce`・`latestSendoff`・`bounced`・`needsRecheck` を付与（下記「22 の引き継ぎ警告の材料」） | 不要 | UI |
| 23 | `/versions/{versionId}` | GET | 版の要約（案件情報・件数・状態・確認の進捗） | 不要 | UI |
| 24 | `/versions/{versionId}/items` | GET | 明細（**未取消の訂正を適用した現在値**と訂正履歴） **応答の各行に `rowMatch: {confirmationId, recordedBy, recordedAt} | null`（未取消の一致確認。2026-09-13 追記・AD-024。SCR-03 の照合チェック表示と #32 の取消に必要）** | 不要 | UI |
| 25 | `/versions/{versionId}/items/{itemId}/evidence` | GET | 行の根拠・原表記・出典・原文抜粋（SCR-04） | 不要 | UI |
| 26 | `/versions/{versionId}/questions` | GET | 確認事項＋最新判断（対応状況・解決状態） | 不要 | UI |
| 27 | `/versions/{versionId}/inventory` | GET | 網羅性照合の両表と集計（SCR-05）。**応答形（2026-09-13・AD-025）**: `summary`（`sourceEntryCount` 総要素 / `sourceItemCount` 原明細=status≠excluded / `outputRowCount` / `splitEntryIds` 1 entry に link≥2 / `excludedEntryIds` / `unmappedEntryIds` unmapped∧link0 / `orphanItemIds` link なし item / `multiMappedItemIds` / `inconsistentEntryIds` status と構造の不一致 / `coverage: {confirmationId, recordedBy, recordedAt}\|null`）、`entries[]`（位置・原項番・抜粋・status 保存値・basis・`linkedItems`・構造判定 `judgement`。`(seq, id)` 順）、`items[]`（行ID・原項番・グループ・`sourceEntries`・`hasSource`）。判定定義は 04-db:681 が正。unmapped>0 は何も拒否しない（対応なし 0 件は保証ではない） | 不要 | UI |
| 28 | `/versions/{versionId}/records` | GET | 人の記録の一覧（訂正・確認・判断・状態・差し戻し・送付可否） | 不要 | UI |
| 40 | `/versions/{versionId}/evidence` | GET | **版の全根拠を一括取得**（.xlsx 根拠シート用。行の根拠と案件レベルの根拠の両方） | 不要 | UI |

### F. 人の記録（④D層・**エージェントに登録しない**）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 29 | `/versions/{versionId}/edits` | POST | 値の訂正を記録する（対象項目・新値・理由・修正者） | 不要 | UI |
| 30 | `/versions/{versionId}/edits/{editId}/undo` | POST | 訂正を取り消す（行は消さず取消を記録）。**入力 `recordedBy`（取消者・必須・空文字禁止）→ `undone_by`**（2026-09-13・memory AD-017） | 不要 | UI |
| 31 | `/versions/{versionId}/confirmations` | POST | 一致確認・網羅性確認を記録する | 不要 | UI |
| 32 | `/versions/{versionId}/confirmations/{confirmationId}/undo` | POST | 確認を取り消す（取消も履歴に残す）。**入力 `recordedBy`（取消者・必須）→ `undone_by`**（AD-017） | 不要 | UI |
| 33 | `/versions/{versionId}/questions/{questionId}/judgements` | POST | 確認事項の判断を記録する | 不要 | UI |
| 34 | `/versions/{versionId}/state-events` | POST | 状態遷移を記録する（担当者確認済み・評価確認済み） | 不要 | UI |
| 35 | `/versions/{versionId}/bounce-comments` | POST | 行ごとの差し戻しコメントを記録する | 不要 | UI |
| 36 | `/versions/{versionId}/bounces` | POST | 差し戻しを記録する（状態は戻さない） | 不要 | UI |
| 37 | `/versions/{versionId}/sendoff-decisions` | POST | 送付可否を記録する（評価確認とは別） | 不要 | UI |

### G. 出力（FUNC-09）

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 38 | `/versions/{versionId}/exports` | POST | .xlsx を書き出す（5シート） | 不要 | UI |
| 39 | `/versions/{versionId}/exports` | GET | 出力履歴（初回出力の保全確認に使う） | 不要 | UI |

> **同一リソースのパスは1系統に寄せる。**根拠（`evidences`）は書き込み（17）・行単位の読み取り（25）・版一括の読み取り（40）をすべて `/versions/{versionId}/...` 配下に置く。**書き込みは `POST /versions/{versionId}/evidence` とし、対象行は body の `itemId` で受ける（省略＝案件レベルの根拠）。**書き込みだけ `/items/{itemId}/evidence` にすると、④`evidences.item_id IS NULL`（見積期限・納地など `case_headers` の項目の根拠。部分UNIQUE索引で1項目1件に保たれている）を登録する経路が作れず、版が確定済みかの判定（`E_VERSION_FINALIZED`）と版スコープの検査（④原則2）もパスから導けない。行単位の読み取り（25）は SCR-04 のための読み取り専用パスとして残す。
> **記録系のパスは複数形の追記型で揃える。**37 は `/sendoff-decisions`（`/exports` `/bounces` `/confirmations` と同じ）。送付可否は単数の設定値ではなく**判断の記録を積む**リソースであるため、単数リソース `/sendoff` にはしない。
> **記録系はすべて版スコープ配下に置く。**33 は `/versions/{versionId}/questions/{questionId}/judgements` とする。`/questions/{id}/judgements` にすると、17 を版スコープへ寄せたのと同じ理由（版が確定済みかの判定と ④原則2「別版の行・事項に記録を紐づけない」の検査をパスから導けない）で境界が緩む。

> **メーカーへの送信・外部LLMへの送信を行う API は定義しない。**01 の原則「AI は送信しない」と D05 未承認のため、**そのエンドポイントを作らないこと自体を設計とする**（②Out of Scope）。

## 2. フローごとの IPO

業務フロー（ユースケース）単位で切る。**FLOW-02 だけがエージェントのループ**であり、他は決定的な処理。

### FLOW-01 案件を作り資料を投入する

**対応機能(②)**: FUNC-01, FUNC-02 ／ **画面**: SCR-01 → SCR-02

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件名・案件ID | 案件を作成する | 案件ID | 2 `POST /cases` | `cases` |
| 2 | ファイル（PDF/XLSX/EML/TXT） | 形式を判定し、上限（D02）を検査。**超過は具体的に通知し切り捨てない** | 受付結果 | 5 `POST /cases/{id}/documents` | `documents` |
| 3 | 受け付けた資料 | テキスト・セル値をページ／シート単位で抽出。読めないページは記録する | 抽出結果・読取状態 | 5（同一処理内） | `document_pages` / `document_issues` |
| 4 | .eml | ヘッダ・本文・引用部・P.S.・添付を分離する。**表示順で新旧を決めない** | 構造化されたメール | 5（同一処理内） | `email_parts` |
| 5 | 案件ID | 資料一覧と読取結果を表示する。`partial` を成功と表示しない | 読取結果一覧 | 4 `GET /cases/{id}/documents` | `documents` / `document_issues` |

### FLOW-02 エージェントが Item List 案を作る

**対応機能(②)**: FUNC-02〜07 ／ **画面**: SCR-02（起動）→ SCR-03（結果） ／ **詳細**: `agent-plan.md`

> ステップ4〜9は**エージェントのループ**であり、順序・回数は実行時に LLM が決める。下表は正常系のスケッチで、仕様ではない。

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件ID | 起動前に読取成功資料が1件以上あるか、上限内かを検査する。**満たさなければ起動しない**（AE05b） | 実行ID・版ID | 12 `POST /cases/{id}/agent-runs` | `agent_runs` / `versions` |
| 2 | 実行ID | 規則版を固定し、使用モデルを記録する | 規則セット | 11 `GET /rule-sets/{v}` | `rule_sets` / `agent_runs` |
| 3 | 案件ID | 何が投入されているか確認する | 資料一覧 | 4 | `documents` |
| 4 | 資料ID・範囲 | 本文・表・注記を読む。読めない範囲は記録して続行する | テキスト／`unreadable` | 6・7・9 | `document_pages` / `document_issues` |
| 5 | 参照表現 | 「本文3.2項による」等の参照先を案件内から探す | 該当箇所 | 8 | `document_pages` |
| 6 | 読んだ内容 | 共通条件を適用し、個別例外を優先する。原文の粒度を落とさない | 案件情報 | 15 | `case_headers` |
| 7 | 明細候補 | 表記を整理し、**数値と単位を分離**、未確定は状態で保持、択一・定尺長は別行にする。**相反する記載で優先関係が判定できない場合はどちらも採用せず、同一 `groupCode`（`CFL-n`）の候補2行として両方を残す**（X04・④3.3） | 明細行 | 16 | `items` / `item_ends` |
| 8 | 登録した行・案件情報 | 項目ごとに原値・採用値・出典・引用・変更理由を残す。**案件情報（見積期限・納地等）の根拠は `itemId` を省略して登録する** | 根拠 | 17 | `evidences`（行スコープ／`item_id IS NULL`） |
| 9 | 不明・不足 | 埋めずに確認事項として対象つきで差し出す | 確認事項 | 18 | `questions` |
| 10 | 資料の全要素 | 明細にしなかった要素を**除外理由つきで**棚卸しする | インベントリ | 19 | `source_inventory_entries` / `inventory_links` |
| 11 | 版ID | **完了条件の機械判定**を実行する（出典欠落・単位欠落・原項番欠落・候補1件のグループ・未走査範囲など。3.4 が種別の SSOT） | 違反一覧 | 20 | 参照のみ |
| 12 | 違反0件 | 版を作成案として確定する。違反が3回続けば中断、上限超過で強制停止 | 版の確定／停止理由 | 21 | `versions` / `agent_runs` |
| 13 | 実行ID | 画面が進捗と結果を取得する（ポーリング） | 状態・経過秒・版ID | 13 | `agent_runs` |

### FLOW-03 担当者が明細を確認し訂正する

**対応機能(②)**: FUNC-05, FUNC-07, FUNC-08 ／ **画面**: SCR-03 ⇄ SCR-04

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 版ID | 明細を取得する。**未取消の訂正を適用した現在値**と訂正履歴を返す | 明細・件数 | 24 | `items` + `item_edits` |
| 2 | 行ID | 原表記・採用値・出典・原文抜粋を表示する | 根拠 | 25 | `evidences` |
| 3 | 行ID・確認者名 | 出典と一致することを記録する。**確認者名が空なら記録しない** | 一致確認 | 31 | `confirmations`（`row_match`） |
| 4 | 対象項目・新値**または新状態**・理由・修正者 | 制約を検査して訂正を記録する。**単位なし数量・状態なし未確定・択一の合算・原表記の編集を拒否**（X11）。値を消して「記載なし」等にする訂正は `newState` で受ける（3.6） | 訂正記録 | 29 | `item_edits`（`new_value` / `new_state`） |
| 5 | 訂正ID | 取り消す。**行は消さず取消日時を記録** | 取消記録 | 30 | `item_edits.undone_at` |
| 6 | 確認事項・判断者 | 対応状況と解決状態を**別々に**記録する | 判断記録 | 33 | `question_judgements` |

### FLOW-04 担当者が網羅性を照合する

**対応機能(②)**: FUNC-03, FUNC-06, FUNC-08 ／ **画面**: SCR-05

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 版ID | 資料側インベントリと明細の対応表を作り、欠落・余分・分割を判定する | 両表と集計 | 27 | `source_inventory_entries` / `inventory_links` / `items` |
| 2 | 資料ID | 原資料を読取専用で開く。**元ファイルを変更しない**（N01） | ファイル | 10 | `documents` |
| 3 | 確認者名 | 網羅性確認を記録する。**確認者名が空なら記録しない** | 網羅性確認 | 31 | `confirmations`（`coverage`） |
| 4 | 記録ID | 取り消す（取消も履歴に残す） | 取消記録 | 32 | `confirmations.undone_at` |

### FLOW-05 担当者が確認を完了して引き渡す

**対応機能(②)**: FUNC-08, FUNC-10 ／ **画面**: SCR-03 → SCR-06

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 版ID | 全行の一致確認と網羅性確認の充足を検査する | 遷移可否・未充足の内訳 | 23 | `confirmations` / `items` |
| 2 | 担当者名 | 状態を担当者確認済みにする。**未解決があっても遷移可。件数を記録に残す** | 状態イベント | 34 | `version_state_events` / `versions.current_state` |

### FLOW-06 上司が評価確認・差し戻し・送付可否を記録する

**対応機能(②)**: FUNC-08, FUNC-10 ／ **画面**: SCR-06

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 版ID | 確定した明細・訂正・判断・要約・変更／判断事項・未解決事項を取得する | 承認画面のデータ | 23・24・26・28 | `items` / `item_edits` / `questions` / `question_judgements` |
| 1b | 行ID（画面内） | 全行の索引と**行単位の索引**（③SCR-06 の右ドロワー）は、step1 で取得済みのデータを**クライアント側で絞り込んで**表示する。**API を追加しない**（行ごとに問い合わせると明細数ぶんの呼び出しになる） | 行に紐づく事項の一覧 | —（追加なし） | 同上 |
| 2 | 行ID・コメント・確認者名 | 差し戻す点を行ごとに記録する | 行コメント | 35 | `bounce_comments` |
| 3 | 確認者名 | 行コメントを連結して差し戻しを記録する。**状態は担当者確認済みのまま**（X13） | 差し戻し記録 | 36 | `bounces` / `bounce_comments.bounce_id` |
| 4 | 確認者名 | 評価確認済みにする。未解決件数を記録に残す | 状態イベント | 34 | `version_state_events` |
| 5 | 判断・理由・判断者 | 送付可否を記録する。**保留・承認は理由必須**。評価確認とは別の記録 | 送付可否 | 37 | `sendoff_decisions` |

### FLOW-07 .xlsx を出力する

**対応機能(②)**: FUNC-09 ／ **画面**: SCR-03

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 版ID | 5シートを組み立てる。訂正適用後の値・根拠・確認事項・記録・状態を反映 | .xlsx | 38 | ④6章の対応表 |
| 2 | 出力内容 | 外部由来の文字列を**数式化しない**。候補関係・状態を色だけで表さない（N05） | 安全な .xlsx | 38（同一処理内） | — |
| 3 | 出力結果 | 出力時点の状態・送付可否・未解決件数を**その時点の値として保存**し、書き出したファイルも**サーバ側に保存してパスとハッシュを残す**（⑥共通手順3・4 の初回出力の保全） | 出力記録・保全ファイル | 38 | `exports`（`storage_path` / `content_hash` / `is_initial`） |
| 4 | 版ID | 出力履歴を表示する。**初回出力（`is_initial`）の保全は `content_hash` の照合で確認する**（差し替わっていれば採点の根拠が失われるため検知する） | 履歴 | 39 | `exports` |

### FLOW-08 記録がある版を再実行する

**対応機能(②)**: FUNC-10, N04 ／ **受入基準**: X12 ／ **画面**: SCR-02・SCR-03

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件ID | 既存版に記録があるか検査し、**件数つきの引き継ぎ警告**を返す | 警告と記録の内訳 | 22 | `versions` / `item_edits` / `confirmations` / `question_judgements` |
| 2 | 案件ID（確認後） | 新しい版を作る。**前版の記録をコピーしない**。`prev_version_id` で系譜のみ残す | 新版（作成案） | 12 | `versions.prev_version_id` |
| 3 | 新版ID | 「前版の記録は引き継がれていない」旨を表示する。**既存版は保全し上書きしない** | 表示 | 22・23 | `versions` |

## 3. エンドポイント詳細

> 型・JSON構造・バリデーションは orval スキーマが SSOT。ここでは契約の意味とエラーの意味論を定義する。
> **すべてのエンドポイントを同じ密度では書かない。**要件の制約を背負う10本を詳細化し、残りは 5章に要約する。詳細化の基準は「エラー応答が業務ルールそのものになっているか」。

### 3.1 エージェントを起動する

- **Method / Path**: `POST /cases/{caseId}/agent-runs`
- **目的**: AGENT-01 を起動し、作成案の版を1つ作る
- **認証 / 必要権限**: 不要 / `UI`
- **対応テーブル(④)**: `agent_runs` / `versions` / `rule_sets`
- **対応フロー**: FLOW-02 step1、FLOW-08 step2
- **スキーマ**: `schemas/agent-run-request`（orval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `caseId` | Yes | 対象案件。**他案件の資料は読ませない**（N01） |
| `ruleVersion` | No | 使用する規則版。**省略または `current` 指定時は ④`rule_sets.is_current = true` の版**（最大 id や `rule_version` の文字列順で決めない）。採用した版は `agent_runs.rule_set_id` と `versions.rule_set_id` に同値で残す |
| `acknowledgedCarryOver` | 条件付き | 既存版に記録がある場合に必須。**引き継がれない旨を利用者が確認したことを示す**（X12） |

#### レスポンス（成功 202）

| フィールド | 意味 |
|-----------|------|
| `runId` | 実行ID。以後の進捗取得に使う |
| `versionId` | 作成中の版ID。確定前は画面に出さない |
| `startedAt` | 起動時刻。経過時間の起点（N06） |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 読取成功の資料が1件も無い。**明細0件の作成案を作らない**（AE05） | `E_NO_READABLE_DOCUMENT` |
| 400 | 既存版に記録があるのに確認が無い（X12） | `E_CARRY_OVER_NOT_ACKNOWLEDGED` |
| 409 | 同じ案件で実行中の `agent_run` がある。二重生成を防ぐ | `E_RUN_IN_PROGRESS` |
| 413 | 入力上限（D02）超過。**具体的な超過内容を返す**（X09・AE05b） | `E_LIMIT_EXCEEDED` |
| 503 | `AGENT_MODE=claude` だがキー未設定（実モデルが構成されていません） | `E_EXTERNAL_SEND_NOT_APPROVED` |

### 3.2 実行の進捗・結果を取得する

- **Method / Path**: `GET /agent-runs/{runId}`
- **目的**: 生成中の表示（SCR-02）と結果の取得。画面はこれをポーリングする
- **必要権限**: `UI` ／ **対応テーブル**: `agent_runs`（`stage` / `stage_detail` 列。④3.2） ／ **フロー**: FLOW-02 step13
- **スキーマ**: `schemas/agent-run`

#### レスポンス（成功 200）

| フィールド | 意味 |
|-----------|------|
| `outcome` | `running` / `success` / `failed` / `stopped` |
| `stage` | 進捗の段階。`reading` / `extracting` / `self_checking` / `done`（④`agent_runs.stage`）。**明細そのものは返さない**（確定前の行を正解に見せない） |
| `stageDetail` | 段階の内訳（`資料 2/5` 等の材料。④`agent_runs.stage_detail`）。画面文言は ③ が正 |
| `turns` / `elapsedSec` | ターン数・経過秒。**人の作業時間には含めない**（N06） |
| `stopReason` | `completed` / `failed` / `max_turns` / `inner_timeout` / `inactivity_timeout` / `outer_timeout` / `repeated_call` / `no_readable_document` / `validation_loop`（④`agent_runs.stop_reason` の CHECK と同値。`.claude/rules/agent-development.md` §3）。**タイムアウトは無応答・内側・外側を区別して返す**（単一の `timeout` に丸めない。外側発火は内側が機能しなかった異常・同 §6） |
| `limits` | その実行に適用した停止閾値（`maxTurns` / `innerTimeoutS` / `inactivityTimeoutS` / `outerTimeoutS`。④`agent_runs.limits`）。D06 が仮値のため、**どの閾値で走った実行か**を画面と評価から追えるようにする |
| `versionId` | 成功時のみ。失敗・中断時は null |
| `isComplete` | 未走査範囲がある場合 false。**完全成功と表示しない**（N03） |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 404 | 実行が存在しない | `E_NOT_FOUND` |

### 3.3 明細行を登録する

- **Method / Path**: `POST /versions/{versionId}/items`
- **目的**: AGENT-01 が抽出した明細を登録する。**②5章・6章の制約をここで拒否する**
- **必要権限**: `AGENT` ／ **対応テーブル**: `items` / `item_ends` ／ **フロー**: FLOW-02 step7
- **スキーマ**: `schemas/item-proposal`

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `rows[].sourceNo` | Yes | 原項番。**全行に必須**（完了条件②） |
| `rows[].qtyState` | Yes | `numeric` / `tba` / `not_stated` / `not_applicable` |
| `rows[].qtyValue` / `qtyUnit` | 条件付き | `qtyState='numeric'` のとき両方必須。それ以外は値を渡してはならない |
| `rows[].odValue` / `wallValue` / `weightValue` / `lengthValue` | No | 値を渡す場合は**対応する単位フィールドが必須**（④items の CHECK と同じ。数量だけでなく全数値項目に適用する・R04） |
| `rows[].odState` / `wallState` / `weightState` / `gradeState` / `connectionState` / `lengthState` / `dueState` / `placeState` | Yes | 重要項目の状態。`stated` / `tba` / `not_stated` / `not_applicable`（④`items` の状態列。**値がある項目は `stated`、無い項目は理由を状態で示す**）。④で NOT NULL・既定値なしのため、**1つでも欠けると行は登録できない**（完了条件③を登録時に担保する） |
| `rows[].qtyRaw` | Yes | 原表記。整理後の値と別に必ず保持する |
| `rows[].gradeRaw` / `kindRaw` | Yes | 原表記（R01・R03） |
| `rows[].groupCode` / `candidateLabel` | 条件付き | 択一・定尺長で分割した行。候補区分だけを渡せない |
| `rows[].ends[]` | No | クロスオーバー等の両端（径・接続・BOX/PIN） |

#### レスポンス（成功 201）

| フィールド | 意味 |
|-----------|------|
| `items[].itemId` / `rowCode` | 登録された行と表示用行ID |
| `rejected[]` | 拒否した行と理由。**部分成功を成功と扱わない** |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 数量が数値なのに単位が無い（②5章・X11） | `E_QTY_UNIT_REQUIRED` |
| 400 | 未確定なのに数値が入っている／状態が無い。**TBA を 0 にしない** | `E_QTY_STATE_INVALID` |
| 400 | 原項番または原表記が無い | `E_SOURCE_REF_REQUIRED` |
| 400 | 候補区分があるのに選択グループが無い | `E_GROUP_REQUIRED` |
| 400 | 外径・肉厚・単重・定尺長に値があるのに単位が無い（R04） | `E_UNIT_REQUIRED` |
| 400 | 重要項目の状態が欠けている（完了条件③） | `E_STATE_REQUIRED` |
| 400 | 値と状態が矛盾する（値があるのに `not_stated` 等／`stated` なのに値が無い） | `E_STATE_VALUE_CONFLICT` |
| 409 | 版が確定済み（`finalized_at` あり）。**確定後に明細を足さない** | `E_VERSION_FINALIZED` |

> **換算値は「拒否する」のではなく「渡す口を持たない」。**「換算値を含むか」はサーバから判定できない（送られてきた数値が原値か換算値かを区別する手段が無い）。したがって D03 未承認の間は、**`rule_sets.conversion_enabled = false` のとき換算値を渡すフィールドをスキーマに持たせない**（未知フィールドは 400 で拒否）。承認後に `convertedValue` / `conversionNote` を追加し、`conversion_enabled = true` の規則版でのみ受け付ける（④7章 D03「換算値を保持する列は承認まで作らない」と同じ担保）。

### 3.4 完了条件を機械判定する

- **Method / Path**: `GET /versions/{versionId}/validation`
- **目的**: `agent-plan` の完了条件①〜⑧を機械判定する。**エージェントに合否を自己申告させない**
- **必要権限**: `UI/AGENT` ／ **対応テーブル**: C層全テーブル＋`agent_run_steps` / `document_pages` / `document_issues`（参照のみ） ／ **フロー**: FLOW-02 step11
- **スキーマ**: `schemas/validation-result`

#### レスポンス（成功 200）

| フィールド | 意味 |
|-----------|------|
| `violations[]` | 違反の種別・対象行・内容。**空配列が合格**（完了条件の判定方法そのもの） |
| `violations[].kind` | `unscanned_range` / `missing_evidence` / `missing_unit` / `missing_source_no` / `orphan_candidate` / `orphan_question` / `excluded_without_basis` / `missing_question` / `unsplit_conflict` |
| `counts` | 明細数・確認事項数・インベントリ件数（画面の表示にも使う） |

#### 違反種別と完了条件の対応（`agent-plan` 完了条件の機械判定リストの SSOT）

| kind | 判定内容 | 判定元 |
|------|---------|-------|
| `unscanned_range` | 読取成功範囲に、当該実行が走査もせず `document_issues` にも記録していない範囲がある（完了条件①） | `document_pages` − `agent_run_steps(document_id, locator)` − `document_issues`。版から実行は `agent_runs.version_id`（UNIQUE・④3.2）で一意に引ける |
| `missing_evidence` | 出典の無い項目がある（完了条件②） | `items` / `case_headers` に対する `evidences` の欠落 |
| `missing_unit` | 値があるのに単位が無い数値項目がある（数量・外径・肉厚・単重・定尺長） | `items`（登録時の CHECK をすり抜けた場合の二重防御） |
| `missing_source_no` | 原項番の無い行がある（完了条件②） | `items.source_no` |
| `orphan_candidate` | 選択グループ（`ALT-n` / `CFL-n`）の候補が1行しかない（**分割し損ね**または片方の取り落とし） | `items.group_code` ごとの行数 |
| `orphan_question` | 確認事項の対象行が実在しない（完了条件⑥） | `questions.item_id` |
| `excluded_without_basis` | 根拠のない除外がある | `source_inventory_entries`（CHECK の二重防御） |
| `missing_question` | 見積期限の時刻・TZ が不足（`quote_deadline_tz_state='missing'`）なのに、案件レベル（`item_id` NULL）の確認事項が無い（完了条件⑥・④ case_headers「`missing` なら確認事項が立つ」。2026-09-24 追加・TEST-05 #5） | `case_headers` / `questions` |
| `unsplit_conflict` | 数量の矛盾（`category='conflict'`・対象項目が数量）の確認事項が、選択グループに属さない1行に付いている（X04・④3.3「CFL-n の候補2行で残す」。2026-09-24 追加・TEST-05 #6） | `questions` / `items.group_code` |

> **20 は読み取りだけを行う。**④`agent_runs.validation_result`（最終違反一覧）を書くのは **21 `POST /versions/{id}/finalize`**（中断時はジョブ側）であり、**GET である 20 は DB を更新しない**（安全メソッドに副作用を持たせない）。エージェントは自己点検のたびに 20 を呼ぶが、記録として残すのは最終判定である。
> **`summed_group`（択一候補の合算）は種別に持たない。**④`items` が合計列を持たず、合算値を格納する場所自体が無いため、この違反は発生し得ない（構造で担保済み。空振りする判定を残すと「チェックしている」という誤った安心を与える）。代わりに、**分割し損ねを検出する `orphan_candidate`** を持つ。
> **「未確定は状態値で保持（数値0でない）」と 完了条件③（重要項目が値または状態で埋まっている）も種別に持たない。**④`items` が重要項目ごとに状態列（`od_state` / `wall_state` / `weight_state` / `grade_state` / `connection_state` / `length_state` / `due_state` / `place_state` / `qty_state`）を持ち、値と状態を対にする CHECK（例 `CHECK((qty_state='numeric' AND ...) OR (qty_state<>'numeric' AND qty_value IS NULL))`・`CHECK((connection_state='stated') = (connection IS NOT NULL))`）で**値も状態も無い行を登録時に弾く**ため。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 404 | 版が存在しない | `E_NOT_FOUND` |

> **T-201補足（2026-09-12）**: 未走査判定にはメールの `email_parts` も含める。メール locator、issue の適用範囲、TBA・両端仕様の根拠項目名は `04-db.md` §3.3「T-201 補足」の契約に従う。

### 3.5 版を作成案として確定する

- **Method / Path**: `POST /versions/{versionId}/finalize`
- **目的**: エージェントの成果物を「作成案」として確定し、画面に出す
- **必要権限**: `AGENT` ／ **対応テーブル**: `versions` ／ **フロー**: FLOW-02 step12
- **スキーマ**: `schemas/finalize-result`

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | `validate_draft` に違反が残っている。**違反があるまま確定させない** | `E_VALIDATION_FAILED` |
| 409 | 明細が0件。**明細0件の正常な作成案を作らない**（N03・AE05） | `E_NO_ITEMS` |
| 409 | すでに確定済み | `E_VERSION_FINALIZED` |

> このエンドポイントは**状態を `draft` にする**だけで、担当者確認済み・評価確認済みへは進めない。状態の前進は 3.7（人の操作）でのみ起きる。

### 3.6 値の訂正を記録する

- **Method / Path**: `POST /versions/{versionId}/edits`
- **目的**: 人が値を訂正する。**旧値を上書きせず記録として積む**
- **必要権限**: `UI`（**エージェントのツールに登録しない**） ／ **対応テーブル**: `item_edits` ／ **フロー**: FLOW-03 step4
- **スキーマ**: `schemas/item-edit`

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `itemId` | Yes | 対象行 |
| `field` | Yes | 対象項目。**編集可能項目のみ**。原表記・出典・原項番・選択グループは受け付けない |
| `newValue` | 条件付き | 新値。数量を数値にする場合は `newState="numeric"` と `qtyUnit` を同時に送る（Service が `qty_value` / `qty_unit` の 2 行を**1トランザクションで**記録。2026-09-13 実装語彙に合わせて改定・memory AD-022）。`newState` が `stated`/`numeric` 以外のときは**送らない** |
| `newState` | 条件付き | 訂正後の状態（`stated` / `tba` / `not_stated` / `not_applicable`）。**値を消して「記載なし」「適用なし」「TBA」にする訂正**はこれだけで表現する（③SCR-04・X11）。`newValue` と `newState` の**少なくとも一方**が必須（④`item_edits` の CHECK と同じ） |
| `reason` | Yes | 修正理由。**空文字は不可** |
| `recordedBy` | Yes | 修正者。**AI が補完しない**（空文字不可） |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 修正理由が空（FUNC-08） | `E_REASON_REQUIRED` |
| 400 | 修正者が空。**AI は補完しない**（②7章） | `E_RECORDER_REQUIRED` |
| 400 | 数量を訂正したが単位が無い（X11） | `E_QTY_UNIT_REQUIRED` |
| 400 | `newValue` と `newState` の**両方が無い**／値と状態が矛盾する | `E_STATE_VALUE_CONFLICT` |
| 422 | 編集対象外の項目（原表記・出典・原項番・選択グループ）（X11） | `E_FIELD_NOT_EDITABLE` |

> 訂正の記録により、版が評価確認済みだった場合は**担当者確認済みへ戻す状態イベントが同一トランザクションで積まれる**（③SCR-06「評価確認済みの後に訂正」・④3.4）。この行の `recordedBy` には**訂正者（本リクエストの `recordedBy`）をそのまま入れる**。④0.3「D層は人のみが書く」の例外ではなく、**人の訂正操作に付随して同じ人の名前で積まれるイベント**であり、AI が記録者名を作る経路にはならない（②7章）。

### 3.7 状態遷移を記録する

- **Method / Path**: `POST /versions/{versionId}/state-events`
- **目的**: 担当者確認済み・評価確認済みへ進める。**状態の真実源**
- **必要権限**: `UI` ／ **対応テーブル**: `version_state_events` / `versions.current_state` ／ **フロー**: FLOW-05 step2、FLOW-06 step4
- **スキーマ**: `schemas/state-event`

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `toState` | Yes | `staff_checked` / `review_checked`。**`draft` へは戻せない** |
| `recordedBy` | Yes | 担当者名または確認者名。空文字不可 |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 確認者名が空 | `E_RECORDER_REQUIRED` |
| 409 | 未照合の行が残っている。**未照合の行IDを返す**（③SCR-03） | `E_STAFF_CHECK_INCOMPLETE` |
| 409 | 網羅性確認が未記録 | `E_COVERAGE_NOT_RECORDED` |
| 409 | 担当者確認前に評価確認済みへ進めようとした。**同一状態への再遷移**、および本 API での `review_checked → staff_checked`（戻す経路は 3.6 の訂正に付随するイベントのみ）も同コード（Build AD-028 ③） | `E_STATE_ORDER` |
| 422 | `draft` への遷移を要求した | `E_STATE_ROLLBACK_FORBIDDEN` |

> 検査順（Build AD-028 ②）: 確認者名 → `draft` 要求 → 順序 → 未照合 → 網羅性。`E_STAFF_CHECK_INCOMPLETE` の `details` は `unmatchedItemIds`（昇順）・`unmatchedRowCodes`（同順）・`coverageRecorded`（bool。③SCR-03 が未照合と網羅性未完了を同時に表示するため同乗）。

> **未解決の確認事項が残っていてもエラーにしない。**遷移は可能で、`unresolvedCount` を記録に残す（②FUNC-07・FUNC-10）。「未解決だから止める」は要件ではない。

### 3.8 差し戻しを記録する

- **Method / Path**: `POST /versions/{versionId}/bounces`
- **目的**: 上司が再修正を求める。**状態は戻さず記録だけを残す**
- **必要権限**: `UI` ／ **対応テーブル**: `bounces` / `bounce_comments` ／ **フロー**: FLOW-06 step3
- **スキーマ**: `schemas/bounce`

#### リクエスト（Build AD-028 ⑥）

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `recordedBy` | Yes | 判断者。空文字不可 |

> 理由はリクエストで受けない。サーバが版の**未紐づけ行コメント**（#35・`bounce_id IS NULL`）を `(recordedAt, id)` 昇順に `"{rowCode}: {comment}"` を改行で連結して `bounces.reason` にし、同一トランザクションで各コメントに `bounce_id` を付与する（④§3.4）。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 確認者名が空 | `E_RECORDER_REQUIRED` |
| 409 | 行コメントが1件も無い。**理由の無い差し戻しを作らない** | `E_NO_BOUNCE_COMMENT` |
| 409 | 状態が作成案（担当者の確認が未完了） | `E_STAFF_CHECK_INCOMPLETE` |
| 409 | 状態が評価確認済み（差し戻せるのは担当者確認済みのみ。評価確認を取り消す経路が無く「差し戻し中」が意味を持たないため。Build AD-028 ⑤） | `E_STATE_ORDER` |

> **`version_state_events` に行を作らない。**差し戻しは状態ではなく記録であり、評価状態は `staff_checked` のまま（②FUNC-10・X13）。

### 3.9 送付可否を記録する

- **Method / Path**: `POST /versions/{versionId}/sendoff-decisions`
- **目的**: 対外送付の可否を記録する。**評価確認とは別の記録**
- **必要権限**: `UI` ／ **対応テーブル**: `sendoff_decisions` ／ **フロー**: FLOW-06 step5
- **スキーマ**: `schemas/sendoff-decision`

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| `decision` | Yes | `undecided` / `hold` / `approved` |
| `reason` | 条件付き | `hold` / `approved` のとき必須。**未解決を残して承認する場合も理由を残す** |
| `recordedBy` | Yes | 判断者。空文字不可 |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 保留・承認なのに理由・条件が無い（③SCR-06） | `E_SENDOFF_REASON_REQUIRED` |
| 400 | 判断者が空 | `E_RECORDER_REQUIRED` |

> **このAPIは送信を行わない。**送付可否は人の判断の記録であり、実際の送付は業務側で人が行う（①原則「AI は送信しない」）。

### 3.10 .xlsx を出力する

- **Method / Path**: `POST /versions/{versionId}/exports`
- **目的**: 記録を反映した .xlsx を書き出す。**書き出した時点の写し**
- **必要権限**: `UI` ／ **対応テーブル**: `exports`（読取は④6章の対応表） ／ **フロー**: FLOW-07
- **スキーマ**: `schemas/export`

#### レスポンス（成功 200）

| フィールド | 意味 |
|-----------|------|
| （本体） | .xlsx バイナリ。5シート（案件情報／Item List／根拠／確認事項／変更・確認記録）。`Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| ヘッダ `Content-Disposition` | `attachment; filename="{fileName}"`。`fileName` = `{案件ID}_v{版}_{評価状態}_{YYYYMMDD-HHMMSS}.xlsx`（評価状態は機械語彙 `draft`/`staff_checked`/`review_checked`、案件IDは `[A-Za-z0-9._-]` 以外を `_` に置換。ASCII 安全）。**どの記録時点の写しか判別できる** |
| ヘッダ `X-Export-Id` | 出力記録のID（#39 の行と対応） |

> 2026-09-13 Build AD-030 ㉑: 本体と JSON を 1 応答で両立できないため、`fileName`・`exportId` はヘッダで返す。リクエスト body は無い（出力は人の「記録」ではなく写しの保全）。書き出した .xlsx を読み戻す API は作らない（④§3.5）。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | 版が未確定（作成案として確定していない） | `E_VERSION_NOT_FINALIZED` |

> **未解決事項が残っていても出力できる。**件数を案件情報シートと `exports.unresolvedAtExport` に明示する（②FUNC-09）。
> **出力した .xlsx を取り込む API は定義しない**（②Out of Scope）。

## 4. .xlsx 出力の入力元（FLOW-07 の詳細）

| シート | 取得元API | 備考 |
|--------|----------|------|
| 案件情報 | 23 `GET /versions/{id}` | 状態・送付可否・未解決件数・生成所要を**出力時点の値**で確定させる |
| Item List | 24 `GET /versions/{id}/items` | **訂正適用後の現在値**。訂正前の値は出さない |
| 根拠 | 40 `GET /versions/{id}/evidence` | 原値・採用値・出典・引用。**版単位で一括取得する**（25 を行数ぶん呼ぶと12明細で12回になるため） |
| 確認事項 | 26 `GET /versions/{id}/questions` | 最新判断つき。対応状況と解決状態を別列で出す |
| 変更・確認記録 | 28 `GET /versions/{id}/records` | 訂正・確認・判断・状態・差し戻し・送付可否。記録が無ければ**列見出しのみ** |

原明細インベントリ（27）は**出力しない**（④6章）。

## 5. その他のエンドポイントの要約

3章で詳細化しなかった API。いずれも**エラーの意味論が単純**（存在しない・必須欠落・スコープ違反）なため要約に留める。

| # | エンドポイント | 主な入力 | 主な出力 | 主なエラー |
|---|--------------|---------|---------|-----------|
| 1 | `GET /cases` | — | 案件・進捗ステータス・状態・送付可否・最新の状態イベント・確認事項の残数/母数（F-15） | — |
| — | （1 の進捗ステータスの導出元） | — | ①資料投入=案件があり確定版なし ②案の確認=確定版あり ③担当者確認=`versions.current_state='staff_checked'` ④上司の評価確認=`'review_checked'`（③2章。**①②は業務状態ではなく UI の表示区分**であり状態遷移の記録対象にしない） | — |
| 2 | `POST /cases` | 案件ID・名称 | 案件 | 409 `E_DUPLICATE_CASE_CODE` |
| 4 | `GET /cases/{id}/documents` | 案件ID | 資料一覧・読取状態・ページ／シート数・受付時の読取不能範囲 | 404 |
| 5 | `POST /cases/{id}/documents` | ファイル | 受付結果・読取状態 | 413 `E_LIMIT_EXCEEDED` / 415 `E_UNSUPPORTED_FORMAT`（**投入の事実は記録したうえで 415 を返す**。②FUNC-01 X01「未対応形式でも投入の事実は資料一覧に残す」と両立させるため、`details.documentId` に作成した資料IDを入れ、④`documents` は `kind='unsupported'` / `read_status='unsupported'` で1行残る。**413 は記録を残さない**＝上限超過は受け付け自体を拒否する） |
| 6 | `GET /documents/{id}/content` | 範囲 | テキスト・セル値＋**ページごとの `readStatus`** | 409 `E_UNREADABLE`（**要求範囲が全体として読取不能のときのみ**。一部ページが読めない場合は 200 で返し当該ページを `unreadable` と示す。`agent-plan` の `read_document` が「画像のみページは `unreadable` を返す」契約であり、読めたページまで落とさない・N03） |
| 7 | `GET /documents/{id}/email` | — | ヘッダ・本文・引用部・添付一覧 | 409 `E_NOT_EMAIL` |
| 8 | `GET /cases/{id}/search` | 検索語・`limit` | 該当箇所（資料ID・位置・抜粋） | 400 `E_QUERY_REQUIRED` |
| 9 | `POST /documents/{id}/issues` | 範囲・種別・説明 | 記録 | 400 `E_DETAIL_REQUIRED` |
| 10 | `GET /documents/{id}/file` | — | 原ファイル（読取専用） | 404 |
| 11 | `GET /rule-sets/{v}` | 規則版（`current` で現行版） | R01〜R08・論理項目定義 | 404 |
| 14 | `GET /agent-runs/{id}/steps` | — | ツール呼び出しトレース | 404 |
| 14a | `GET /cases/{id}/agent-runs/active` | 案件ID | 実行中 run の ID または null | 404 |
| 15 | `POST /versions/{id}/header` | 案件情報（原文粒度） | 登録結果 | 400 `E_RAW_REQUIRED` / 409 `E_VERSION_FINALIZED` |
| 17 | `POST /versions/{id}/evidence` | `itemId`（**任意**。省略＝案件レベル）・項目・原値・採用値・出典・引用 | 登録結果 | 400 `E_SOURCE_REF_REQUIRED` / 404 `E_NOT_FOUND`（**その版に属さない行**・④原則2） / 409 `E_VERSION_FINALIZED` / 409 `E_EVIDENCE_DUPLICATE`（同一項目に2件目。行の根拠・案件レベルの根拠それぞれで1件） |
| 18 | `POST /versions/{id}/questions` | 対象・理由・候補 | 確認ID | 400 `E_TARGET_INVALID`（実在しない行） |
| 19 | `POST /versions/{id}/inventory` | 要素・状態・根拠・対応行 | 登録結果 | 400 `E_BASIS_REQUIRED`（**根拠のない除外**） |
| 22 | `GET /cases/{id}/versions` | 案件ID | 版・生成所要・状態・未解決・**引き継ぎ警告の材料**（下記4値） | 404 |
| 23〜28・40 | 各 `GET` | 版ID | 画面表示用データ | 404 |
| 30・32 | `POST .../undo` | 対象ID | 取消記録 | 409 `E_ALREADY_UNDONE` |
| 31 | `POST /versions/{id}/confirmations` | 種別・行ID・確認者 | 確認記録 | 400 `E_RECORDER_REQUIRED` / 400 `E_TARGET_INVALID` / 409 `E_ALREADY_CONFIRMED`（**未取消の確認が既にある**・④`confirmations` の部分UNIQUE） |
| 33 | `POST /versions/{id}/questions/{qid}/judgements` | 対応状況・解決状態・判断内容・判断者 | 判断記録 | 400 `E_RECORDER_REQUIRED` / 404 `E_NOT_FOUND`（**その版に属さない確認事項**・④原則2） |
| 35 | `POST /versions/{id}/bounce-comments` | 行ID・コメント・確認者 | 行コメント | 400 `E_RECORDER_REQUIRED` / 400 `E_COMMENT_REQUIRED`（コメント空・Build AD-028 ⑰）/ 404 `E_NOT_FOUND`（その版に属さない行） |
| 39 | `GET /versions/{id}/exports` | 版ID | 出力履歴・初回出力（`storage_path` / `content_hash` / 照合結果 `integrity: intact｜modified｜missing`・Build AD-030 ⑱） | 404 |

#### 22 の「引き継ぎ警告の材料」（③3章の警告文と1対1）

③ SCR-02 の警告文は「訂正 n件・照合 n/N・網羅性確認 済／未・判断 n件」を数字で示すため、22 は版ごとに次の4値を返す。**警告の文言は ③ が正**であり、22 は材料だけを返す。

| フィールド | 意味 | 導出元(④) |
|-----------|------|-----------|
| `carryOver.editCount` | 未取消の訂正の件数 | `item_edits`（`undone_at IS NULL`） |
| `carryOver.rowMatchConfirmed` / `rowMatchTotal` | 一致確認済み行数 / 明細行数（n/N） | `confirmations`（`kind='row_match'`・未取消） / `items` |
| `carryOver.coverageRecorded` | 網羅性確認の有無（済／未） | `confirmations`（`kind='coverage'`・未取消）が1件以上 |
| `carryOver.judgementCount` | 確認事項の判断が記録された確認事項の件数 | `question_judgements` を持つ `questions` の件数 |

`POST /cases/{id}/agent-runs` の `acknowledgedCarryOver`（3.1）が必須になるのは、**この4値のいずれかが0でない場合**である（X12）。

版ごとに次の導出値も返す（Build AD-029 ③〜⑤。**API が導出し UI は表示だけ**。3 画面で同じ比較を複製しない）:

| フィールド | 定義 | 導出元(④) |
|-----------|------|-----------|
| `bounced` | 最新の `bounces` 行があり、かつその後に `to_state='review_checked'` のイベントが無い | `bounces` / `version_state_events` |
| `needsRecheck` | 最新の状態イベントが `review_checked → staff_checked`（評価確認済みの後に訂正された） | `version_state_events` |
| `latestStateEvent` / `latestBounce` / `latestSendoff` | 各記録の `(recorded_at, id)` 降順先頭（無ければ null） | 各記録テーブル |

#### 28 の応答形と #34〜#37 の成功応答（Build AD-029 ⑥⑫）

28 は `{edits, confirmations, judgements, stateEvents, bounces, unlinkedComments, sendoffDecisions}` の 7 配列（取消済みを含む全行・各 `(recordedAt, id)` 昇順。`bounces[].comments` に紐づけ済み行コメントを内包、`unlinkedComments` は `bounceId` が null の行コメント）。
34〜37 は 201 で記録した行を返す（`stateEventId` / `bounceCommentId` / `bounceId` / `sendoffDecisionId` を先頭に、記録した値と `recordedAt`）。`versionId` は返さない。

## 6. エラーコード一覧

`code` の SSOT。画面の文言は ③`03-spec.md` の「エラー・例外表示」に対応させる。

| コード | 意味 | 根拠 |
|-------|------|------|
| `E_NOT_FOUND` | 対象が存在しない | — |
| `E_DUPLICATE_CASE_CODE` | 案件IDの重複 | ④`cases.case_code` UNIQUE |
| `E_LIMIT_EXCEEDED` | 入力上限超過。**具体的な超過内容を返す** | FUNC-01, D02, X09 |
| `E_UNSUPPORTED_FORMAT` | 未対応形式 | FUNC-01, X01 |
| `E_UNREADABLE` | 要求範囲が**全体として**読取不能。**読めたと扱わない**（一部ページのみ読めない場合はエラーにせずページごとの `readStatus` で示す・5章 6） | FUNC-01, N03 |
| `E_NOT_EMAIL` | .eml でない資料にメール構造を要求した | FUNC-02 |
| `E_QUERY_REQUIRED` | 検索語が空 | FUNC-04 |
| `E_NO_READABLE_DOCUMENT` | 読取成功の資料が0。**明細0件の作成案を作らない** | N03, AE05 |
| `E_CARRY_OVER_NOT_ACKNOWLEDGED` | 記録がある版の再実行で確認が無い | FUNC-10, X12 |
| `E_RUN_IN_PROGRESS` | 実行中の二重起動 | N03 |
| `E_REQUEST_INVALID` | 個別コードに該当しない入力不正（400）。camelCase規約・path/query形式違反は422。値を応答へ含めない | 0.2, 0.4 |
| `E_JOB_START_FAILED` | 予約直後のトレース保存またはジョブ投入失敗（503）。予約した実行はfailedとして保持 | 3.1, N03 |
| `E_RUN_NOT_ACTIVE` | 終了済み実行に紐づく版への遅延書込を拒否（409） | 3.3, N03 |
| `E_EXTERNAL_SEND_NOT_APPROVED` | 実モデルが構成されていません（503。`AGENT_MODE=claude` かつキー未設定） | **D05**（承認範囲は agent-plan.md 末尾） |
| `E_QTY_UNIT_REQUIRED` | 数値の数量に単位が無い | ②5章, X11 |
| `E_UNIT_REQUIRED` | 外径・肉厚・単重・定尺長に値があるのに単位が無い | R04, ④items の CHECK |
| `E_QTY_STATE_INVALID` | 未確定の状態と数値が矛盾。**TBA を 0 にしない** | ②5章, X11 |
| `E_STATE_REQUIRED` | 重要項目の状態が欠けている | 完了条件③, ④`items` の状態列 |
| `E_STATE_VALUE_CONFLICT` | 値と状態が矛盾する（値があるのに `not_stated` 等／`stated` なのに値が無い／訂正で値も状態も無い） | 完了条件③, X11, ④`items`・`item_edits` の CHECK |
| `E_SOURCE_REF_REQUIRED` | 原項番・原表記・出典が無い | FUNC-03, FUNC-07 |
| `E_GROUP_REQUIRED` | 候補区分だけで選択グループが無い | R06, R07 |
| `E_BASIS_REQUIRED` | 根拠のない除外 | FUNC-03, ③SCR-05 |
| `E_TARGET_INVALID` | 対象行が実在しない | FUNC-07 |
| `E_DETAIL_REQUIRED` | 読取不能の説明が空。**表示できない記録を残さない** | N03, ④`document_issues.detail` |
| `E_RAW_REQUIRED` | 原文の粒度が失われている（原表記なし） | R04, ②5章 |
| `E_EVIDENCE_DUPLICATE` | 同一項目に2件目の根拠を登録した | ④`evidences` の部分UNIQUE |
| `E_VERSION_FINALIZED` | 確定済みの版への書き込み | ④`versions.finalized_at` |
| `E_VERSION_NOT_FINALIZED` | 未確定の版の出力 | FUNC-09 |
| `E_VALIDATION_FAILED` | 完了条件の違反が残っている | agent-plan 完了条件 |
| `E_NO_ITEMS` | 明細0件での確定 | N03, AE05 |
| `E_REASON_REQUIRED` | 修正理由が空 | FUNC-08 |
| `E_RECORDER_REQUIRED` | 記録者名が空。**AI は補完しない** | ②7章, FUNC-08 |
| `E_FIELD_NOT_EDITABLE` | 編集対象外の項目（**422**。認可ではなく契約違反なので 403 は使わない・0.1） | X11, ③SCR-04 |
| `E_ALREADY_UNDONE` | 取消済みの記録の再取消 | ④D層 |
| `E_ALREADY_CONFIRMED` | 未取消の確認が既にある行・版への再記録 | ④`confirmations` の部分UNIQUE |
| `E_STAFF_CHECK_INCOMPLETE` | 未照合の行が残る | FUNC-08, ③SCR-03 |
| `E_COVERAGE_NOT_RECORDED` | 網羅性確認が未記録 | FUNC-08, ③SCR-05 |
| `E_STATE_ORDER` | 状態の順序違反 | FUNC-10 |
| `E_STATE_ROLLBACK_FORBIDDEN` | 作成案へ戻そうとした | FUNC-10, X13 |
| `E_NO_BOUNCE_COMMENT` | 理由の無い差し戻し | FUNC-10, ③SCR-06 |
| `E_SENDOFF_REASON_REQUIRED` | 保留・承認に理由が無い | FUNC-10, ③SCR-06 |
| `E_COMMENT_REQUIRED` | 行コメントが空（Build AD-028 ⑰） | FUNC-10, ③SCR-06 |

> **`E_NO_CHANGE` は置かない。**「現在値と同じ訂正を拒否する」は 02 の要件ではなく（FUNC-08 が求めるのは理由・記録者の必須と旧値の保持）、追記型の方針（④0.2 原則1）とも競合する。単位や状態だけを変える訂正（`newValue` が同値で `newState` や単位が変わる）を誤って弾くため、要件由来でない制約を契約に置かない。
> **エラーは業務ルールそのもの**である。上表の各行は 02 の制約・受入基準に1対1で対応しており、単体テストの根拠になる。
> **`E_CONVERSION_NOT_APPROVED` は置かない。**「換算値かどうか」はサーバから判定できないため、エラーで拒否するのではなく**換算値を渡すフィールドを持たせない**ことで D03 を担保する（3.3 の注記）。判定不能な契約をエラーコードとして残さない。

## 7. エージェントのツールと API の対応

`agent-plan.md` のツール13点と API の対応。**エージェントに登録するのはこの13本だけ**である。

| ツール | API | 副作用 |
|--------|-----|--------|
| `list_case_documents` | 4 `GET /cases/{id}/documents` | read |
| `read_document` | 6 `GET /documents/{id}/content` | read |
| `read_email` | 7 `GET /documents/{id}/email` | read |
| `search_documents` | 8 `GET /cases/{id}/search` | read |
| `get_rules` | 11 `GET /rule-sets/{v}` | read |
| `record_case_header` | 15 `POST /versions/{id}/header` | write |
| `propose_items` | 16 `POST /versions/{id}/items` | write |
| `record_evidence` | 17 `POST /versions/{id}/evidence` | write |
| `record_question` | 18 `POST /versions/{id}/questions` | write |
| `record_source_inventory` | 19 `POST /versions/{id}/inventory` | write |
| `report_unreadable` | 9 `POST /documents/{id}/issues` | write |
| `validate_draft` | 20 `GET /versions/{id}/validation` | read |
| `finalize_draft` | 21 `POST /versions/{id}/finalize` | write |

**登録しない API**（人の領域）: 29〜37（訂正・確認・判断・状態遷移・差し戻し・送付可否）、38・39・40（出力・版一括の参照）、1・2・**3**・5・10・12・13・14（案件作成・案件情報の参照・資料投入・起動・監視）。

> **3 `GET /cases/{caseId}` は `UI` 区分**である。ツール一覧に無い API を「エージェントも呼べる」と書くと、7.1 の「境界はツール登録で守る」と矛盾するため、区分を `UI` に寄せた。エージェントが案件名を必要とする場面（出典の記述など）は、**4 `GET /cases/{id}/documents` の応答に案件ID・案件名を含める**ことで満たす（`list_case_documents` の出力）。14本目のツールを増やさない。

### 7.1 この境界の限界（PoC の割り切り）

現在の設計では、**この境界を守るのはツール登録だけ**である。API 側に認可が無いため、実装の誤りでエージェントに人の記録APIを渡してしまえば、AI が確認者名を書ける状態になる。02 N02 が認証・認可を実装対象外としているための割り切りであり、次のいずれかで補強できる。

| 補強案 | 効果 | 状態 |
|--------|------|------|
| API を `/agent/*` と `/ui/*` にパス分離し、エージェント実行時のクライアントに `/ui/*` を到達不能にする | 誤登録しても届かない | **実装済み**（0.3。`backend/app/main.py` ＋ `tests/unit/test_api_path_separation.py` が検査） |
| `agent_run_steps` に**ツール一覧外の呼び出しを検知したら停止**する検査を入れる | 事後検知 | 未実施（Build で実施可能。`agent_run_steps.tool_name` が④3.2 でツール一覧に無い名前を記録しない前提と対になる） |
| API キー・ロールによる認可 | 恒久対策 | 対象外（複数利用者・本番運用時。02 N02 のスコープ外） |

**パス分離は済んでいるが、境界が破れる余地は残る**: ①`UI/AGENT` の参照系を増やしすぎると `/agent/*` 配下が広がる（新しい参照系を `AGENT` に足すときは 7章のツール13本と対応が付くかを必ず確認する）、②エージェントのツール実装がベースURLを無視して絶対URLで `/ui/*` を叩けば届く（ツール実装のレビュー観点）。この2点は build-loop の reviewer チェックリスト（`.claude/rules/clean-architecture.md`）で見る。

## 8. 未確定事項

| ID | 内容 | API への影響 |
|----|------|-------------|
| D01 | 正式なメーカー用テンプレート | 38 の出力マッピングのみ変わる。エンドポイントは変えない |
| D02 | 入力上限 | 5・12 の `E_LIMIT_EXCEEDED` の閾値。設定値であり契約は変わらない |
| D03 | 換算表・精度・丸め | 16 は**換算値を渡すフィールドを持たない**（未承認の間はスキーマレベルで排除）。承認後に `convertedValue` / `conversionNote` を追加し、`conversion_enabled = true` の規則版でのみ受け付ける（3.3） |
| D05 | 外部LLM送信 | 12 の `E_EXTERNAL_SEND_NOT_APPROVED`。**承認まで実LLMを呼ばない** |
| D06 | 強制停止閾値 | 13 の `stopReason` と `limits`。**適用した閾値は実行ごとに返す**（④`agent_runs.limits`）。閾値自体は設定値であり契約は変わらない |
| — | orval スキーマの実体 | `schemas/*` の定義は Build で作成する。本書はスキーマ名と意味のみを定める |

---

## 次のステップ

→ `/r2b:design-implementation-check` で実装設計フェーズ（agent-plan Part 2・04-db・05-api-ipo）のレビューを行う
→ `02-requirement.md` の各機能に「対応API」欄を追記する

### T-202 入出力の補足

- #16 は `{rows: [...]}`、#19 は `{entries: [...]}` を受理し、バッチは全件一括保存。失敗時は全件を保存しない。#17/#18 は1件ずつ受理する。
- `E_REQUEST_INVALID` (400): 不正な型・未定義フィールドなど、個別業務コードに該当しない入力不正。入力値そのものはエラーに含めない。camelCase規約違反・パス/クエリ形式違反は422。

- `E_JOB_START_FAILED` (503): 実行予約後のジョブ投入失敗。予約した実行はfailedに記録する。
- #14 は `{steps: [...]}`、各stepはstepId/seq/toolName/argsDigest/argsSummary/locator/documentId/resultStatus/durationMs/parentStepId。job_start/job_finishも記録し、資料全文は返さない。

- `E_RUN_NOT_ACTIVE` (409): 終了済み実行に紐づく版への遅延書込。停止後の処理が成果物を変更することを防ぐ。
- 進捗GET（#13）とstep取得（#14）は読取専用とし、DB書込・排他ロック・JSONL再構築を行わない。再実行要求時には、保存済みouterTimeoutS+完了保存猶予16秒を過ぎた実行をouter_timeoutとして回収する。一時的なDB障害で実行中が残り続けることを防ぐ。通常起動は単一サーバープロセスとし、プロセス起動時には残存runningをfailedとして回収する。

- #12の容量再確認では、原本が欠損・参照不能なら容量だけ再検査を省略する（投入時の上限検査は維持）。抽出済みdocument_pages/email_partsがあれば再利用できる。資料数・ページ数・読取可能性の検査は省略しない。
- #14の `job_start` / `job_finish` / `job_trace_failure` はジョブ管理イベントであり、AGENTのツール登録を増やさない。`job_trace_failure` は本文を含まないディスク障害記録。例外の生メッセージ・スタック・資料本文はAPI/JSONLへ出さない。
- #16の `rejected` は全件一括保存のため常に空配列。#20のcountsはitems/questions/inventoryの非負整数3項目。
