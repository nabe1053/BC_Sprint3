# Codex セッション作業規約（2026-09-14 改訂・研修者決定＝Codex 単独運用へ移行）

**2026-09-14 より Claude メインセッションは退く（トークン枯渇）。以後は Codex だけで回す。**
Claude が持っていた 4 つの権限（memory 編集・レビュー起動・品質ゲート・commit）は、
下記 §0 のとおり **Codex のフェーズ（実装／レビュー／転記）** に移譲する。
この文書が Codex 側の恒久ルール。着手前に必ず読むこと。

> 移行前の記述（「Claude が〜する」）は §0 と §0c を正として読み替える。
> 判断に迷ったら設計書（`docs/requirements/`）→ `.claude/memory.md` → 本ファイルの順に正。

---

## 0. 役割分担（これを崩さない）

**役割は「人」ではなく「セッション（フェーズ）」に付く。**1 スライスを 3 つのセッションで回す。

| フェーズ | セッション | やること | やらないこと |
|---|---|---|---|
| **A 実装** | 実装セッション | 指示書 §0 の決定に従い RED → 実装 → REFACTOR、handoff の更新 | `.claude/memory.md` の編集、自分の差分のレビュー、commit、指示書の決定の変更 |
| **B レビュー** | **新しい Codex セッション（フレッシュ文脈）** | §0d の手順で独立レビュー、指摘を handoff に書く | 実装（1 行も直さない）、memory の編集、commit |
| **C 転記・確定** | 転記セッション（A を再開してよい） | 指摘の修正 → 再レビュー（B をもう一度）→ memory 転記 → `make check` → commit → §7 更新 | 未レビューのまま commit |

- **自分が書いたコードを自分でレビューしない（CLAUDE.md 憲法6）。**単独運用での「別エージェント」とは
  **実装の会話を引き継がない新しいセッション**を指す。同じセッションの続きで自分の差分を見て
  「レビューした」ことにしない。理由: 実装時の前提をそのまま正しいと見なす誤りが検出できない。
- **`.claude/memory.md` を編集できるのはフェーズ C のセッションだけ。**A・B は読むだけ。
  進捗・決定・学び・希望 Status はまず `docs/t{ID}-handoff.md` に書き、C でまとめて 1 回転記する。
  理由: 同時追記で RV/LN の ID 衝突と Status 上書きが実際に起きた（memory §6 TODO-004）。
- **並行セッションを走らせない（WIP=1・§2）。**転記中に別スライスの実装を始めない。

---

## 0b. 単独運用の周回（2026-09-14 改定・旧「常駐ループ」を置換）

Codex はこの 1 周を単位に動く。研修者の中継を待つのは **§0e の「研修者に上げること」だけ**。

```
1. .claude/memory.md（§3 バックログ・§6 未解決）と §7「次にやること」を読む
2. §7 の最優先スライスを 1 つ選ぶ（WIP=1）。指示書 docs/t{ID}-instructions.md があればそれが正。
   無ければ §0c の手順で自分で指示書を書く（決定表つき）
3. 【A 実装】RED → 実装 → REFACTOR。handoff に「レビュー対応」表（§6）を書く
4. make check（BE のみなら check-be / FE のみなら check-fe）green を handoff に実出力で貼る
5. 【B レビュー】新しいセッションを開き §0d のプロンプトでレビュー。指摘を handoff に追記
6. 指摘を修正 → B をもう一度（指摘ゼロになるまで。3 回超過は BLOCKED として memory §6 へ）
7. 【C 転記】memory 転記（§1 決定 / §4 指摘 RV / §5 学び LN / §3 Status=DONE）→ make check →
   commit（§6b の手順・pathspec 限定）→ §7 を次スライスに書き換える
8. 1 へ戻る。§0e に当たったら §7 に「研修者確認待ち: <論点>」と書いて別スライスへ移る
```

- **§7 は自分のキューになった。**Claude の更新を待たない。1 周ごとに自分で書き換える。
- 1 周が長くなりすぎるときはスライスを割る（半日で回らない粒度にしない）。

## 0c. 指示書が無いスライスの進め方（T-602 / T-603 以降）

指示書（`docs/t{ID}-instructions.md`）は **実装の前に必ず書く**。いきなりコードを書かない。
既存の `docs/t501-instructions.md` / `t502` / `t601` / `t503` が雛形。構成は固定:

```
対象スライス・依存・設計の正（file:line で列挙）
§0 決定表（未決を 1 行 1 件。決めたものは「確定」、決められないものは「研修者確認待ち」）
§1 範囲と範囲外    §2 DTO / API / シート等の契約    §3 エラー・語彙
§4 実装順序と RED→GREEN（テストファイル名まで）    §5 完了条件（make check・handoff 見出し）
§6 設計書との齟齬（書き戻しが要る箇所）
```

- **決定表を埋めずに実装に入らない。**「実装しながら決める」と設計書と乖離し、後で全部やり直しになる
  （memory LN-012・T-302 の教訓）。
- 設計書（01〜06・agent-plan.md）に無いものを足さない。足す必要が出たら**先に設計書を直す**
  （`.claude/rules/agent-development.md` §1）。設計書の改定は §0e の研修者判断。
- 決定を確定したら `.claude/memory.md` §1 に **AD-0xx** として 1 件記録し、指示書 §0 から参照する
  （既存の AD-028〜AD-031 と同じ書式）。採番は既存の最大値 +1。

## 0d. レビュー・プロトコル（憲法6 を単独運用で満たす）

**新しい Codex セッション**を開き、次をそのまま渡す。実装セッションの会話を引き継がない。

```
T-xxx を独立レビューしてください。あなたは実装者ではありません。コードを 1 行も書き換えないでください。
入力: docs/txxx-instructions.md（§0 の決定は所与。蒸し返さない）、docs/txxx-handoff.md（実装者の主張）、
      設計の正（指示書が挙げている docs/requirements/... の該当箇所）、
      .claude/rules/clean-architecture.md の reviewer チェックリスト、
      UI を含むなら .claude/rules/design-guidelines.md の reviewer チェックリスト、
      .claude/memory.md（読むだけ。§2 の CV は既に守られている前提で検査する）
対象: git status --short と git diff の範囲だけ
観点: ①指示書 §0 の決定が全件反映されているか（1 件ずつ file:line で確認）
      ②クリーンアーキの依存方向（内側が外側を import していないか）
      ③TDD: RED の記載が妥当か／既存テストの削除・弱化が無いか／assert が実応答を見ているか
      ④handoff の数値（テスト件数・ゲート結果）が自分の手元で再現するか（make check を 1 回実行する）
      ⑤秘密・個人情報がトレース/ログ/応答に漏れていないか
出力: P1（DONE 不可）/ P2（要修正）/ P3（記録のみ）を file:line つきで。最後に DONE 可否を 1 行。
      先頭に memory §4 へ貼る 3 行要約を「RV 候補」として付ける。
```

- レビューセッションは**実装しない**。指摘だけ返し、修正は実装セッション側で行う。
- 「handoff にそう書いてあるから正しい」としない。**数値は自分で再現する**（§6 の最低要件）。
- 指摘ゼロで初めて DONE。3 回直しても残るなら BLOCKED（memory §6 に BLK として記録）。

## 0e. 研修者に上げること（Codex が単独で決めてはいけないこと）

次に当たったら §7 に「研修者確認待ち: <論点>」と書き、**そのスライスを止めて別スライスへ移る**。

1. **設計判断**: 設計書（01〜06・agent-plan.md）の要件・データモデル・API 契約を変える判断
2. **破壊的操作**: `rm -rf`、DB の drop/truncate、migration の巻き戻し、git の履歴書き換え
3. **外部送信（D05）**: 実 LLM への送信範囲を広げること（現在の承認は `references/sample-01`〜`10` のみ。
   `references/proposal.pptx`・実業務資料・認証情報は送らない）
4. **スコープ変更**: バックログにないスライスの追加、既存スライスの範囲拡大
5. **BLOCKED 化**: レビュー 3 回超過、または依存が解けないとき
6. **秘密情報**: `backend/.env` の中身を読む・表示する・コミットすることは**常に禁止**
   （存在確認は行数の grep まで）。鍵が要る作業は研修者に依頼する

## 1. 品質ゲートは `make check`（2026-09-12 新設）

**リポジトリ直下の `Makefile` が検証の単一入口。**個別コマンドを手で組み立てない。

```sh
make check-be   # BE だけ触ったスライス（db 起動 → migration → ruff → pytest 全体）
make check-fe   # FE だけ触ったスライス（openapi → orval → tsc → eslint → jest）
make check      # スライス完了時のフルゲート
```

守ること:

- **`--confcutdir` や専用 tsconfig で範囲を切った実行を「検証した」と呼ばない。**
  切り出し実行は作業中の高速フィードバック用。**再レビュー依頼の根拠には `make check` の出力を貼る。**
- **ORM に列を足したら、同じ手順の中で `make migrate` を実行する。**
  `tests/conftest.py` が `Base.metadata` で TRUNCATE するため、モデルだけ先行すると
  無関係な既存統合テストが全滅する（memory LN-013）。
- **migration は開発 DB（octg_db）にも適用する。**統合テストは `TestClient` の lifespan で
  アプリ本体のエンジン（`settings.DATABASE_URL` = octg_db）に触るため、開発 DB のスキーマが
  古いと `tests/integration` が全滅する。`make migrate` は両方に適用する（memory LN-017）。
- 全体回帰を「保留」にしない。保留した結果、4回目のレビューで 44 ERROR が出た（RV-015 P1-1）。

---

## 2. WIP は 1（同時に触るスライスは1つ）

- 着手中のスライスを閉じるまで次に進まない。「A の指摘修正中に B を実装」をしない。
- 例外: Claude が **明示的に並行スライスを指示した場合のみ**（§5）。
- 1スライスの終わり = `make check` green ＋ handoff 更新 ＋「再レビュー依頼」の記入。そこで**止まる**。

---

## 3. ファイル配置の規約（チケット名をファイル名に入れない）

`routes_t202.py` のようなチケット名つきファイルは、チケットが閉じた瞬間に意味を失い、
次のスライスがどこに書けばいいか分からなくなる。**以後、新規ファイルにチケット ID を含めない。**

正の配置（既存の T-101/T-102 の構造に合わせる）:

| 種類 | 置き場 |
|------|--------|
| AGENT 名前空間のエンドポイント | `app/api/agent/endpoints/{資源}.py` |
| UI 名前空間のエンドポイント | `app/api/ui/endpoints/{資源}.py` |
| 名前空間ごとの DTO | `app/api/{agent,ui}/schemas/{資源}.py` |
| 両名前空間で共有する DTO / ハンドラ | `app/api/common/` |
| 横断の DI・lifespan | `app/api/dependencies.py` |

### 着手タスク C-1（**完了・2026-09-12 RV-026。以下は履歴**）

以下をリネーム＋import 追従する。**振る舞いを変えない**（純粋な移動。`make check` が green のままであること）。

```
app/api/routes_t202.py        → app/api/common/route_errors.py
app/api/dependencies_t202.py  → app/api/dependencies.py
app/api/schemas_drafts.py     → app/api/common/schemas/drafts.py   （#20 は UI/AGENT 共有のため common）
app/api/schemas_runs.py       → app/api/ui/schemas/agent_runs.py   （#12-14 は UI 名前空間）
backend/tests/t201/           → tests/unit/ ・ tests/integration/ へ層ごとに配分
backend/tests/t202/           → 同上
frontend/orval.t202.config.ts → 削除（`orval.config.ts` に一本化）
frontend/tsconfig.t202.json   → 削除（`npm run typecheck` に一本化）
backend/scripts/export_openapi_isolated.py → 削除（`scripts/export_openapi.py` に一本化）
```

- テストの移動先は `.claude/rules/clean-architecture.md`「テストと層の対応」に従う
  （Repository/API の実 DB を使うもの → `tests/integration/`、決定的関数 → `tests/unit/`）。
- 移動でテストが落ちる場合、**落ちる理由を handoff に書く**。隔離設定を復活させて隠さない。
- `orval.config.ts` の `clean: true` で G1 の生成物が消える懸念がある場合は、
  消えるファイル名を handoff に列挙して Claude の判断を仰ぐ（勝手に `clean: false` を常設しない）。

---

## 4. 「1箇所に集約」はテストで固定した（消さないこと）

`backend/tests/unit/test_single_source_of_truth.py` が以下を機械的に検査する（memory CV-015）。

- 停止閾値・モデル識別子は `app/agent/definition.py` のみ（外での数値リテラル・文字列直書きを検出）
- `E_*` → HTTP status の対応表は `app/api/errors.py` のみ
- `storage_path` は `resolve_readable_path()` の引数としてのみ現れる

同種の「集約したのに複製された」指摘が出たら、**修正と同時にこのファイルへ検査を1つ足す**。
`tests/unit/test_api_path_separation.py` と合わせて、この2本は**削除・弱体化禁止**。

---

## 5. 並行作業の規則（同一スライスに2人を入れない）

- **同じスライスを2セッションで実装しない。**衝突の実績あり（memory TODO-004・LN-015）。
- 並行してよいのは、Claude が明示した**依存が独立で、触るファイルが重ならないスライス**だけ。
  現時点で並行可能なのは `T-301`（G3 BE）と `T-401`（G4 BE）— どちらも依存は T-201 のみ。
  並行指示が出たときは、handoff 冒頭に**自分が触るファイルの一覧**を先に書いてから着手する。
- 共有ファイル（`app/main.py` / `app/api/errors.py` / `app/models/__init__.py` /
  `alembic/versions/` / `docs/requirements/*`）を並行スライスで同時に編集しない。
  必要になったら handoff に書いて Claude に調停を依頼する。
- レビュー中は作業ツリーを触らない（レビュー対象がレビュー中に変わった実績あり: LN-015）。

---

## 6. 修正報告の書き方（自己申告を通さないための最低要件）

handoff の「レビュー対応」表に、指摘ごとに次の3列を書く。

| 指摘番号 | 変更内容（ファイル:行） | RED を確認したテスト名 と 実行コマンド・件数 |

- 「直した」だけの報告は再レビューで通らない（memory LN-006）。
- **実応答（HTTP レスポンス）をアサートするテストが無い箇所は、直っていないものとして扱う。**
- テストの強度は「変異させたら落ちるか」で示す（memory LN-009）。変異内容も1行で書く。
- 既存テストを**変更・削除した場合は必ず理由を書く**。レビュアーは改竄を疑って見る。

---

## 6b. commit の手順（2026-09-14 移譲・Claude から Codex へ）

**フェーズ C でのみ commit する。**レビューが DONE 可、`make check` green、memory 転記済みが前提。

```sh
git status --short                      # 1. 自スライス以外の差分が無いか目で見る
git add -- <自スライスのパスだけ>        # 2. pathspec 限定。git add -A / git add . は使わない
git diff --cached --stat                # 3. 意図しないファイル（他スライス・生成物）が無いか確認
git commit -m "..."                     # 4. 下記の書式
git log --oneline -1
```

- **`git add -A` を使わない。**別セッションの作業中ファイルを巻き込んだ事故がある（memory LN-038・CV-023）。
- メッセージ: 1 行目 `feat|fix|docs|chore: <スライスID> <日本語の要約>`、本文に ①主な変更 ②`make check` の結果
  ③memory への転記内容（AD/RV/LN/Status）。末尾の Co-Authored-By 行は**付けない**（実装者は Codex）。
- **commit しないもの**: `backend/.env`、`backend/traces/`、`backend/openapi.json`、`frontend/src/shared/api/generated/`、
  `backend/storage/`、`.agents/`・`.codex/`（いずれも .gitignore 済み。漏れていたら §0e 5 で研修者へ）。
- ブランチは `main` のまま（本プロジェクトは PR を使わない）。push は研修者が行う。

---

## 7. 次にやること（2026-09-14 15:00 更新・**待機運用は廃止。現在は T-602 の指示書作成**）

> **待機方法への回答（Codex の質問への直接回答）: 待たない。**
> 旧 §0b の「§7 の見出しの更新時刻が変わるまで待つ」は **2026-09-14（AD-032）で廃止**した。
> Claude メインセッションはもう更新しない。**§7 は Codex 自身のキュー**であり、1 スライス終えるたびに
> 自分で書き換えて次へ進む。ポーリングもスリープもしない。
> 止まってよいのは §0e の 6 つ（設計判断・破壊的操作・D05・スコープ変更・BLOCKED 化・秘密情報）に
> 当たったときだけで、そのときは §7 に「研修者確認待ち: <論点>」と自分で書き、**別スライスへ移る**。
> 以降 `### タスク 〜` の見出しはすべて履歴。**この節の箇条書きだけが現在のキュー。**

- **いま: T-602 の指示書を書く**（研修者指示・2026-09-14）。`docs/t602-instructions.md` を §0c の構成で新規作成する。
  T-602 = 【API】G6 出力 API #38（`POST /versions/{versionId}/exports`）・#39（`GET .../exports` 履歴）・#40（`GET /versions/{versionId}/evidence` 版一括）。
  - 入力: `docs/requirements/05-api-ipo.md` 3.10（AD-030 ㉑ で応答形は確定済み）・#38/#39/#40・0.2〜0.4・6 章／`docs/t601-instructions.md` の
    「T-602 へ渡す契約」節（`ExportService.export → ExportResult(record, content)`・`list_exports → integrity`・`list_evidence`・`E_VERSION_NOT_FINALIZED` 409）／
    前例 `docs/t502-instructions.md`・`docs/t402-instructions.md`（`DraftRoute`・`ERROR_RESPONSES`・`CamelModel`・`dependencies.py` の factory・`route_contract.py`）
  - §0 決定表で必ず決める論点: ①バイナリ応答の返し方（`Response` クラスと OpenAPI の `content` 宣言。AD-030 ㉑ の
    200 ＋ `Content-Disposition: attachment; filename="…"` ＋ `X-Export-Id` を実現する形）②orval がバイナリ応答をどう生成するか
    （`frontend/orval.config.ts` を確認。FE が生成クライアントを使うのか #10 と同じく URL 関数＋`apiBaseUrl` で叩くのか。決めて T-603 へ渡す）
    ③`X-Export-Id` がブラウザから読めるか（同一オリジンか CORS の expose-headers が要るか。`backend/app/main.py` と `frontend/next.config.*` を確認）
    ④`tests/fixtures/route_contract.py` の `UI_ONLY_SEGMENTS` に `exports` / `evidence` を登録するか（#38 は書込・#40 は読取）
    ⑤`E_VERSION_NOT_FINALIZED` 409 を `app/api/errors.py` に足す（既存か確認）⑥#40 の DTO を #26 の既存根拠 DTO と共有するか新設か（CV-015）
    ⑦orval model の増減見込み
  - **注意（依存）**: T-602 の**実装**は T-601（`ExportService` / `ExportRepository` / `exports` テーブル）が DONE してからでないと通らない。
    指示書は先に書けるので、契約部分は「着手時に `docs/t601-handoff.md` の契約節で実型を確認する」と明記すること（`docs/t502-instructions.md` が同じ書き方をしている）。
    指示書を書き終えたら §7 をこの下の順に書き換え、**T-501 のレビューへ移る**
- 次（この順に消化する）:
  1. **T-501 の【B レビュー】**（`docs/t501-handoff.md` は実装完了・BE 694 passed の主張まで届いている。**レビューは未実施**）。
     §0d のプロンプトで新しいセッションを開き `docs/t501-instructions.md`（AD-028 の 18 決定＋`latest_review_checked_at` 追補）と突き合わせる。
     特に: ②検査順と `details` の camelCase、⑤ review 版の差し戻しが `E_STATE_ORDER`、⑦ `bounce_id` は NULL→値の 1 回だけ、
     ⑨ 訂正のみ降格（undo/confirm/judge では積まない）、⑫ `current_state` 代入が 2 箇所だけ、⑬ carryOver 4 値、
     ⑮ 未解決述語の一元化、2 セッションの block 観測（CV-024）が本物か。DONE 可なら【C 転記】→ commit（§6b）
  2. **T-502**（`docs/t502-instructions.md`・AD-029 の 18 決定。API 層のみ）
  3. **T-601**（`docs/t601-instructions.md`・AD-030 の 21 決定。BE のみ）
  4. **T-602 の実装**（1 で書いた指示書に従う。T-601 DONE が前提）
  5. **T-603**（G6 出力ボタン・版の履歴 FE ＋ `VersionListItem.elapsedSec` の API 追補。指示書は §0c で自分で書く）
  6. **T-503**（`docs/t503-instructions.md`・AD-031 の 25 決定。FE）
  7. **C-3**（記録のみ P3 のまとめ。memory §6 の TODO-009/017/020/023/026/027/030/031/033/035/036）
  8. **Phase 3 の残り AE04〜AE07**（実 LLM を使うので着手前に §0e 3 で研修者確認）

### 研修者確認待ち（Codex は決めない。回答が来るまで該当スライスを止める）

`.claude/memory.md` §6 の次の TODO が未回答。**G5/G6 の実装自体はこれらの回答なしで進められる**（暫定案で実装済み）。

| TODO | 論点 | 暫定 |
|---|---|---|
| TODO-022 | `13-3/8″` → `13.375 in` の分数→小数化は D03（換算禁止）に抵触するか | 抵触しない扱いで AE01 を PASS 判定 |
| TODO-034 | 評価確認済みの版で「訂正の取消」をしたとき状態を担当者確認済みへ戻すか | 戻さない（訂正のみ降格） |
| TODO-038 | `exports` に実施者名（`exported_by`）を持つか | 持たない |
| TODO-039 | SCR-06 の「変更採用（P.S./Rev.）」タグを API に足すか | 出さない |
| TODO-018 | 要求納期・納地を人が訂正できるようにするか | 編集不可（AD-018） |
| TODO-025① | `range_class` と `length_value` が `length_state` を共有する件 | 状態ラベルは列につき 1 つ（CV-025） |
| TODO-029 | `inventory_links` に複合 FK `(version_id, item_id)` を足すか | 書込時検査のみ |

### タスク L-8c: 依存の逆流を解消（RV-037 P2）
- `RECOVERY_GRACE_S` を `app/domain/run_types.py` へ移し、`app/agent/definition.py` はそこから import して再公開（`from app.domain.run_types import RECOVERY_GRACE_S`）。
  `run_repository.py` は domain から import（`app/agent` を参照しない）。SSOT テスト（`test_single_source_of_truth.py:141-173`）の「定義場所」を domain に付け替え、
  「`app/repositories/**` が `app.agent` を import しない」を機械検査に追加（clean-architecture の逆流検出）。P3: `RECOVERY_GRACE_S > FINISH_TIMEOUT_S*3 + 0.3 + CANCEL_CLEANUP_S` の assert 1 行。
  完了見出し `## L-8c 対応`（t205-handoff）

### タスク N-2: #24 に `rowMatch` を追加（AD-024 ①・T-302 追補）
- `ItemCurrentResponse.rowMatch: {confirmationId, recordedBy, recordedAt} | null`（未取消の一致確認。`kind='row_match'`・`undone_at IS NULL`）。`RecordRepository.list_items_with_edits`
  に select を足す（読取拡張・書込不変）。05 #24 は書き戻し済み。テスト: unit（Service mock で `rowMatch` の有無）＋ integration（confirm → items に rowMatch、undo → null）。
  OpenAPI/orval 再生成で model 追加・消失なしを handoff に。完了見出し `## N-2 対応`（t302-handoff）

### タスク O: T-303（`docs/t303-instructions.md`・AD-024 の 15 決定を含む）— N-2 の後に着手
- 完了見出し `## 再レビュー依頼（T-303）`（t303-handoff）。**`make check-fe` と design-lint は自由に実行可**（Claude は pytest を回さない）

### タスク L-8: 起動時回収の安全化とテスト lifespan の DB 分離（AD-023）

1. `RunRepository.recover_interrupted()`: 対象を **`outcome='running'` かつ `started_at + limits.outer_timeout_s < now()`** に限定（期限切れ＝生きているはずがない run）。
   終了は `RunResult("failed", detail="process_interrupted")` のまま（プロセス死の回収という意味は不変）。新しい run は触らない。JSONL 再構築（`_export_or_fail`）の対象も同様
2. `run_lifespan`: `get_db` を直接呼ばず、**`app.dependency_overrides.get(get_db, get_db)`** を通す（テストの override が lifespan にも効く）。
   `tests/integration/conftest.py` の `client` fixture が lifespan を起動しても **開発 DB に一切触れない**ことをテストで固定（`app.core.database.AsyncSessionLocal` を monkeypatch して
   呼ばれたら fail、または `settings.DATABASE_URL` の engine に `connect` 監視）
3. テスト: ①期限内の running run は起動時回収で終了しない（実 DB integration）②期限切れは `process_interrupted` になる ③lifespan がテスト DB のみを使う ④既存の
   `recover_interrupted` テストの期待更新は「期限内は残す」に合わせる（削除でなく置換、理由を handoff に）
4. 設計書: 04-db §3.2 補足の `process_interrupted` 説明に「起動時回収は外側期限を過ぎた run のみ」を追記。agent-plan T-202 補足の「起動前に worker は生きていない」を
   「別プロセス（テスト含む）が生きている可能性があるため期限で判定」に改める（LN-055）
5. 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green。commit しない。Claude は提出後に AE02 を再実行

### タスク N: T-302（`docs/t302-instructions.md`）— 調整依頼への回答（08:20）

- **許可**: `latestVersionId` 必須追加に伴う FE テスト fixture の追従 **2 行**（`features/cases/__tests__/hooks.test.tsx` の `sampleCase` に `latestVersionId: null`、
  `components/__tests__/CaseListPage.test.tsx` に `latestVersionId: 1`）を T-302 の例外として許可する。テスト本文・assert・プロダクトコードは変えない。
  契約を optional に弱めない判断は正しい。handoff に「T-302 例外（orchestrator 許可）」として file:line を分けて書く
- 適用後に除外なし `make check` を再実行し、handoff 末尾に **`## 再レビュー依頼（T-302）`** の見出しを書く（Claude はこの見出しだけを監視する。本文中の
  「再レビュー依頼」の語は誤検知になるので見出し以外で使わない）
- L-8 が先か T-302 の仕上げが先かは Codex の判断でよい（どちらも小さい）。両方の handoff が揃ったら Claude がまとめてレビューする

### タスク L-7: ツール入口の例外変換と、後始末キャンセルの上書き防止（TODO-021）

1. **`ToolExecutor.invoke`（`tools.py`）**: `begin_step` を含め、入口から出口まで全経路を `ToolReply` に写す。`begin_step` / `locked()` の `require` が上げる `DomainError`
   （`E_NOT_FOUND` / `E_RUN_NOT_ACTIVE` 等）は `ToolReply({"code": ...}, is_error=True)`。それ以外の予期しない例外は `E_INTERNAL`（固定コード）で is_error。
   `asyncio.CancelledError` は従来どおり再送出。`step_id` 未取得のとき `fail_step` は呼ばない
2. **runner `bounded()` / 本体**: `executor.call` が例外で終わった場合（起きない前提だが）`RunResult("failed", turns, "worker_failed")` を返し、worker を例外で落とさない
3. **runner `finally`**: 後始末中の CancelledError は**進行中の例外・戻り値を絶対に上書きしない**。`sys.exc_info()` で進行中例外があればそれを優先（`uncancel()` して握る）、
   戻り値が確定していればそれを返す、期限停止（`deadline_stop`）も従来どおり。**外側（jobs）からの本物のキャンセル**は `deadline_stop=False` かつ進行中例外なし・戻り値未確定の
   場合だけ再送出（このケースは jobs が結果を読まないので分類に影響しない）
4. **jobs `_execute`**: `worker.result()` が `CancelledError` を上げた（= worker task 自体がキャンセルされた）場合は `process_interrupted` ではなく
   `RunResult("failed", detail="worker_failed")`。`process_interrupted` は `await asyncio.wait({worker})` 自身が CancelledError を受けたとき（プロセス停止・`stop_jobs`）のみ。
   04-db §3.2 の `worker_failed` / `process_interrupted` の説明を「worker の例外・キャンセル」「ジョブ境界自身の中断」に書き分ける
5. **診断ログ**: `_consume` / `_worker_done` の error ログに例外の**固定コード**（`DomainError.code`、無ければ型名）を含める。メッセージ本文・引数・資料本文は出さない
6. テスト（決定的・SDK モック）: `begin_step` が `DraftError("E_RUN_NOT_ACTIVE")` を上げる gateway で `invoke` が is_error `ToolReply` を返す / 後始末で CancelledError を上げる
   policy ＋ 進行中に DraftError が出た経路で runner の結果が `failed/worker_failed`・turns 保持（`process_interrupted` にならない）/ jobs で worker task をキャンセルさせたとき
   `worker_failed`、`_execute` 自身をキャンセルしたとき `process_interrupted` / `_consume` のログに code が出て本文が出ない
7. 変異: `check_agent_mutations.py` に「`begin_step` を try の外に戻す」「後始末の CancelledError を再送出に戻す」を追加
8. 完了条件: 限定テスト GREEN を handoff に。`make check` は Claude が §7 で「pytest 可」と書いてから実行して追記。commit しない。Claude は提出後に run 10（AE03 再実行）

### タスク L-6: 根拠・確認事項の一括登録、MAX_TURNS 80、プロンプト補強、無応答診断（AD-021）

1. **一括登録**: `EvidenceArguments.evidences: list[EvidenceInput]`（1 件以上）/ `QuestionArguments.questions: list[QuestionInput]` に変更。保存は従来どおり 1 行ずつ
   （同一トランザクション）、`observation.count` は件数。旧 `evidence:` / `question:` 単数キーは**受けない**（語彙を 2 つにしない。MCP schema と description を更新）。
   `local_dummy_policy` と `evaluate_local_agent.py` の呼出しを配列に追従。ツール名・13 本・検証規則は不変
2. **`definition.MAX_TURNS = 80`**（SSOT テスト・agent-plan と一致）。他の期限は不変
3. **システムプロンプト**（`definition.SYSTEM_PROMPT`、agent-plan Part 1 の写しとして両方更新）に追記: ①材質・接続の代替候補は明細行にしない。`record_question`
   に対象行つきで残す（R03/R04）②根拠・確認事項は項目を集めて配列で一括登録 ③`validate_draft` の違反はまとめて直してから再検証 ④`propose_items` は 1 回で全行
4. **無応答診断**（TODO-021）: runner が `inactivity_timeout` / `inner_timeout` で停止するとき、`job_interrupted` の observation に `{"sinceLastHeartbeatS": n, "heartbeats": m}`
   （数値のみ）を追加。既存の観測スキーマ（status/count/code）に**数値キーを足すだけ**、本文なし。04-db §3.2 補足に 1 行
5. テスト: 配列 1 件/複数件/0 件（`E_REQUEST_INVALID`）/ 旧単数キー拒否 / count が件数 / dummy 方針の 14 ケース `make agent-eval` PASS / 診断メタの数値のみ /
   `MAX_TURNS` SSOT。`test_agent_execution_tools` の期待を配列に更新（削除でなく置換。理由を handoff に）
6. 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（除外なし）＋ `make agent-eval` 14/14。commit しない。Claude は提出後に run 8

### タスク L-5: ツールエラーをモデルへ返して継続（AD-020・agent-plan:235 改定済み）

1. **runner**: `reply.is_error` で即 `RunResult("failed", turns, "tool_rejected")` にせず、**同一ツール名×同一 `observation.code` が連続 `REPEATED_CALL_LIMIT`（3）回**で
   初めて `failed/tool_rejected`。それまでは is_error の結果をモデルへ返して継続（`repeated_call` の既存カウンタと同型の別カウンタ。`repeated_call` は「同一引数の反復」なので混ぜない）
2. **ToolExecutor の error 経路**: `E_REQUEST_INVALID` のとき、ツール結果（`ToolReply` → SDK handler の `content`）に **固定コード＋モデル自身の引数に対する項目別の検証メッセージ**
   （Pydantic の `loc` と `msg`。`input` 値は含めない・資料本文や他案件情報を含めない）を返す。トレースの `observation` は従来どおり code と count のみ（本文なし）。
   スコープ逸脱（`E_NOT_FOUND` 等）は固定コードのみ
3. **run 5 の実引数を再現**: `E_REQUEST_INVALID` になった `record_source_inventory` の入力を推定し（トレースには残っていない。`InventoryArguments` のスキーマと
   agent-plan「ツール一覧」の inventory 定義を照合）、**MCP ツールの `input_schema`/description にモデルが迷わない説明**（`status` の語彙・`basis` 必須条件・`excerpt` の意味）が
   出ているか確認して不足を補う（説明文の追加は設計外のツール追加ではない）
4. テスト（SDK 完全モック・決定的）: 同一コード 2 回は継続し 3 回目で `tool_rejected` / 異なるコードは連続と数えない / 成功で連続カウンタがリセット /
   E_REQUEST_INVALID の結果に `loc`・`msg` が含まれ `input` 値・資料本文が含まれない / 既存 `test_agent_execution_tools` の期待更新は「継続」に合わせる
5. 設計書: agent-plan T-203 節の該当行は Claude が改定済み（:235）。04-db §3.2 の `tool_rejected` 説明を「連続 3 回」に合わせて 1 行修正
6. 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green。`make agent-eval`（14 ケース）の既存シナリオが落ちないこと（`unsupported` は
   `report_unreadable → record_question → local_dummy_unsupported` 経路なので影響なし。落ちたら理由を書く）。commit しない。Claude は提出後に run 6

### タスク L-4: 長い生成中の無応答誤判定と、期限発火時の分類崩れ（run 4）

1. **欠陥 A（無応答の生存信号）**: `ClaudeAgentOptions(include_partial_messages=True)` にし、`consume()` で **`StreamEvent` も `PolicyHeartbeat`** として送る
   （設計「メッセージ間の無応答」をストリームイベント粒度で測る。閾値 60 秒は不変）。agent-plan T-205 節に「生存信号 = SDK メッセージおよび StreamEvent」と追記。
   テスト: StreamEvent が 20 秒間隔で続く 80 秒でも `inactivity_timeout` にならない
2. **欠陥 B（分類崩れ）**: runner の `bounded()` が無応答/内側期限で `task.cancel()` したとき、claude_policy の後始末（SDK consume タスクの cancel・`query()` の anyio cancel scope）
   から **`CancelledError` が worker タスクへ漏れ**、`jobs._execute` の `except CancelledError` → `process_interrupted` になる。修正: policy の `finally` / 後始末を
   **自タスクへの CancelledError を再送出しない形**（`asyncio.shield` した別タスクで SDK を閉じる、または後始末中の CancelledError を捕捉して `LocalPolicyStop` の伝播を優先）にし、
   runner が `RunResult("inactivity_timeout", turns)` を返すこと。テスト: 「後始末で CancelledError を上げるモック policy」で runner が `inactivity_timeout` を返し turns を保持
3. **turns の上書き**: `jobs.py` の `RunResult("failed", detail="process_interrupted"|"worker_failed")` と `RunResult("outer_timeout")` は turns を持たない → `run_repository.finish()` で
   **`result.turns` が None/未指定なら DB の既存 turns を保持**する（0 で潰さない）。テスト: 6 ターン記録済み run に `outer_timeout` を finish しても turns=6
4. 実機停止系の評価シナリオ: `scripts/evaluate_local_agent.py` は local_dummy のまま。代わりに **claude モード用の手動確認手順**を handoff に 1 節（無応答を起こすには
   `INACTIVITY_TIMEOUT_S` を環境変数で一時的に小さくできる口があるか。無ければ追加しない＝設計外。記録のみ）
5. 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（T-301 の衝突テストは L-3 と同じ deselect を明記。CV-023）。SDK は完全モック。commit しない。
   Claude は提出後に `AGENT_MODE=claude` で run 5 を回す

### タスク L-3: ToolSearch の許可とハーネスツールの遮断（AD-019）

1. `definition.py`: `RUNTIME_META_TOOLS = ["ToolSearch"]`（SDK ランタイムのメタツール。業務ツール 13 本とは別の定数。agent-plan のツール一覧は増やさない）。
   `claude_policy` の `allowed_tools = ALLOWED_TOOL_NAMES + RUNTIME_META_TOOLS`。hook（`hooks.py`）は `ToolSearch` を許可（`tool_input` の検査は不要。定義取得のみで副作用なし）。
   `_record_denials` の `safe_name` 判定にも `RUNTIME_META_TOOLS` を含める
2. `DISALLOWED_TOOLS` に CLI 2.1.241 が公開するハーネスツールを追加: `Task, CronCreate, CronDelete, CronList, DesignSync, EnterWorktree, ExitWorktree, ListAgents,
   Monitor, NotebookEdit, PushNotification, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskOutput, TaskStop, Workflow`（既存 8 に加える）。
   **SDK `ClaudeAgentOptions` に組込みツール集合を明示する引数（`tools` 等）があれば `tools=[]`（組込みゼロ）を優先**し、`disallowed_tools` は多重防御として残す
   （SDK の `types.py` を確認して handoff に根拠を書く）
3. `ProcessError`（CLI が max_turns 後に exit 1）と `ResultMessage(subtype="error_max_turns")` の順序を確認し、**max_turns の写しが `model_error` に負けない**ようにする
   （ResultMessage を受けた後の例外は無視して既に決まった stop_reason を優先）。テスト: ResultMessage 到達後に `ProcessError` が上がるモックで `max_turns` になる
4. テスト（SDK 完全モック）: `ToolSearch` が hook を通る / 他のハーネスツール名（`Task`, `SendMessage`）は拒否 / `allowed_tools` に 13＋`ToolSearch` / `disallowed_tools` 集合 /
   `_record_denials` が `ToolSearch` を `unregistered` に潰さない
5. 設計書: agent-plan.md T-205 節に「SDK ランタイムのメタツール `ToolSearch` は許可（定義取得のみ）。業務ツールは 13 本のまま」「ハーネスツールは disallowed」を追記
6. 完了条件: `AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（T-301 の RED ファイルがあるなら `--ignore` した件数を書く。CV-023）。commit しない。
   **Claude は L-3 の提出後に pytest を回す**（それまで Codex の `make check` は自由）

### タスク L-2: T-205 RV-030 の修正（実評価の前提）

1. **P2-3（必須・D05）** `claude_policy.py` の `ClaudeAgentOptions` に **`setting_sources=[]`** を明示（ユーザー/プロジェクト設定・CLAUDE.md・スラッシュコマンドを読み込ませない）。
   あわせて `cwd` を明示（例: 一時ディレクトリまたは `backend/`。リポジトリの `.claude/` を含む親ディレクトリにしない）。テスト: options に `setting_sources==[]` が渡ることを assert
2. **P2-2（必須）無応答時計の意味を設計どおり「メッセージ間」に戻す**: `consume()` が SDK メッセージ（テキスト・部分出力・SystemMessage）受信ごとにキューへ**生存シグナル**
   （ターンに数えない番兵）を積み、runner の `bounded()` はそれで無応答時計だけをリセットする（内側期限・ターン数・repeated_call は不変）。閾値 `INACTIVITY_TIMEOUT_S=60` は変えない。
   テスト: 「ツール呼出しの間に 60 秒超のメッセージ列があっても `inactivity_timeout` にならない」「メッセージが本当に止まれば 60 秒で `inactivity_timeout`」の 2 本（fake clock）
3. **P2-1（必須）** `ResultMessage.permission_denials`（SDK 側 hook 拒否）から**ツール名と固定コード（`E_TOOL_NOT_REGISTERED` / `E_EXTERNAL_LINK_BLOCKED`）だけ**を拾い、
   既存の `guardrail_denied` 管理イベントとして記録（原文・引数は載せない）。テスト: permission_denials 1 件 → `guardrail_denied` 1 件、引数本文が trace に無い
4. **P3-1** `ClaudeAgentOptions(stderr=<固定コードのみ記録するコールバック or 捨てる>)` で SDK 子プロセスの stderr が uvicorn へ直行しないように
5. **P3-3** `ANTHROPIC_API_KEY` を `SecretStr` にし、`get_secret_value()` は `ClaudeAgentOptions.env` を組む直前の 1 箇所だけ。`partial(...)` の repr にキーが載らないことをテスト
6. **P3-4** `disallowed_tools=["Bash","Read","Write","Edit","WebFetch","WebSearch","Glob","Grep"]` を追加（多重防御。hook が主防御のまま）
7. **P3-5** `scripts/check_agent_mutations.py` に claude 系の変異 3 種（bind の request クリアを外す＝二重記録 / `max_turns` 写しを外す / 例外本文を記録する）を追加し
   `make agent-mutations` で再現可能に。P3-2（`impl_version`）は agent-plan に「impl_version はツール実装の版。判断役は `model` で区別」と 1 行追記して記録のみ
8. 設計書: agent-plan.md T-205 節に `setting_sources=[]`・`disallowed_tools`・生存シグナルによる無応答判定・`permission_denials` の記録を追記（LN-030: 語彙一覧と 1対1）
9. 完了条件: SDK は引き続き**完全モック**（実 API を呼ぶテストなし）。`AGENT_MODE=local_dummy DEBUG=false CI=true make check` all green（424+）。commit しない

### タスク L: T-205 実モデル接続（**K-2 の直後に着手。§7 更新を待たない**）

設計の正: `docs/requirements/agent-plan.md` 末尾「T-205 実モデル接続（D05 承認）」。**この範囲を出ない**（判断役の差し替えのみ。ツール・hook・トレース・ジョブ・完了判定・期限は T-203 のまま）。
1. `app/core/config.py`: `AGENT_MODE: Literal["local_dummy","claude"] = "local_dummy"`。`definition.py`: `MODEL_ID = "claude-sonnet-5"`（SSOT テストの対象に含める）
2. `app/agent/claude_policy.py`（新規）: 既存 `local_dummy_policy` と同じ「方針」の口で、SDK `query()` を `ClaudeAgentOptions(model, system_prompt=SYSTEM_PROMPT,
   mcp_servers={"app": agent_server}, allowed_tools=ALLOWED_TOOL_NAMES, hooks=build_hooks(), max_turns=MAX_TURNS)` で起動。ツール実行は**登録済み SDK handler →
   run 束縛 `ToolExecutor`** の既存経路（`tools.py` の ContextVar）を通す。`query()` を `ToolExecutor` 外で呼ばない。SDK の `max_turns` 終了は `stop_reason=max_turns` に写し、
   SDK 例外は `failed` / `stage_detail=model_error`（例外本文をトレースに載せない）。runner の内側 / 無応答期限・jobs の外側期限は不変
3. 組み立て（`app/api/dependencies.py`）: `AGENT_MODE` で `policy_factory` を選ぶ。`claude` かつ `ANTHROPIC_API_KEY` 未設定なら `RunService(external=True)` 相当で
   #12 を 503 `E_EXTERNAL_SEND_NOT_APPROVED`（文言「実モデルが構成されていません」）。`agent_runs.model` に `MODEL_ID` / `DUMMY_MODEL_ID` を保存
4. 設計書追記: 04-db §3.2 補足の固定診断コード一覧に `model_error`。05-api-ipo 6章の 503 文言更新
5. テスト: **SDK をモック**した `claude_policy` の分岐（切替・キー未設定 503・model_error・max_turns の写し・ツール呼出しが ToolExecutor を通ること）のみ。
   **実モデルを呼ぶテストを書かない**（決定性・課金）。`make agent-eval` は `local_dummy` のまま
6. 完了条件: `DEBUG=false CI=true make check` all green（既存 404 / 166 ＋新規）＋ `docs/t205-handoff.md` ＋ `再レビュー依頼`。**`.env` を読まない・表示しない**。
   実モデルでの実行確認は Claude が行う（キー投入は研修者、TODO-016）
7. その後: TODO-009 / TODO-011 ①（`backend/app/` を触る整理）→ G3 T-301（BE）。並行可は T-401（§5）

### タスク F: T-103（G1 FE）の指摘修正 — 指示書は `docs/t103-instructions.md`

RV-019（P1 5 / P2 8 / P3 5 ＋ 未完成 9）の修正内容・優先順・完了条件を**指示書に確定済み**。
着手するときはそちらを読む（本節に内容を二重化しない）。前提の決定は AD-013・AD-009・AD-008・AD-005。

- **WIP=1 を守る**（§2）。T-201 / T-203 のレビュー対応中は着手しない
- 実施順（AD-011）では G2 を縦に通すのが先。T-103 は **T-204 と同じ FE なので、
  どちらを先にやるかは Claude が指示する**（勝手に並行しない）
- 完了条件は `make check-fe` green ＋ design-lint 違反ゼロ ＋ `docs/t103-handoff.md` の
  レビュー対応表（指摘ごとに 変更ファイル / RED→GREEN の実結果 / 実行コマンドと件数）

### 別スライス候補（今はやらない・記録のみ）

`case_service.py` / `document_query_service.py` / `document_intake_service.py` が `app.models`（ORM）を
直接 import しており `clean-architecture.md`「services が ORM を直接参照していない」に抵触する
（T-101/T-102 由来）。Claude が改修スライスとして memory §3 に積むまで着手しない。
