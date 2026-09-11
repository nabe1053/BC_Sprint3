"""エージェント実行トレース: backend/traces/{run_id}.jsonl に記録する。

レコードは agent-plan.md の IPO 拡張表（Input / 判断 / ツール実行 / 観察・Output）と同型で、
かつ 04-db.md `agent_run_steps`（tool_name / args_digest / locator / document_id /
result_status）と対応させる。記録されない実行は評価できない — すべての実行はここを通す。
`args_summary` は要約のみ。資料全文・認証情報は残さない（N02）。
"""

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

TRACES_DIR = Path(__file__).resolve().parents[2] / "traces"


def digest_args(args: dict) -> str:
    """引数のハッシュ（同一ツール・同一引数の連続呼び出し検知に使う）。"""
    raw = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def summarize_args(args: dict, limit: int = 200) -> str:
    """引数の要約のみを残す。資料全文・認証情報は含めない（N02）。"""
    raw = json.dumps(args, ensure_ascii=False, default=str)
    return raw[:limit] + ("..." if len(raw) > limit else "")


class TraceRecorder:
    def __init__(self, scenario: str | None = None) -> None:
        self.run_id = (
            datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
        )
        self.path = TRACES_DIR / f"{self.run_id}.jsonl"
        self.step = 0
        self._start = time.monotonic()
        TRACES_DIR.mkdir(exist_ok=True)
        self._write(
            {
                "type": "meta",
                "run_id": self.run_id,
                "scenario": scenario,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def _write(self, record: dict) -> None:
        record.setdefault("elapsed_s", round(time.monotonic() - self._start, 2))
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def record_input(self, prompt: str) -> None:
        self._write({"type": "input", "prompt": prompt})

    def record_decision(self, text: str) -> None:
        """判断(Process): アシスタントのテキスト/思考。"""
        self.step += 1
        self._write({"type": "decision", "step": self.step, "text": text})

    def record_tool_use(self, name: str, tool_input: dict) -> None:
        """ツール実行: 使用ツールが agent-plan.md ツール一覧の範囲内かの検証に使う。"""
        self._write(
            {
                "type": "tool_use",
                "step": self.step,
                "tool": name,
                "args_digest": digest_args(tool_input),
                "args_summary": summarize_args(tool_input),
            }
        )

    def record_observation(self, tool_name: str, content, is_error: bool) -> None:
        """観察: ツール結果。"""
        self._write(
            {
                "type": "observation",
                "step": self.step,
                "tool": tool_name,
                "content": content,
                "is_error": is_error,
            }
        )

    def record_guardrail_block(self, tool_name: str, reason: str) -> None:
        """ガードレールにより拒否されたツール呼び出し（hooks.py から呼ばれる）。"""
        self._write(
            {
                "type": "guardrail_block",
                "step": self.step,
                "tool": tool_name,
                "reason": reason,
            }
        )

    def record_result(
        self,
        stop_reason: str,
        *,
        num_turns: int | None = None,
        cost_usd: float | None = None,
        detail: str | None = None,
    ) -> None:
        """終了: stop_reason は completed / failed / max_turns / inner_timeout /
        inactivity_timeout / outer_timeout / repeated_call のいずれか
        （agent-plan.md 停止条件と対応付ける）。"""
        self._write(
            {
                "type": "result",
                "stop_reason": stop_reason,
                "num_turns": num_turns,
                "cost_usd": cost_usd,
                "detail": detail,
            }
        )
