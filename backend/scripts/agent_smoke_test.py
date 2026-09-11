"""Slice 0-7 疎通テスト。

ジョブ起動 → ポーリングという「実行の型」そのものでセットアップ全体（SDK・APIキー・
トレース・タイムアウト・ジョブ）を検証する。

ANTHROPIC_API_KEY が backend/.env に未設定の場合はスキップする（Foundation を
キー未設定で失敗扱いにしないため。CLAUDE.md の指示）。キーを設定してから実行する:

    cd backend
    echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env
    uv run python scripts/agent_smoke_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.jobs import get_job, read_progress, start_agent_job  # noqa: E402


async def main() -> None:
    run_id = start_agent_job("ping ツールで 'hello' を送って結果を報告して")
    print(f"run_id={run_id}（即時に返る = 202 相当）")

    while (job := get_job(run_id)).status == "running":  # GET ポーリング相当
        await asyncio.sleep(2)
        last = read_progress(run_id, limit=1)
        print(
            f"  polling... status={job.status} last={last[-1]['type'] if last else '-'}"
        )

    print(
        f"status={job.status} turns={job.result.num_turns if job.result else '-'} "
        f"cost=${job.result.cost_usd if job.result else '-'}"
    )
    assert job.status == "completed", "疎通テスト失敗"
    print("OK: traces/ にトレースが生成されました（backend/traces/*.jsonl を確認）")


if __name__ == "__main__":
    from app.core.config import settings

    if not settings.ANTHROPIC_API_KEY:
        print(
            "SKIP: ANTHROPIC_API_KEY が backend/.env に未設定のため疎通テストをスキップします。\n"
            "      スケルトン・トレース基盤・タイムアウト2層の実装は完了しています。\n"
            "      キーを設定後、このスクリプトを再実行してください。"
        )
        sys.exit(0)

    asyncio.run(main())
