.PHONY: model-batch-test model-batch-unit
model-batch-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_agent_execution_tools.py tests/unit/test_policy_activity.py tests/unit/test_single_source_of_truth.py -q
model-batch-test: model-batch-unit model-batch-db
model-batch-db:
	@cd $(BACKEND) && uv run pytest tests/integration/test_agent_tool_repository.py -q
model-batch-mutations:
	@backend/.venv/bin/python /tmp/model-batch-mutation.py
