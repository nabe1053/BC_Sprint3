record-heads:
	@cd $(BACKEND) && uv run alembic heads
record-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_record_inputs.py tests/unit/test_item_current_values.py -q
record-schema:
	@cd $(BACKEND) && uv run pytest tests/integration/test_record_schema.py -q
record-carryover:
	@cd $(BACKEND) && uv run pytest tests/integration/test_runs.py -k carryover -q
record-write:
	@cd $(BACKEND) && uv run pytest tests/unit/test_record_service.py tests/integration/test_record_repository.py -q
record-read:
	@cd $(BACKEND) && uv run pytest tests/integration/test_record_queries.py -q
record-describe:
	@for record_db in $(DEV_DATABASE) octg_test; do \
	  docker exec $(DB_CONTAINER) psql -X -v ON_ERROR_STOP=1 -U $(DB_USER) -d $$record_db \
	    -c 'SELECT current_database();' -c '\d item_edits' -c '\d confirmations' -c '\d question_judgements' || exit 1; \
	done
record-mutations:
	@backend/.venv/bin/python /tmp/record-mutation.py
