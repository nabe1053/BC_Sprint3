recovery-grace-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_run_recovery.py tests/unit/test_single_source_of_truth.py -q

recovery-grace-mutation:
	@cd $(BACKEND) && .venv/bin/python /tmp/recovery-grace-mutation.py
