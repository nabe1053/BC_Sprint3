# Codex セッション作業規約（2026-09-12 改訂・研修者決定）

**実装は主に Codex が担当する。**Claude メインセッション（orchestrator 役）は、スライスの指示・
レビュー起動・memory 転記・品質ゲートの実行を担当し、原則としてコードを書かない。
この文書が Codex 側の恒久ルール。着手前に必ず読むこと。

---

## 0. 役割分担（これを崩さない）

| 担当 | やること | やらないこと |
|------|---------|-------------|
| **Codex（実装）** | RED テスト → 実装 → REFACTOR、レビュー指摘の修正、handoff の更新 | `.claude/memory.md` の編集、レビュー、スライスの取捨選択、commit |
| **Claude（orchestrator）** | スライス指示、reviewer 起動、memory 転記、`make check`、commit | 実装（指摘修正の代行を含む） |

- 自分が書いたコードを自分でレビューしない（CLAUDE.md 憲法6）。レビューは必ず別エージェント。
- **`.claude/memory.md` は読むだけ。編集しない。**進捗・決定・学び・希望 Status は
  `docs/t{ID}-handoff.md` に書き、Claude が memory へ転記する。
  理由: 同時追記で RV/LN の ID 衝突と Status 上書きが実際に起きた（memory §6 TODO-004）。

---

## 0b. 常駐ループ（2026-09-12 研修者決定・memory AD-014 案 B）

Codex はこのループで動く。研修者の中継を待たない。

```
1. 本ファイル §7「次にやること」を読む（見出しの更新時刻を控える）
2. §7 の最優先タスクを1つ実施する（WIP=1。§7 に無いことはしない）
3. `make check`（BE のみなら check-be / FE のみなら check-fe）green と handoff の
   「レビュー対応」表・「再レビュー依頼」を書いて止まる（commit はしない）
4. §7 の見出しの更新時刻が変わるまで待つ（例: 60 秒ごとに `head -n 140 docs/reviews/CODEX-INSTRUCTIONS.md | grep '^## 7'`）。
   変わったら 1 へ戻る。§7 に「停止」と書かれていたら終了する
```

Claude（orchestrator）は handoff を監視し、レビュー結果を §7 に書いて更新時刻を変える。
§7 の更新前に次のタスクを推測して着手しない。研修者確認が要る判断（設計・破壊的操作・D05）は
§7 に「研修者確認待ち」と書かれるので、その間は待つ。

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

## 7. 次にやること（2026-09-12 22:40・T-204 1回目レビュー後・短ラウンド）

- **T-204 → DONE 不可**（memory RV-027。P1 0 / P2 4 / P3 5）。骨格（実行の型・完了判定・decoder・層配置・design）は全て OK。方針転換なし
- **いま進めるのはタスク J（T-204 の短ラウンド）**。修正はいずれも小さい。WIP=1 のまま
- **完了合図の固定文字列**: handoff 冒頭の見出しを `## RV-027 対応（タスク J）` とし、末尾に `再レビュー依頼` と書く。Claude はこの2語を監視する

### タスク J: T-204 RV-027 の修正（orchestrator 判断つき）

1. **P2-1 版の注記（必須）**: `agentRuns.versionNote` を追加し `AgentRunPanel` の起動ボタン近傍に常時表示。文言は 03-spec:124
   「実ファイルを抽出する処理ではありません。再実行は別の生成版になります。未生成の案件ではまだ版がありません」（件数は出さない）
2. **P2-2 作成後の引き継ぎ通知（必須）**: `acknowledgedCarryOver: true` で起動した run が成功したら、完了表示に
   「前版の修正・確認記録は引き継がれていません（既存版は保全されています）」を併記（03-spec:155 X12。件数なし）。RED を先に
3. **P2-3 elapsedSec の丸め（必須）**: `RunProgress` で `Math.floor(run.elapsedSec)` してから `t()` へ。実 API 相当の小数値（例 `12.3456789`）を渡すテスト 1 本
4. **P2-4 起動結果不明の行き止まり（必須・判断済み）**: 資料投入を止める保守的判断は**維持**する。そのうえで、パネルに
   「状態を確認し直す」ボタン（**再 POST しない**。パネルの `uncertain`/エラー状態をリセットして起動可能状態へ戻すだけ）を置き、文言を
   「起動結果を確認できません。状態を確認し直してから、必要なら再度起動してください」に変える。「一覧を再読み込み」は受付一覧と誤読されるので使わない。
   リセット後に再起動した場合、サーバーが `E_RUN_IN_PROGRESS`（409）を返せば既存の 409 表示に落ちる（二重実行は BE が防ぐ）
5. **P3-1**: 進行中 Promise の保持を `useMemo` → `useRef`（`caseId` 変化時に `useEffect` でクリア）。ESLint 警告は依存配列で正しく解消する
6. **P3-2**: 停止理由 9・段階 3 の語彙配列を `model.ts` のモジュール定数へ集約し `stopReasonLabelKey()` / `stageLabelKey()` を export
7. **P3-3**: `stage === "done"` は既知値。`agentRuns.stage.done`「結果を確定中」を追加し pending 扱いにしない
8. **P3-4**: 成功時に診断コードを**併記しない**（完了表示は versionId＋注記のみ）とテストで固定
9. **P3-5**: `docs/test-results/run-ui-checks.mk` / `run-ui-mutations.py` / `run-ui-browser.cjs` は `/tmp` 参照で再実行不能なので**削除**（本指示で承認）。
   ログと画像は残す
10. 完了条件: `DEBUG=false CI=true make check` all green ＋ design-lint 0 ＋ `docs/t204-handoff.md` 冒頭に `## RV-027 対応（タスク J）` の対応表
    （指摘ごとに変更ファイル:行 / RED→GREEN 実結果 / 変異 1 行）＋ `再レビュー依頼`。BE 変更なし。commit しない

### T-204 の後（着手は §7 更新待ち）
- Claude が G2 ミニ評価（実ジョブ 1 本を UI から起動しトレースを agent-plan.md と突き合わせ）→ Phase 3 入口。Codex は待機
- その後 G3（T-301 BE）。並行可は T-401 のみ（§5）

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
