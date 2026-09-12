record-api-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_record_api.py -q
record-api-read:
	@cd $(BACKEND) && uv run pytest tests/unit/test_case_service.py tests/unit/test_api_path_separation_live.py tests/integration/test_api_records.py -q
record-api-mutation:
	@backend/.venv/bin/python /tmp/record-api-mutation.py
