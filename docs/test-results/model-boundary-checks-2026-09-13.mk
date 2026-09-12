model-boundary-test:
	@cd $(BACKEND) && uv run pytest tests/unit/test_agent_failure_boundaries.py tests/unit/test_agent_execution_tools.py tests/unit/test_policy_activity.py tests/unit/test_policy_tool_errors.py tests/unit/test_claude_policy.py -q
model-boundary-format:
	@cd $(BACKEND) && uv run ruff format app/agent/jobs.py app/agent/runner.py app/agent/tools.py tests/unit/test_agent_failure_boundaries.py scripts/check_agent_mutations.py
	@cd $(BACKEND) && uv run ruff check app/agent/jobs.py app/agent/runner.py app/agent/tools.py tests/unit/test_agent_failure_boundaries.py scripts/check_agent_mutations.py
