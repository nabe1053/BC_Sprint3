# T-601 作業指示書（orchestrator → Codex）— 2026-09-13

対象スライス: **T-601【BE】G6 .xlsx 5 シート生成**（memory §3・依存 **T-501 DONE**。`docs/t501-handoff.md` の「T-502 へ渡す契約」節で `record()` の `yield version` / `list_records` / `unresolved_count` の実型を確認してから着手し、差があれば handoff 冒頭に書く）。T-502（API）が並行のときは **`app/api/**`・`frontend/` を触らない**（CV-023。commit は pathspec）。handoff 冒頭に触るファイル一覧を先に書く（CODEX-INSTRUCTIONS §5）。
設計の正: 04-db.md §3.5 `exports`・§3.6 導出値・6 章 出力対応表（AD-030 で追記済み）・7 章 D03／05-api-ipo.md FLOW-07・3.10（AD-030 で応答形確定済み）・4 章「.xlsx 出力の入力元」・#38/#39/#40／02-requirement.md FUNC-09・5 章 出力データ・6 章 R04・7 章／03-spec.md SCR-03「現在の記録を出力」「版の履歴」・エラー表／06-scenario-test.md TEST-15・X07・X08・AE03。
前提事実（確認済み）: `openpyxl>=3.1.5` は `backend/pyproject.toml` に既存（追加不要）／`exports` は ORM・migration とも未作成／`agent_runs.version_id`（UNIQUE FK）は既存で `elapsed_sec` と版は DB 上で結線済み／`DocumentStorageGateway` は `storage_root` 注入可・`backend/storage/` は .gitignore 済み。

## 0. orchestrator 決定（AD-030・確定。蒸し返さない）

| # | 事項 | 決定 |
|---|---|---|
| ① | ライブラリ | **openpyxl（既存依存）**。通常モード（`write_only` 不可: セル型の後付けができない）。他ライブラリを足さない |
| ② | シート名・順序 | `SHEET_NAMES = ("案件情報", "Item List", "根拠", "確認事項", "変更・確認記録")` を **`app/domain/export_types.py` の 1 定数**に置き、ビルダ・テスト・T-602 が import（CV-015）。原明細インベントリは出力しない |
| ③ | 換算禁止（D03）の担保 | **ビルダは snapshot の列を写すだけ**。四則演算・単位変換・丸めを書かない。構造で固定: (a) 出力される数値セルの集合 ⊆ snapshot に存在する `Decimal` 値の集合（集合包含・LN-059）(b) `export_workbook.py` / `export_types.py` / `export_service.py` に `float(` / `round(` 0 件（SSOT テスト）(c) `evidences.conversion_note` は写すだけ |
| ④ | ファイル保存先 | **ディスク**: `{EXPORT_ROOT}/{caseId}/{uuid4}.xlsx`（`settings.EXPORT_ROOT` 既定 `storage/exports`）。書込・パス検証は **`DocumentStorageGateway(storage_root=settings.EXPORT_ROOT)` を再利用**（元ファイル名をパスに入れない・AD-007 と同型・CV-015）。DB bytea は採らない |
| ⑤ | `exports` 行の内容 | `file_name`（⑨）/ `storage_path` / `content_hash`=保存バイト列の sha256 hex / `exported_at`=サーバ採時（CV-009）/ `state_at_export`=ロック下の `versions.current_state` / `sendoff_at_export`=最新 `sendoff_decisions.decision`（無ければ `'undecided'`）/ `unresolved_at_export`=`version_state.unresolved_count()`（T-501 の純粋関数を import）/ `is_initial`=その版の exports 行が 0 件のとき true |
| ⑥ | 記録者 | **`exports` に記録者列を持たない（04-db どおり）**。E 層は写しの保全記録で D 層の「人の記録」ではない。#38 はリクエスト body を持たない。`exported_by` 追加は研修者判断（TODO-038） |
| ⑦ | スナップショットの一貫性 | **版行 `FOR UPDATE` の下で全データを読み、同一トランザクションで exports 行を INSERT**（D 層の全書込が同じロックを取るため出力中に訂正・遷移が混ざらない。CV-024 で 2 セッション観測）。Item List は `apply_edits`（`item_current_values.py`）で未取消訂正を適用した現在値。旧値は「変更・確認記録」のみ |
| ⑧ | 未確定版 | `finalized_at IS NULL` → **`E_VERSION_NOT_FINALIZED`**（05 #38 409）。存在しない版は `E_NOT_FOUND`。`RecordRepository.version()` は未確定を `E_NOT_FOUND` にするため **`ExportRepository.lock_version()` を別に持つ**（両コードを区別するテスト 2 本）。`errors.py` への追加は T-602 |
| ⑨ | ファイル名 | 純粋関数 `export_file_name(case_code, version_no, state, exported_at)` → `{case_code_safe}_v{version_no}_{state}_{YYYYMMDD-HHMMSS}.xlsx`。`state` は**機械語彙**（`draft`/`staff_checked`/`review_checked`。ASCII 安全・Content-Disposition）。`case_code_safe` は `[A-Za-z0-9._-]` 以外を `_`（空になれば `case{case_id}`）。時刻は ⑪ の JST |
| ⑩ | 決定性 | **`build_workbook(snapshot, exported_at) -> bytes` の純粋関数**（時計・DB・設定を読まない）。バイト同一は保証しない（zip エントリ時刻）→ テストは「同入力 2 回 → 全シートのセル `(coordinate, value, data_type)` が同一」。`wb.properties.creator="OCTG Item List Agent"`・`created=modified=exported_at`（naive UTC） |
| ⑪ | timestamptz の書式 | **文字列セル**。`format_ts(dt)` 1 関数: `dt.astimezone(ZoneInfo("Asia/Tokyo")).isoformat(sep=" ", timespec="seconds")` → `2026-09-13 14:03:05+09:00`。`DISPLAY_TZ` は `export_types.py` の 1 定数。None は空セル。（TODO-030 ⑥ の日時書式をこれで確定。FE 追従は C-3） |
| ⑫ | 数値セル | `*_value`（`Decimal`）は **`Decimal` のまま `cell.value`**（float 経由の丸め無し）。`data_type=="n"`。隣に `*_raw` 列を必ず置く。`float()` 禁止（③b） |
| ⑬ | 数式化防止（N05・X08） | **全文字列は `write_text(cell, value)` 1 関数経由**で `cell.data_type = "s"` に固定（先頭 `=` を数式にしない）。読み戻しで全セル `data_type != "f"` を assert |
| ⑭ | 状態・語彙のラベル | 04-db 語彙 → 日本語ラベルの辞書を `export_types.py` に 1 つずつ（`ITEM_STATE_LABELS` / `VERSION_STATE_LABELS` / `SENDOFF_LABELS` / `RESOLUTION_LABELS` / `STATUS_LABELS` / `CATEGORY_LABELS`）。辞書のキー集合 == 対応 `Literal` の値集合をテストで固定（LN-052）。色・塗りは使わない |
| ⑮ | 「変更・確認記録」の粒度 | **1 記録 = 1 行の単一表**。取消は別行にせず `取消者`/`取消日時` 列。対象: `item_edits` / `confirmations` / `question_judgements` 全履歴 / `version_state_events` / `bounces`＋`bounce_comments` / `sendoff_decisions`（T-501 `list_records` の 7 配列が材料）。並び `(recorded_at, 種別順, id)` 昇順。0 件なら見出し行のみ |
| ⑯ | 生成所要 | **案件情報シートに書く**（`AgentRun.version_id == version.id` の `elapsed_sec`。NULL なら「未記録」）。#22/#23 への API 露出は T-603（TODO-037 文言修正済み） |
| ⑰ | 案件情報シートの「資料一覧」 | 同シート下部に **第 2 表**（見出し「資料一覧」）: `documents` 案件全件・`(received_at, id)` 昇順: 資料名／形式／読取状態／受付日時／ページ数 |
| ⑱ | 初回出力の保全確認（#39 材料） | `ExportService.list_exports(version_id)` は全行に **`integrity: Literal["intact","modified","missing"]`** を付ける（`resolve_readable_path` None → `missing`、sha256 不一致 → `modified`） |
| ⑲ | 置き場 | `app/domain/export_types.py` / `app/services/export_workbook.py`（純粋ビルダ。import は openpyxl・domain・`item_current_values` のみ）/ `app/services/export_service.py` / `app/repositories/export_repository.py` / `app/models/exports.py` / migration `alembic/versions/export_records.py`（CV-017） |
| ⑳ | ファイル書込と DB の順序 | ロック下で snapshot → bytes → sha256 → `storage.save` → exports INSERT → commit。INSERT 失敗時は保存ファイルを `os.remove`（best effort・失敗はログのみ） |
| ㉑ | #38 の応答形（T-602 向けに先決め） | **200 バイナリ＋`Content-Disposition: attachment; filename="{file_name}"`＋ヘッダ `X-Export-Id`**（05 3.10 書き戻し済み）。読み戻し API は作らない（04-db §3.5）。T-601 は `ExportResult(record, content)` を分けて返す |

## 1. 範囲と範囲外

**範囲（BE のみ・endpoint 無し）**: ①domain: `ExportSnapshot`（`case`, `version`, `header`, `documents`, `items: list[ItemRow]`（現在値＋`ends`＋`row_match`＋`edit_count`）, `evidences`, `questions`（最新判断つき）, `records`（T-501 7 配列）, `elapsed_sec`, `rule_version`, `conversion_enabled`, `unresolved_count`, `matched_count`, `coverage_confirmed`）/ `ExportResult` / `SHEET_NAMES` / `*_LABELS` / `DISPLAY_TZ` ②純粋関数: `build_workbook`・5 つの `build_*_sheet(ws, snapshot, exported_at)`・`write_text`・`format_ts`・`export_file_name`・`sha256_hex` ③`ExportRepository`: `lock_version` / `snapshot` / `count_exports` / `save_export` / `list_exports` / `list_evidence`（版一括・#40 の材料）④`ExportService`: `export(version_id) -> ExportResult` / `list_exports(version_id)` ⑤ORM `Export`＋`models/__init__.py`＋migration ⑥`settings.EXPORT_ROOT` ⑦fixtures `tests/fixtures/export_data.py` ⑧SSOT テスト追記。
**範囲外**: API endpoint・DTO・`errors.py`・OpenAPI・orval（T-602）、SCR-03 の出力ボタン・版の履歴（T-603）、`frontend/`、`app/agent/**`（ツール 13 本・`AGENT_TOOL_NAMES` 不変）、T-501 の仕様変更（利用のみ）、`route_contract.py`・`test_api_path_separation.py`、`docs/requirements/*`（orchestrator が反映済み）。**`backend/openapi.json` 不変**（`make check-be` のみ）。

## 2. シート仕様（列は左から。見出しは定数タプルで持ち、テストは見出し行の完全一致を assert）

| シート | 列（見出し） | 出典 |
|---|---|---|
| 案件情報（第 1 表: `項目 / 値 / 状態`） | 案件ID・版・作成日時（`finalized_at`）・一部未完了（あり／なし）・評価状態・送付可否・送付可否の理由・未解決件数・一致確認（`n/N`）・網羅性確認（済／未）・訂正件数（未取消）・生成所要（秒）・規則版・換算（「無効（D03 未承認）」固定）・照会番号・客先名・要求納期（原文）・要求納期の粒度・納期基準・納地（原文）・受渡条件・見積期限（原文）・見積期限（日時）・見積期限 TZ・出力日時・注記 3 行（「サンプル用の簡略書式（D01）」「.xlsx は書き出した時点の写し。編集内容はアプリに取り込まれません」「未承認の換算は行いません」） | `cases` / `versions` / `case_headers`（`*_state` は状態列にラベル）/ 最新 `sendoff_decisions` / `rule_sets` / `agent_runs.elapsed_sec` / 未取消 `confirmations` / `item_edits` |
| 案件情報（第 2 表「資料一覧」） | 資料名 / 形式 / 読取状態 / 受付日時 / ページ数 | `documents` |
| Item List | 行ID / 原項番 / 品種 / 原品名 / 用途 / 外径 / 外径単位 / 外径原表記 / 外径状態 / 肉厚 / 肉厚単位 / 肉厚原表記 / 肉厚状態 / 単重 / 単重単位 / 単重原表記 / 単重状態 / グレード / グレード原表記 / グレード状態 / 接続 / 接続原表記 / 接続状態 / レンジ / 定尺長 / 定尺長単位 / 定尺長原表記 / レンジ・定尺長状態 / 数量 / 数量単位 / 数量原表記 / 数量状態 / 数量参考注記 / 要求納期（原文） / 要求納期状態 / 納地（原文） / 納地状態 / 備考 / 選択グループ / 候補区分 / 継承候補 / 両端A 外径 / 両端A 単位 / 両端A 原表記 / 両端A 接続 / 両端A BOX・PIN / 両端B（同 5 列） / 一致確認 / 確認者 / 確認日時 / 訂正件数 | `items`＋`apply_edits` / `item_ends`（`side`）/ 未取消 `row_match`。並び `(seq, id)`。**合計・小計行を作らない**（R07） |
| 根拠 | 行ID（案件レベルは「案件」）/ 項目名 / 原値 / 採用値 / 資料名 / 位置 / 引用 / 共通条件・個別例外 / 換算条件 / 変更の採用理由 / 資料上の変更前値 | `evidences` JOIN `documents.file_name`。並び: 案件レベル（`id`）→ 行（item `seq`, `evidence.id`） |
| 確認事項 | 確認ID / 行ID（案件レベルは「案件」）/ 対象項目 / 区分 / 理由 / 候補・不足条件 / 対応状況 / 解決状態 / 判断内容 / 判断者 / 判断日時 | `questions`＋最新 `question_judgements`（無ければ 未対応／未解決・他は空）。並び `question.id` |
| 変更・確認記録 | 種別 / 行ID / 項目 / 変更前の値 / 変更前の状態 / 変更後の値 / 変更後の状態 / 理由・内容 / 補足 / 記録者 / 記録日時 / 取消者 / 取消日時 | ⑮。種別ラベル: 訂正／一致確認／網羅性確認／判断／状態遷移／差し戻し／差し戻しコメント／送付可否。補足: 状態遷移=`{from}→{to}（未解決 n 件）`・判断=`{status}/{resolution}`・送付可否=decision ラベル・差し戻しコメント=紐づけ有無 |

共通: 文字列は `write_text`（⑬）、`Decimal` は ⑫、日時は ⑪、None は空セル、状態は ⑭。**セル書式・塗り・条件付き書式・数式・ハイパーリンクを使わない。**

## 3. 実装順序と RED→GREEN（層順・下位は mock。純粋ビルダは bytes を openpyxl で読み戻して検証）

| 順 | 成果物 | RED（先に書く） | 置き場 |
|---|---|---|---|
| 1 | `export_types.py`＋`export_file_name`・`format_ts` | `SHEET_NAMES` 5 個・順序固定 / ラベル辞書キー集合 == `Literal` 値集合 / `format_ts` が `+09:00` 秒精度・None→"" / `export_file_name("S-01/α", 2, "staff_checked", ts)` == `S-01__v2_staff_checked_20260913-140305.xlsx`、空 code → `case{id}` | `tests/unit/test_export_types.py` |
| 2 | `export_workbook.py` 純粋ビルダ | fixtures snapshot（2 明細・両端あり 1・訂正 1・案件レベル根拠 1・未解決 1・記録 7 種）で: ①`sheetnames == list(SHEET_NAMES)` ②各シート 1 行目が見出しタプルと完全一致 ③外径セル `data_type=="n"` かつ `Decimal(str(v)) == Decimal("13.375")`・隣の原表記 `13-3/8"` ④**D03**: 全数値セルの集合 ⊆ snapshot の `Decimal` 集合（AE03 型: `od 339.7 mm`・`qty 118 t` だけの snapshot で 13.375 や本数相当が 1 つも現れない。集合差 `== set()`）⑤**N05**: `=HYPERLINK(...)`・`=1+1`・`+1`・`-1`・`@SUM` を note/quote/comment に入れる → 全セル `data_type != "f"`・値そのまま ⑥訂正適用: K55→L80 で Item List は L80 のみ・K55 は「変更・確認記録」の変更前列のみ ⑦記録 0 件 → 見出し行のみ ⑧未解決 n → 「未解決件数」== n ⑨送付可否なし → 「未判断」、draft → 「作成案」⑩**X07**: 別案件 snapshot B の固有値集合 ∩ A の全文字列セル集合 `== set()` ⑪決定性: 同入力 2 回で `(coordinate, value, data_type)` 同一 ⑫塗り・数式・条件付き書式 0 ⑬第 2 表の資料名が `received_at` 順 ⑭生成所要 None → 「未記録」 | `tests/unit/test_export_workbook.py` |
| 3 | ORM `models/exports.py`＋migration | **実 DB**: `state_at_export='pending'` 23514 / `sendoff_at_export='yes'` 23514 / `unresolved_at_export=-1` 23514 / 空 `file_name`・`storage_path`・`content_hash` 23514 / 同一版に `is_initial=true` 2 行目 23505（部分 UNIQUE）/ `is_initial=false` は複数可 | `tests/integration/test_export_schema.py` |
| 4 | `ExportRepository` | 実 DB（`seed_export_version`）: `snapshot()` の各集合が seed と一致（items 順・evidences の `file_name` JOIN・`records` 7 キー）/ 未確定版 `lock_version` → `E_VERSION_NOT_FINALIZED`、存在しない → `E_NOT_FOUND` / `count_exports` 0→1 / `list_exports` `(exported_at, id)` 昇順 / **2 セッション（CV-024）**: A が `lock_version` 保持中に B が `RecordService.edit` → `pg_blocking_pids` で block 観測 → A commit 後 B 成功、A の snapshot に B の訂正が無い / クエリ数が items 数に依存しない（N=2 と N=12 で同数） | `tests/integration/test_export_repository.py` |
| 5 | `ExportService.export` / `list_exports` | Repository・storage mock: `lock_version` 後に `snapshot` が同ロック内 / `exported_at` サーバ採時・snapshot と exports 行で同一 / `content_hash == sha256(storage に渡した bytes)` / `storage.save(case_id, "*.xlsx", bytes)` / `count_exports==0` → `is_initial=True`、`==1` → False / `state_at_export`・`sendoff_at_export`（無し → `undecided`）・`unresolved_at_export` が snapshot の値 / `save_export` 例外 → remove 呼出・例外再送出 / `list_exports`: `tmp_path` に実ファイルで `intact`、1 バイト変更 `modified`、削除 `missing` | `tests/unit/test_export_service.py` |
| 6 | `settings.EXPORT_ROOT`＋gateway 再利用 | `DocumentStorageGateway(storage_root=settings.EXPORT_ROOT).save(7, "x.xlsx", b)` → `storage/exports/7/<uuid>.xlsx` 形 | `tests/unit/test_document_storage.py`（追記） |
| 7 | SSOT 追記 | 3 ファイルに `float(`・`round(` 0 件 / `"変更・確認記録"` リテラルが `export_types.py` 以外の `app/**` に無い / `unresolved_count` の再定義が無い | `tests/unit/test_single_source_of_truth.py`（追記） |
| 8 | fixtures | `snapshot(**overrides)`・`seed_export_version(session)`（T-501 の `seed_record_version` を呼んで拡張。CV-021） | `tests/fixtures/export_data.py` |
| 9 | 統合 1 本（実配線・実 DB・`tmp_path` root） | `ExportService(ExportRepository(session), DocumentStorageGateway(tmp_path)).export(vid)` → ファイル存在・sha256 一致・`is_initial` true → 2 回目 false → 保存ファイルを開き 5 シート・Item List 行数 == items 数 → 未確定版 `E_VERSION_NOT_FINALIZED` | `tests/integration/test_export_repository.py`（末尾） |

- 変異 1 行: `write_text` の `data_type="s"` を消す → 順 2 ⑤／外径セルを `float(value)` に → 順 7（SSOT が主検出である旨を handoff に）／`is_initial=True` 固定 → 順 5 と順 3 の部分 UNIQUE
- 既存テストを消さない・弱めない。`seed_record_version` を変更するなら理由を handoff に

## 4. migration（新規・必須）

- `revision="export_records"`, `down_revision="approval_records"`（着手時 `alembic heads` 単一を確認。T-501 未適用なら着手しない）。適用済みリビジョンを編集しない（LN-018）
- `exports`: `id bigserial PK` / `created_at`・`updated_at`（`TimestampedBase`。`RecordedBase` は使わない・⑥）/ `version_id bigint NOT NULL FK versions`（索引 `ix_exports_version_id`）/ `file_name text NOT NULL` / `storage_path text NOT NULL` / `content_hash text NOT NULL` / `exported_at timestamptz NOT NULL` / `state_at_export text NOT NULL` / `sendoff_at_export text NOT NULL` / `unresolved_at_export integer NOT NULL` / `is_initial boolean NOT NULL DEFAULT false`
- 制約（ORM `__table_args__` と同名）: `ck_exports_state_at_export IN ('draft','staff_checked','review_checked')` / `ck_exports_sendoff_at_export IN ('undecided','hold','approved')` / `ck_exports_unresolved_nonneg (unresolved_at_export >= 0)` / `ck_exports_file_name`・`ck_exports_storage_path`・`ck_exports_content_hash`（`trim(...) <> ''`）/ **部分 UNIQUE `uq_exports_initial_per_version (version_id) WHERE is_initial`**
- UPDATE・DELETE 経路を作らない。`downgrade` は drop。両 DB の `\d exports`（LN-018/026）

## 5. 完了条件

- `DEBUG=false CI=true make check-be` all green（基準: T-501 DONE 時の実測＋新規 → 実測を handoff に。CV-016）。T-502 が並行なら pytest の時間帯を分ける（LN-027・CV-023）
- 両 DB に migration 適用済み・`\d exports`・`alembic heads` 単一
- `backend/openapi.json` 不変／`app/api/**`・`app/agent/**`・`frontend/src` に diff なし／`pyproject.toml` に依存追加なし
- `docs/t601-handoff.md`: 冒頭に触ったファイル一覧 → T-501 契約との差分 → §0 ①〜㉑ の反映箇所（file:line）→ レビュー対応表（項目／file:line／RED テスト名・コマンド・件数／変異 1 行）→ 既存テスト変更の理由 → `\d exports`・`make check-be` 実出力 → **「T-602 へ渡す契約」節**（下記）→ 末尾見出し **`## 再レビュー依頼（T-601）`**（本文中でこの語を使わない・LN-033）。commit は Claude

### 「T-602 へ渡す契約」節に書くこと
- `ExportService.export(version_id) -> ExportResult(record: Export, content: bytes)` と `list_exports(version_id) -> list[ExportWithIntegrity]` の属性一覧（`export_id`・`file_name`・`storage_path`・`content_hash`・`exported_at`・`state_at_export`・`sendoff_at_export`・`unresolved_at_export`・`is_initial`・`integrity`）
- DI: `ExportService(ExportRepository(session), DocumentStorageGateway(storage_root=settings.EXPORT_ROOT))`
- 新コードと推奨 HTTP: `E_VERSION_NOT_FINALIZED` 409（既存なら「既存」と明記）
- `ExportRepository.list_evidence(version_id)` が **#40 の材料**（`file_name` JOIN 済み・案件レベル→行の順）
- #38 は ㉑（200 バイナリ＋`Content-Disposition`＋`X-Export-Id`）。`file_name` は ASCII 安全
- `SHEET_NAMES`・ラベル辞書は `app/domain/export_types.py` から import（FE i18n との一致は T-603）
