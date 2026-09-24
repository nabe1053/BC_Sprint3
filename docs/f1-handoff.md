# F-1 handoff: propose_items の引数契約とモデルの食い違い解消

指示書: `docs/f1-instructions.md`（決定 A〜D。E は範囲外・研修者判断待ち）

## 発端（原因調査の結論）
sample-10（.eml）で「案を作成する」が失敗（run 27 `failed` / 内訳 `tool_rejected`）。SDK セッション記録
（`~/.claude/projects/-tmp-agent-run-z3i9ocft/`）で、`propose_items` の 4 回連続の `E_REQUEST_INVALID` を確認した:
①`odState=stated` なのに `odValue` 無し → ②`odValue: 13.375`（JSON number。Schema は number を許すのにバリデータが拒否）→
③`rangeClass=R3` なのに `lengthState=not_stated` → ④同種。同一ツール×同一コードの 3 連続で打ち切り。run 23〜26 でも同じ型の失敗が出ていた。

## 変更
| 決定 | 実装 | テスト |
|---|---|---|
| A | `draft_types.py` `Number` に `WithJsonSchema`（string か integer のみ・description）。float の拒否は維持 | `test_draft_inputs.py::test_number_schema_matches_validator_and_excludes_json_floats` |
| B | `agent_types.py` `ItemArguments` の docstring（= ツール説明）に、状態と値の規則を両方向で記載 | `test_agent_tools.py::test_propose_items_description_states_the_value_contract` |
| C | `Input.consistency_errors()` を追加し、wrap validator で全件を返す。`ItemInput` の旧 `consistent_values` を置き換え（検査順は同じ・loc は該当項目・固定の直し方ヒント） | `test_all_consistency_violations_are_reported_in_check_order` / `test_quantity_and_unit_errors_still_come_first` / `test_conflict_hint_covers_value_given_with_non_stated_state` |
| D① | `tools.py` `trace_errors()`（path と type だけ・最大 20 件）→ `fail_step(errors=)` → observation.errors | `test_agent_execution_tools.py::test_item_validation_failure_records_every_path_and_type_only` / `..._are_capped`、inventory テストは errors まで検査する形に強化 |
| D② | `run_repository.py` `job_finish` イベントに `stopDetail`（stage_detail） | `test_agent_tool_repository.py::test_validation_failure_trace_keeps_paths_types_and_stop_detail` / `test_completed_or_undetailed_finish_has_null_stop_detail` |
| 設計 | `04-db.md`（945 付近）・`agent-plan.md:239` に observation.errors / stopDetail を追記 | — |

RED は全件で確認済み（Schema に number が含まれる／違反が 1 件だけ／説明文が空／`errors` の KeyError）。

## ゲート
- `AGENT_MODE=local_dummy make check`: BE 825 passed / FE 446 passed（P2 修正前）
- `AGENT_MODE=local_dummy make check-be`: 826 passed・`✅ check-be: backend green`（P2 修正後）
- 統合: OpenAPI 出力 → orval 再生成 → 差分なし（生成物の `odValue?: string | number | null` は新しい Schema とも矛盾しない）

## レビュー対応（reviewer サブエージェント）
| # | 指摘 | 対応 |
|---|---|---|
| P2 | 状態と値のヒント文とツール説明が片方向（「stated なら値が必要」）だけ。`dueState=tba` と `dueRaw` の組で、LLM が stated に書き換える方へ誘導される | 両方向の文に修正し、逆方向のテストを追加 |
| P3 | 「違反を全件返す」は、型・必須のエラーがある行では成り立たない | docstring を正確な表現に修正 |
| P3 | trace の path に、extra_forbidden で LLM が付けた未知のキー名が入り得る | 記録のみ（次回、伏せるか 04-db に許容と明記） |
| P3 | 20 件で切ったことがトレースに残らない（`errorsTotal` が無い） | 記録のみ |
| P3 | UI API のエラー `details.errors[].path` が `rows.0` から `rows.0.qtyState` などに変わったが、API テストで固定していない（code は不変） | 記録のみ |
| P3 | B のテストは用語が含まれるかだけを見ている | 逆方向の語句の確認を追加。残りは記録のみ |

再レビュー（2回目）: **P1 0 / P2 0・DONE 可**。新しい P3 は1件で、記録のみ。内容は、ヒント文が「値を渡さない」とは言うものの単位（odUnit 等）に触れていないこと。実装は stated 以外で単位を渡しても拒否しないので、説明が誤っているわけではない。

## 別件（今回の範囲外で見つかったもの）
- `backend/.env` が `AGENT_MODE=claude` のままだと、`tests/integration/test_run_regressions.py::test_definition_defaults_reach_reserved_run` が落ちる（テストが `.env` に依存している）。`make check` をそのまま実行すると赤になる。
- 決定 E（3 回規則の判定単位）は研修者の設計判断待ち。

## 未実施
- 実モデルでの再評価（sample-10 / AE02 の再実行）。外部 LLM への送信なので、研修者の確認後に行う。
- memory 転記と commit（フェーズ C）。

## 希望 Status
F-1 = DONE（再レビューで P1 と P2 が 0 件を確認済み）
