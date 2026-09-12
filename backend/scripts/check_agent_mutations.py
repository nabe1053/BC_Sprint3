"""In-process hook mutations in child interpreters; shared source files stay intact."""
# ruff: noqa: E402 -- standalone script adds backend root before app imports.
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def child(case):
    import pytest
    from app.agent import hooks

    original = hooks.guard_pre_tool_use

    if case == "block_source_url":

        async def mutated(data, tool_id, context):
            if "https://" in json.dumps(data.get("tool_input", {})).lower():
                return hooks._deny("E_EXTERNAL_LINK_BLOCKED")
            return await original(data, tool_id, context)

        hooks.guard_pre_tool_use = mutated
        selection = "url_source_records_succeed_unchanged"
    elif case == "allow_read_url":
        hooks._contains_blocked_pattern = lambda value: None
        selection = "guardrail_reasons_are_distinct_without_source_text"
    elif case == "allow_unknown_tool":

        async def mutated(data, tool_id, context):
            return {}

        hooks.guard_pre_tool_use = mutated
        selection = "hook_rejects_every_unregistered_capability"
    else:
        selection = "url_source_records_succeed_unchanged or guardrail_reasons_are_distinct_without_source_text or hook_rejects_every_unregistered_capability"
    return pytest.main(
        [
            "tests/unit/test_agent_execution_tools.py",
            "-k",
            selection,
            "-q",
            "--tb=short",
            "--disable-warnings",
        ]
    )


def main():
    cases = ("baseline", "block_source_url", "allow_read_url", "allow_unknown_tool")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=cases)
    args = parser.parse_args()
    if args.case:
        raise SystemExit(child(args.case))
    for case in cases:
        result = subprocess.run(
            [sys.executable, "-B", __file__, "--case", case],
            text=True,
            capture_output=True,
        )
        expected = 0 if case == "baseline" else 1
        if result.returncode != expected:
            print(result.stdout + result.stderr)
            raise SystemExit(f"Unexpected test exit for {case}: {result.returncode}")
        summaries = [
            line
            for line in result.stdout.splitlines()
            if " passed" in line or " failed" in line
        ]
        if not summaries:
            raise SystemExit(f"Missing pytest results for {case}")
        print(f"{case}: {summaries[-1]} (expected exit {expected})")


if __name__ == "__main__":
    main()
