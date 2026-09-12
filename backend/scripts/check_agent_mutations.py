"""In-process hook mutations in child interpreters; shared source files stay intact."""
# ruff: noqa: E402 -- standalone script adds backend root before app imports.
import argparse
import json
import inspect
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def child(case):
    import pytest
    from app.agent import hooks

    original = hooks.guard_pre_tool_use
    test_file = "tests/unit/test_agent_execution_tools.py"

    if case.startswith("boundary_"):
        from app.agent import runner, tools

        module = tools if case == "boundary_begin_outside_try" else runner
        source = inspect.getsource(module)
        if case == "boundary_begin_outside_try":
            start = source.index("        try:\n", source.index("    async def invoke"))
            end = source.index(
                "            decision = await guard_pre_tool_use(", start
            )
            prefix = source[start + len("        try:\n") : end]
            source = (
                source[:start]
                + "".join(
                    line[4:] if line.strip() else line
                    for line in prefix.splitlines(True)
                )
                + "        try:\n"
                + source[end:]
            )
        elif case == "boundary_cleanup_reraise":
            before = "if not (deadline_stop or pending_exception or result_ready):"
            if before not in source:
                raise SystemExit(f"Mutation target missing: {case}")
            source = source.replace(before, "if True:", 1)
        exec(compile(source, module.__file__, "exec"), module.__dict__)
        return pytest.main(
            [
                "tests/unit/test_agent_failure_boundaries.py",
                "-q",
                "--tb=short",
                "--disable-warnings",
            ]
        )

    if case.startswith("claude_"):
        from app.agent import claude_policy, tools

        module = tools if case == "claude_request_clear" else claude_policy
        source = inspect.getsource(module)
        changes = {
            "claude_request_clear": [
                (
                    "_policy_request.set(request)",
                    "_policy_request.set(request if request is not None else _policy_request.get())",
                ),
            ],
            "claude_max_turns": [('reason = "max_turns"', "reason = None")],
            "claude_exception_body": [
                ("except Exception:", "except Exception as exc:"),
                (
                    'reason = reason if terminal_received else "model_error"',
                    "reason = str(exc)",
                ),
            ],
        }
        for before, after in changes.get(case, []):
            if before not in source:
                raise SystemExit(f"Mutation target missing: {case}")
            source = source.replace(before, after, 1)
        # Mutate only this child interpreter; repository files remain unchanged.
        exec(compile(source, module.__file__, "exec"), module.__dict__)
        return pytest.main(
            [
                "tests/unit/test_claude_policy.py",
                "-q",
                "--tb=short",
                "--disable-warnings",
            ]
        )

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
            test_file,
            "-k",
            selection,
            "-q",
            "--tb=short",
            "--disable-warnings",
        ]
    )


def main():
    cases = (
        "baseline",
        "block_source_url",
        "allow_read_url",
        "allow_unknown_tool",
        "claude_baseline",
        "claude_request_clear",
        "claude_max_turns",
        "claude_exception_body",
        "boundary_baseline",
        "boundary_begin_outside_try",
        "boundary_cleanup_reraise",
    )
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
            timeout=60,
        )
        expected = (
            0 if case in ("baseline", "claude_baseline", "boundary_baseline") else 1
        )
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
