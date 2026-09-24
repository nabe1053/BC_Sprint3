# F-1 指示書: propose_items の引数契約とモデルの食い違いを解消する（改修・Phase 4）

- 種別: 改修（agent）／依存: T-203, T-205（DONE）
- 発端: sample-10（AE02 相当・run 23〜27）で `propose_items` が毎回 `E_REQUEST_INVALID` になり、
  run 27 は同一ツール×同一コード 3 連続（`tool_rejected`）で `failed`。SDK セッション記録で確認した失敗列:
  ①`odState=stated` に `odValue` 無し → ②`odValue: 13.375`（JSON number）拒否 → ③`rangeClass` あり・`lengthState=not_stated` → ④同種
- 設計の正: `docs/requirements/agent-plan.md:239`（observation は安全なメタデータのみ）・`:243`（is_error で返し継続・3 回規則）、
  `docs/requirements/04-db.md:941-945`（ジョブ管理イベント・stage_detail の固定診断コード）

## §0 決定表

| # | 論点 | 決定 |
|---|---|---|
| A | `Number` の JSON Schema が `number` を許すのにバリデータは float を拒否する | **Schema を実装に合わせる**（`string`（10進表記）か `integer` のみ）。float 拒否は維持（厳密一致・06 採点。`Decimal(str(float))` で受けない） |
| B | ツール説明が `agent-plan: propose_items` だけで state/値の整合ルールが伝わらない | `ItemArguments` に docstring（ツール説明）を付け、state と値・単位の対応、`rangeClass` と `lengthState`、数値の書式、`grade`/`connection` と `*_raw` の違いを明記。`Number` に description。他ツールは範囲外 |
| C | `ItemInput` の整合検査が最初の 1 件で例外を投げる | **全件集めて返す**。順序は従来の検査順を保つ（API の `code` は先頭の `E_` 型なので既存契約不変）。loc は該当項目（例 `lengthState`）に置き、メッセージは直し方を含む固定文（入力値を含めない） |
| D | 失敗の中身がトレースに残らない | ①ツール失敗 step の observation に `errors: [{path, type}]`（最大 20 件・loc と型のみ。msg・入力値は記録しない）②`job_finish` に `stopDetail`（stage_detail の固定診断コード。例 `tool_rejected`）。設計書 04-db.md / agent-plan.md に追記してから実装 |
| E | 3 回規則の判定単位 | **範囲外**（研修者の設計判断待ち） |

## §1 範囲外
- `REPEATED_CALL_LIMIT` の判定変更（E）、HeaderInput / EndInput の整合検査の集約、他ツールの docstring

## §4 実装順序（RED → GREEN）
1. `tests/unit/test_draft_inputs.py`: Schema が number を含まない（A）／複数違反が全件・従来順で返る（C）
2. `tests/unit/test_agent_tools.py` 等: propose_items のツール説明に規則が載る（B）
3. `tests/unit/test_agent_execution_tools.py`: 検証失敗で fail_step に errors（path/type のみ）が渡る（D①）
4. `tests/integration/test_agent_tool_repository.py`: observation.errors と job_finish.stopDetail（D①②）
5. 統合: OpenAPI 出力 → orval → typecheck（`Number` の Schema が API にも出るため）

## §5 完了条件
- `make check` green、reviewer サブエージェントの独立レビューで P1/P2 0、handoff `docs/f1-handoff.md`
