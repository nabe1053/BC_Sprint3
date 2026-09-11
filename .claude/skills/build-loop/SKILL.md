---
name: build-loop
description: memory 駆動の自律実装ループ・オーケストレータ（Sprint 3）。memory.md からプランを作り、Web スライスとエージェントスライス（agent-plan.md 由来）を TDD 実装→独立レビュー→修正→memory 記録で初版完成まで回す。継続改善も同じフローで行う。
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Task(test-designer, implementer, reviewer)
---

# build-loop: 実装ループ・オーケストレータ（Sprint 3）

あなたは **orchestrator**（実装ループの指揮者）です。
`.claude/memory.md` を唯一の可変状態ハブとして、スライス単位で
「計画 → TDD 実装 → 別エージェントのレビュー → 修正 → memory 記録」を
**初版完成まで自律で周回**します。初版後の修正・改善も同じループで行います。

Sprint 3 のスライスには2種類あります：
- **Web スライス**: 画面・CRUD 等（エージェントを動かす器）
- **エージェントスライス**: `docs/requirements/agent-plan.md` に定義されたエージェント（AGENT-XX）。
  実装手順は [agent-slices.md](agent-slices.md) に従う

> memory の書式・書込規約: `.claude/rules/memory-protocol.md`（**必読**）
> クリーンアーキの依存ルール・層マッピング: `.claude/rules/clean-architecture.md`
> UIデザインのガードレール: `.claude/rules/design-guidelines.md`（トークンの真実源は `docs/requirements/03-spec.md` 3章）
> エージェント開発の原則: `.claude/rules/agent-development.md`
> TDD: `.claude/rules/tdd-guide.md`

## 入力（引数）

- 引数なし: **初版ビルドモード**。設計書全体からスライスを生成し、全部 DONE まで周回。
- `--change "<変更要求>"`: **継続改善モード**。変更要求を受けて影響スライスを特定し、差分スライスのみ周回。
  エージェント評価（CLAUDE.md Phase 3）で Fail が出たときの修正もこのモードで回す。

## 大原則

- **memory.md を編集できるのは orchestrator（このスキル）だけ**。サブエージェント（test-designer / implementer / reviewer）は memory を**読むだけ**。指摘・学びは戻り値で受け取り、orchestrator が追記する。
- **完全自律**: プラン確定・スライス完了で承認を挟まず周回する。
- **必ず終端する**: レビュー修正が上限 `N=3` 回を超えたスライスは `BLOCKED` として記録し、依存のない他スライスへ進む。最後に BLOCKED 一覧を報告する。
- **TDD 厳守**: 型定義以外は RED（テスト失敗）を確認してから GREEN に進む。
  例外: **エージェントループは単体テストしない**（ツールのみテスト対象。ループはミニ評価で検証）。
- **依存ルール厳守**: 内側の層（Data/Business）は外側の層（Presentation）を知らない。
- **設計が正**: agent-plan.md に無いツール・完了条件を実装しない。実装中に必要が生じたら
  memory §6 に記録してスライスを BLOCKED にし、設計側の更新を促す（勝手に設計を変えない）。

---

# 手順

## Step 0: 初期化

1. `.claude/memory.md` を Read。存在しなければ `.claude/rules/memory-protocol.md` の雛形で新規作成する。
2. `.claude/rules/clean-architecture.md`・`.claude/rules/design-guidelines.md`・`.claude/rules/agent-development.md`・`CLAUDE.md` を Read し、
   **このプロジェクトのスタック情報**を把握する:
   - 層 → ディレクトリの対応（`app/agent/` の位置づけ含む）
   - 統合ポイントの有無とコマンド（OpenAPI 出力 → orval 再生成 → typecheck）
   - stack コマンド（test / lint / format / typecheck）
   - reviewer チェックリスト（AI Agent 固有項目・design-guidelines の UI 項目含む）
   - デザイントークン（`docs/requirements/03-spec.md` 3章 ↔ `tokens.ts` の対応）
3. モードを判定（引数の有無）。

## Step 1: プラン生成 / 更新（memory §3 へ）

### 初版ビルドモード
1. 設計書を Read（存在するもののみ）:
   - `docs/requirements/01-request.md`, `02-requirement.md`, `03-spec.md`（モック含む）,
     `04-db.md`, `05-api-ipo.md`, **`agent-plan.md`（エージェント設計）**
2. **設計書を実装スライスに分割する**（orchestrator 自身が判断）。分割基準:
   - **縦に貫く**: 1スライス = 1つのユーザー機能を Presentation(UI) → Business Logic → Data Access まで一貫して含む
   - **粒度**: 1〜2日で実装できる機能単位。大きすぎも小さすぎも避ける
   - **エージェントスライスを区別する**: agent-plan.md の AGENT-XX は 1 体 = 1 スライス（大きければ
     「ツール群」「ループ+API接続」に分割可）。種別 `agent` を付ける
   - **依存順**: 基盤スライス（基本CRUD）→ **エージェントのツールが依存する API・テーブル
     （agent-plan.md ツール一覧の最終列）を提供する Web スライス** → エージェントスライス の順に置く
   各スライスに次を付与: ID / 種別（web/agent）/ 概要 / 依存スライス / 対象画面 / API エンドポイント / 関連データ
3. 依存順に並べ、memory §3「実装バックログ」テーブルへ全スライスを `Status=PLANNED` で記録
   （種別列を追加してよい）。

### 継続改善モード
1. `--change` の要求文と memory（§1 決定・§2 規約・§3 バックログ）を突き合わせ、影響スライスを特定。
   エージェント評価の Fail 修正の場合は、該当トレース（`backend/traces/{run_id}.jsonl`）と
   agent-plan.md を読み、原因層（ツール / definition / 設計）を特定してから改修スライスを切る。
2. 新規スライス、または既存スライスの「改修スライス」を memory §3 に `PLANNED` で追加。

> **注**: Foundation（Slice 0-1〜0-7。`app/agent/` スケルトン生成 = agent-setup 含む）は
> **ループの対象外**。スライスに含めない（foundation エージェント・`/foundation-*` で別途実施）。

## Step 2: 次スライスの選択

1. memory §3 から、`Status=PLANNED` かつ **依存スライスがすべて DONE** のものを1つ選ぶ。
2. 該当が無ければ Step 6（終端）へ。
3. 選んだスライスの Status を `IMPLEMENTING` に更新（memory を書き換え）。

## Step 3: スライス指示書の生成

選んだスライスについて、Step 0 で把握したスタック情報を使い、**層ごとの実装計画**を組み立てる。

- **Web スライス**: `clean-architecture.md` の「Web スライスの実装順序」
  （DTO → Repository → Service → API → 統合 → api.ts/hooks → components/page）
- **エージェントスライス**: [agent-slices.md](agent-slices.md) を Read し、その層順
  （tools → definition/ガードレール → jobs 経由 API 接続 → 統合 → ポーリング UI → ミニ評価）で組む。
  指示書には **agent-plan.md の該当箇所（ツール一覧・完了条件・ガードレール）を必ず含める**

各層について次を明記する（サブエージェントに渡す）:

```
## スライス: {ID} {名前}（種別: web / agent）
## 対象層: {層の並び。このスタックに存在する層のみ}

### この層の
- 対象ディレクトリ / ファイル: {path}
- 依存（呼んでよい内側の層）: {...}
- テストコマンド: {CLAUDE.md 記載のコマンド}
- テストケース（正常系 / 異常系）: {IPO・仕様・agent-plan.md から導出}
- 参考にすべき既存実装: {path}
```

## Step 4: 層ごとの TDD 実装

`clean-architecture.md` の**依存内側から外側**の順に、各層で以下を回す。

1. **型/DTO 層**（テスト不要）: `Task(implementer)` に型定義のみ実装させる。
2. **それ以外の各層**:
   - **RED**: `Task(test-designer)` に該当層のテストを書かせ、**テストが失敗すること**を確認（戻り値で失敗を報告させる）。
   - **GREEN**: `Task(implementer)` に「通すべきテスト・対象ファイル・依存ルール」を渡して実装させ、**テスト成功**を確認。
   - 失敗が続く場合も、この段階では implementer に再委譲（層内のリトライ）。
3. **エージェントスライスの definition / ガードレール層**（テスト対象外の設定層）:
   `Task(implementer)` に agent-plan.md の該当箇所を渡して実装させる（agent-slices.md 参照）。
4. **統合ポイント**（orchestrator 自身が Bash で実行）:
   - `cd backend && uv run python scripts/export_openapi.py -o openapi.json`
   - `cd frontend && npm run orval && npm run typecheck`
   - 生成が失敗したら implementer に修正させてから先へ。
5. backend 側の層が完了し統合ポイントを通したら、frontend 側の層に進む。
6. **エージェントスライスのみ・ミニ評価**（orchestrator 自身が Bash で実行）:
   agent-plan.md「評価シナリオ」の正常系1本をジョブ経由で実行し、
   トレース（`backend/traces/{run_id}.jsonl`）の stop_reason が完了条件どおりかを確認する。
   Fail ならトレースを根拠に implementer へ修正を委譲（agent-slices.md の手順）。

## Step 5: レビュー → 修正 → 記録

1. **レビュー**: `Task(reviewer)` にこのスライスの**変更範囲**（対象ファイル群 / `git diff`）と
   `clean-architecture.md` のチェックリスト（UI を含むスライスでは `design-guidelines.md` の
   reviewer チェックリストも）を渡す。エージェントスライスの場合は
   **agent-plan.md と、ミニ評価の run_id も渡す**。reviewer は read-only で**指摘のみ**返す。
2. **判定**:
   - 指摘ゼロ → 3 へ。
   - 指摘あり → Status を `FIXING` にし、`Task(implementer)` に「指摘 + 対象範囲」を渡して修正させる → **reviewer に再レビュー**。これを最大 `N=3` 回。
   - `N` 回超えても指摘が残る → memory §6 に `BLOCKED`（原因・残指摘）を記録し、このスライスを離脱して Step 2 へ。
3. **モック照合（UI を含むスライスのみ）**:
   - 開発サーバーで該当画面を表示し、`docs/requirements/mocks/mockup.html` の対応 `#SCR-xx` と見比べる。
     スクリーンショットが取れる環境なら orchestrator 自身が両者を撮って比較する。
   - 比較観点: 画面構成（要素・配置）がモックと一致 / デザイントークン逸脱がない / 3状態（空・ローディング・エラー）がある
   - 乖離があれば `Task(implementer)` に修正させる（修正回数は 2 の `N=3` に合算）。
   - スクリーンショットが取れない環境では、memory §5 に「研修者の目視確認待ち: {画面}」を記録して先へ進む（自律周回は止めない）。
4. **記録（memory へ、orchestrator が追記）**:
   - §1 アーキテクチャ決定（新たに確定したもの）
   - §4 レビュー指摘と対応（RV-xxx）。**同種の指摘が繰り返し出たら §2 規約へ昇格**（memory-protocol の昇格ルール）。
   - §5 学び・ハマりどころ（LN-xxx）。エージェントスライスはミニ評価の run_id も残す
   - §3 該当スライスの Status を `DONE` に更新
5. **品質ゲート & コミット**: CLAUDE.md 記載の lint/format/typecheck/test と
   `node .claude/scripts/design-lint.mjs`（デザイントークン逸脱の機械検出）を実行し、緑を確認してから
   `git add -A && git commit`（コミットメッセージにスライス ID と概要）。`/git-commit` スキルがあれば併用可。
6. Step 2 に戻る。

## Step 6: 終端

1. memory §3 のスライスに `PLANNED`/`IMPLEMENTING`/`FIXING` が残っていない（= すべて `DONE` か `BLOCKED`）ことを確認。
2. 完了レポートを出力:
   ```
   ## 🎉 実装ループ終了
   - DONE: {n} スライス（うちエージェント: {k}）
   - BLOCKED: {m} スライス
     - {ID}: {原因の要約}（memory §6 参照）
   - 次アクション（BLOCKED があれば人手対応 / なければ初版完成）
   ```
3. **BLOCKED が 0 かつ初版ビルドモード**なら「初版完成」と宣言し、次を案内する:
   - **エージェント評価**（CLAUDE.md Phase 3）: 06-scenario-test.md のエージェント評価シナリオを実行し、
     トレースを agent-plan.md と突き合わせる。Fail は `/build-loop --change` で修正
   - 評価を自動化したくなったら `/r2b-env-sprint3`（Env フェーズ）へ

---

# 制約 / ガードレール

- **memory.md の唯一の編集者**はこのスキル。サブエージェントには読取のみ許可する。
- **依存ルール違反**が reviewer に検出されたら必ず修正する（放置して DONE にしない）。
- **RED を飛ばさない**（型定義・definition 等の設定層を除く）。
- **エージェントループの単体テストを書かせない**（ツールのみ。ループはミニ評価 + Phase 3 の評価で検証）。
- **統合ポイントの生成コードは編集しない**（orval 生成物など）。
- **Build 中に新しいデザイン判断をしない**: トークン（03-spec 3章）に無い色・サイズ・装飾を発明しない。必要になったら `BLOCKED` として研修者に確認する（`.claude/rules/design-guidelines.md`）。
- **agent-plan.md に無いものを実装しない**（設計の更新が必要なら BLOCKED + 報告）。
- **無限ループ防止**: 同一スライスの修正は `N=3` で打ち切り `BLOCKED`。
- **中断復帰**: セッションが切れても memory §3 の Status から再開できる（`IMPLEMENTING`/`FIXING` のスライスから再開）。
