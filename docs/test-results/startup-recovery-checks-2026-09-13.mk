startup-recovery-test:
	@cd $(BACKEND) && uv run pytest tests/integration/test_startup_recovery.py tests/integration/test_runs.py -q

startup-recovery-mutation-deadline:
	@cd $(BACKEND) && .venv/bin/python /tmp/startup-recovery-mutation.py deadline
startup-recovery-mutation-lifespan:
	@cd $(BACKEND) && .venv/bin/python /tmp/startup-recovery-mutation.py lifespan
