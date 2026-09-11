# AI エージェント開発ルール（Sprint 3）

エージェント（`backend/app/agent/`）を実装・変更するときの恒久ルール。
設計の正は `docs/requirements/agent-plan.md`。

## 1. 設計が正（Design First）

- agent-plan.md に無いツール・完了条件・ガードレールを実装しない。実装中に必要になったら、
  **先に agent-plan.md を更新**してから実装する（設計と実装の乖離を作らない）
- `definition.py` の値（システムプロンプト・max_turns・タイムアウト）は agent-plan.md の写し。
  片方だけ変えない

## 2. レイヤー配置と実行の型

- エージェント実行は `app/agent/` に閉じ込める。**起動は service 層から
  `jobs.start_agent_job()` を呼ぶ**（endpoints から `run_agent()` を直接呼ばない）
- **HTTP リクエスト内で完了を同期待ちしない。** 実行の型は
  「POST → 202 + run_id を即返す → GET /runs/{run_id} でポーリング」。
  進捗はトレースの末尾（`jobs.read_progress()`）をそのまま返す
- SSE 等のストリーミングは発展課題（まずポーリングの型で作る）
- ツールが DB・外部 API に触るときは repository / service を経由する
  （ツールに生 SQL・生 HTTP を書かない）

## 3. トレース（記録されない実行は評価できない）

- **すべての実行を `backend/traces/{run_id}.jsonl` に記録する。**
  トレースを通らない実行経路（`query()` の直接呼び出し等）を作らない
- トレースのレコードは agent-plan.md の IPO 拡張表と同型
  （input / decision / tool_use / observation / result）。この同型性が
  「設計どおり動いたか」をトレースで検証できる根拠なので、スキーマを崩さない
- result の `stop_reason` は agent-plan.md の停止条件と対応させる
  （completed / failed / max_turns / inner_timeout / inactivity_timeout / outer_timeout）

## 4. テストと評価の区別

| 対象 | 検証方法 |
|------|---------|
| ツール（決定的な関数） | **単体テスト（TDD）**。正常・異常・境界を pytest で |
| エージェントループ（LLM の判断） | **評価シナリオ + トレース**（06 のエージェント評価シナリオを実行し、agent-plan.md と突き合わせる） |

- エージェントループの単体テストを書こうとしない（非決定的で意味をなさない）
- 「テストが全部通った」はツールの保証であって、エージェントの保証ではない

## 5. ガードレールは強制する（お願いにしない）

- agent-plan.md の「してはいけない操作」は **PreToolUse hook / disallowed_tools でブロック**する。
  システムプロンプトに書くだけ（お願い）で済ませない
- 「人間の承認が必要な操作」は承認フローを通らない限り実行できない構造にする

## 6. タイムアウトは2層（内側 < 外側）

```
無応答（INACTIVITY_TIMEOUT_S）< 内側（INNER_TIMEOUT_S）< 外側（OUTER_TIMEOUT_S）
```

- **内側**（`runner.py`）: エージェント自身の停止条件（agent-plan.md の強制停止）。
  実行全体の上限 + メッセージ間の無応答検知（ハング検知）。
  発火したら**トレースに stop_reason を記録して**整然と終了する
- **外側**（`jobs.py` の `asyncio.wait_for`）: 内側がハング等で発火できなかったときの
  最後の砦。jobs がトレースを握っているので、外側発火も `outer_timeout` として記録される。
  **ジョブを経由しない（＝外側の無い）エージェント起動を書かない**
- 外側が発火した = 内側が機能しなかった異常。握りつぶさず、バグとして調査する
- この大小関係を崩す変更をしない。外側が先に発火すると、実行途中の文脈が
  中途半端に破棄され、内側の停止理由（何に詰まっていたか）が失われる

## 7. 秘密情報

- `ANTHROPIC_API_KEY` は `backend/.env` のみ（git 管理外）。コード・トレースに書かない
- トレースに個人情報・認証情報が乗る設計にしない（ツールの出力に注意）
