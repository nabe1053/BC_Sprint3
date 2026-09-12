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

## 7. 次にやること（2026-09-13 05:00・T-205 全 DONE・T-301 進行中）

- **実評価 run 8 = `completed`**（11 行・AE01 期待どおり・631 秒・14 ターン・漏洩 0）。L-6 は reviewer 確認中（Claude）。**Codex は T-301（タスク M）を再開する**
- T-301 の handoff 冒頭に「T-205 L-3〜L-6 と同一コミット単位（`run_repository._has_records` が `models/records.py` に依存）」と明記する。
  T-205 のファイル（`app/agent/**`・`claude_policy`・`definition`・`hooks`・`run_types`・`run_repository` の T-205 hunk）は**触らない**
- L-6 の reviewer 確認は **DONE 可**で完了（memory RV-032）。T-205 は全ラウンド DONE。Claude は T-301 の再レビュー依頼が来るまで pytest を回さない。Codex の `make check` は自由
- 完了合図: `docs/t301-handoff.md` 末尾 `再レビュー依頼`

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
