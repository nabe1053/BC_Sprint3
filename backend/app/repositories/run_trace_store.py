"""Rebuild JSONL atomically from committed DB events; retries never append duplicates."""
import json
from pathlib import Path


class RunTraceStore:
    def __init__(self, root=None):
        self.root = (
            Path(root) if root else Path(__file__).resolve().parents[2] / "traces"
        )

    def sync(self, run_id, events):
        if not isinstance(run_id, int) or run_id < 1:
            raise ValueError("Invalid run id")
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / f"{run_id}.jsonl"
        pending = self.root / f"{run_id}.jsonl.pending"
        content = "".join(
            json.dumps(event, ensure_ascii=False) + "\n" for event in events
        )
        pending.write_text(content, encoding="utf-8")
        pending.replace(target)
