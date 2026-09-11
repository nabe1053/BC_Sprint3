# Project Memory  <!-- orchestrator 役（メインセッション）が唯一の編集責任者 -->

> 書式・ID 採番・Status 語彙・昇格ルールは `.claude/rules/memory-protocol.md` が正。
> 本プロジェクトは build-loop を使わず手動スライスループで実装する（CLAUDE.md 決定事項5）。

## 1. アーキテクチャ決定 (ADR-lite)

- [AD-001] build-loop（自律ループ）を使わず、手動スライスループで実装する。理由: スライスごとに
  内容を確認しながら進めたい / 影響範囲: memory の編集者は orchestrator 役（メインセッション）、
  レビューは reviewer サブエージェント必須（CLAUDE.md 憲法6）は維持。
- [AD-002] チケット単位は「機能グループ × 3層（BE / API / FE）」とし、**グループ内は BE → API → FE の順**で
  縦に貫く。理由: orval がバックエンドの openapi.json から生成されるため層を横断で先行させると
  手書き仮実装の作り直しが発生する / ビッグバン統合を避ける。
  影響範囲: FUNC-02〜07 は AGENT-01 1体・同一画面のため G2 に集約し、例外的に4枚（BE/API/AGENT/FE）。
- [AD-003] D02（入力上限）の**開発時仮値**を確定: 1案件あたり資料50件 / 1ファイル20MB /
  PDF 200ページ / .xlsx 50シート。理由: ②FUNC-01「上限は開発時に仮値を明示し、初版受入前に確定」。
  影響範囲: 上限は `app/core/config.py` の設定値1箇所で持ち、超過は**具体的な超過内容を返す**
  （`E_LIMIT_EXCEEDED`・X09）。**初版受入前に研修者が実値を確定すること**（§6 TODO-001）。
- [AD-004] 資料の読取ライブラリは pypdf（テキスト PDF）/ openpyxl（.xlsx・data_only）/
  標準ライブラリ email（.eml）。理由: 画像 PDF の OCR は範囲外（②FUNC-01）、マクロ・外部リンクは
  実行しない。影響範囲: openpyxl は `data_only=True` で読み、保存済み値が無いセルは
  読めた値として扱わず確認事項の材料にする。
- [AD-005] 未対応形式は **投入の事実を記録したうえで 415 `E_UNSUPPORTED_FORMAT` を返す**
  （`details.documentId` に資料IDを入れる）。上限超過の 413 は記録を残さない。理由: ②FUNC-01 X01
  「未対応形式でも投入の事実を残す」と 05-api-ipo 5章#5 の 415 契約を両立させるため。
  影響範囲: `docs/requirements/05-api-ipo.md` 5章#5 と `04-db.md` 3.1（`documents.kind` の CHECK に
  `'unsupported'` を追加・migration 540727e02dcb）を更新済み。
- [AD-006] **S/MIME 暗号化 .eml は対象外**（`encrypted` 判定を実装しない。`unreadable` + issue のまま）。
  理由: sample-01〜10 に該当が無く、②FUNC-01 の対応形式にも無い。

## 2. 確立した規約・パターン

- [CV-001] **reader（資料読取部品）の契約**: ①読取4区分は「読めた単位が1つ以上あるか」で決める
  （0 個なら `partial` ではなく `unreadable`）②例外を外へ投げず必ず `read_status` + `issues` で返す
  ③`unreadable`/`encrypted`/`unsupported`/空 のどの経路でも `ReadIssue` を1件以上残し `detail` を空にしない。
  「読めた単位」は pdf=ページ / xlsx=セル / eml=本文＋添付一覧 / text=本文（各 reader の docstring に明記）。
- [CV-002] **locator の表記体系**: `document_pages.locator` は PDF=`p.N` / xlsx=シート名 / text・eml 本文=`body:N`。
  **`document_issues.locator` を `document_pages.locator` と同値にしない**（xlsx のセル単位は `Sheet1!B1`、
  資料全体は `None`）。理由: 04-db.md の完了条件は両者を `(document_id, locator)` で差し引くため、
  同値だと範囲が丸ごと相殺され「1セルも読まずに完了」になる。
- [CV-003] **判定できない値は NULL。0 や既定値で埋めない**（`page_count` / `sent_at` / 数式セルの値）。
  「開けたか」で判定可否が決まる（開けたが中身が空、は判定できた扱い）。
- [CV-004] **入力上限は抽出の前に判定する**（形式ごとに軽量なメタデータ取得関数を用意する）。
- [CV-005] Service は ORM エンティティを生成して Repository に渡してよい。ただし
  `Session` / `select` / `commit` / SQLAlchemy の例外型を Service に持ち込まない。
- [CV-006] **Repository の例外翻訳は SQLSTATE（例 23505）か制約名で限定する。**無条件翻訳は
  誤ったエラーコードを画面に出す。
- [CV-007] 転送メールの注記（`forward_note`）は「※ で始まる行」に限って分離する。厳密な注記分離は
  FUNC-02 = AGENT-01 の責務であり reader では踏み込まない。
- [CV-008] **境界値の受入基準は「ちょうど通る」「+1 で落ちる」の2本セット**で書く（X09 型の基準）。

## 3. 実装バックログ（プラン状態＝ループの制御表）

| ID | スライス | 種別 | 依存 | Status | レビュー | 最終更新 |
|----|---------|------|------|--------|---------|---------|
| T-101 | G1 案件・資料の保存と読取処理（BE） | web | - | DONE | 3回+確認 | 2026-09-12 |
| T-102 | G1 案件・資料 API #1-10（API） | web | T-101 | PLANNED | - | 2026-09-11 |
| T-103 | G1 SCR-01 案件一覧 / SCR-02 資料投入（FE） | web | T-102 | PLANNED | - | 2026-09-11 |
| T-201 | G2 成果物の保存＋完了条件の機械判定（BE） | web | T-101 | IMPLEMENTING | - | 2026-09-12 |
| T-202 | G2 エージェント書込 API #15-21 / 起動・監視 #12-14（API・jobs 経由） | web | T-201 | PLANNED | - | 2026-09-11 |
| T-203 | G2 AGENT-01 本体（tools / ガードレール / runner） | agent | T-202 | PLANNED | - | 2026-09-11 |
| T-204 | G2 実行進捗のポーリング UI（FE） | agent | T-203 | PLANNED | - | 2026-09-11 |
| T-301 | G3 明細の現在値算出・人の記録（BE） | web | T-201 | PLANNED | - | 2026-09-11 |
| T-302 | G3 参照 #23-26 / 記録 #29-31,33（API） | web | T-301 | PLANNED | - | 2026-09-11 |
| T-303 | G3 SCR-03 Item List 確認 / SCR-04 根拠詳細（FE） | web | T-302 | PLANNED | - | 2026-09-11 |
| T-401 | G4 インベントリ・対応関係・照合集計（BE） | web | T-201 | PLANNED | - | 2026-09-11 |
| T-402 | G4 照合 API #19,27（API） | web | T-401 | PLANNED | - | 2026-09-11 |
| T-403 | G4 SCR-05 網羅性照合（FE） | web | T-402 | PLANNED | - | 2026-09-11 |
| T-501 | G5 状態遷移・差し戻し・送付可否の記録（BE） | web | T-301 | PLANNED | - | 2026-09-11 |
| T-502 | G5 承認・状態 API #22,28,34-37（API） | web | T-501 | PLANNED | - | 2026-09-11 |
| T-503 | G5 SCR-06 引合書承認（FE） | web | T-502 | PLANNED | - | 2026-09-11 |
| T-601 | G6 .xlsx 5シート生成（BE） | web | T-501 | PLANNED | - | 2026-09-11 |
| T-602 | G6 出力 API #38,39,40（API） | web | T-601 | PLANNED | - | 2026-09-11 |
| T-603 | G6 出力ボタン・版の履歴（FE・SCR-03 内） | web | T-602 | PLANNED | - | 2026-09-11 |

> 人が読む説明版: `docs/tickets.md`（グループ・完了の目安つき）。本表が進捗の正。

## 4. レビュー指摘と対応履歴

- [RV-001] T-101 1回目: 重大2（未対応形式が `E_UNSUPPORTED_FORMAT` を返さない / 転送メールの引用ヘッダ
  Date・From を破棄）+ 中9 + 軽微5 → 全件修正。設計側は 05-api-ipo.md 5章#5 を orchestrator が更新（AD-005）。
- [RV-002] T-101 2回目: 中6 + 軽微7。別セッションの reviewer からも独立に 6件（暗号化 xlsx の区分欠落 /
  シートごとに毎回ブックを開く N+1 / 上限の判定順 / 未使用 BaseRepository / README のテスト DB 手順）
  → 統合して全件修正。読取契約の非対称が原因 → **CV-001・CV-002・CV-003・CV-004 へ昇格**。
- [RV-003] T-101 3回目: 中4（xlsx の issue locator がページ locator と同値で完了条件を相殺 /
  開けなかった xlsx の `page_count=0` / 空の `latest_body` パート / Service の .eml 分岐が無テスト）+ 軽微6
  → 全件修正。`IntegrityError` の無条件翻訳は **CV-006 へ昇格**。
- [RV-004] T-101 確認レビュー: **指摘なし（DONE 可）**。109 テスト PASS。

## 5. 学び・ハマりどころ（再発防止）

- [LN-001] **reader を1つ直したら、残り3つを同じ観点で必ず見る。**3ラウンド連続で「1つだけ直して他が非対称」
  が発生した。修正時は 4 reader × 5区分の表を毎回埋めて差分を確認する。
- [LN-002] **テストの件数は層の保証にならない。**95件 PASS の時点で Service の `.eml` 分岐は1度も
  実行されていなかった。形式 × 正常/異常の分岐カバレッジを明示的に数える。
- [LN-003] サブエージェントにレビューを依頼する前に、**必ず `uv run pytest tests/ -q` の結果を添える**。
  テストと実装がずれた状態でレビューに回ると、指摘が実態と噛み合わない。
- [LN-004] Python の `cp932` は不正バイトでも私用領域にマッピングして「デコード成功」しがち。
  「どの文字コードでも読めない」テストデータには `\x81\x00` のような不正マルチバイト先頭バイトを使う。
- [LN-005] 「記録は残したうえでエラーを返す」設計（415）と「受付自体を拒否する」設計（413）は非対称。
  API 層はこの2つを別々に扱う必要がある。

## 6. 未解決 / BLOCKED / TODO

- [TODO-001] D02（入力上限）は AD-003 の**仮値**。初版受入（X09 の上限試験）の前に研修者が実値を確定する。
- [TODO-002] **eml には `document_pages` が無い**ため、04-db.md の完了条件の機械判定
  （`document_pages` − `document_issues` を `(document_id, locator)` で差し引く）が eml に適用できない。
  `email_parts` の `part_role`/`seq` 単位で判定するのか、設計側の方針を **T-201（完了条件の機械判定）の前に**決める。
- [TODO-003] `document_issues.issue_type` の語彙（特に `reference_missing` / `not_scanned`）の
  意味づけが 04-db.md に無い。T-101 では「付随情報の欠落（引用元の日付が解釈できない等）」に
  `reference_missing` を割り当てた。設計書に用語定義を追記するとよい。
