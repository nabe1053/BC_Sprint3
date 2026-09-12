row-match-test:
	@cd $(BACKEND) && uv run pytest tests/unit/test_record_api.py tests/integration/test_api_records.py tests/integration/test_record_queries.py -q

row-match-mutation:
	@cd $(BACKEND) && .venv/bin/python /tmp/row-match-mutation.py
