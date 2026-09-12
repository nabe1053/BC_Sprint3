inventory-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_inventory_reconciliation.py tests/unit/test_inventory_service.py -q
inventory-reconciliation:
	@cd $(BACKEND) && uv run pytest tests/unit/test_inventory_reconciliation.py -q
inventory-integration:
	@cd $(BACKEND) && uv run pytest tests/integration/test_inventory_repository.py -q
inventory-heads:
	@cd $(BACKEND) && uv run alembic heads

inventory-mutation:
	@cd $(BACKEND) && .venv/bin/python /tmp/inventory-mutation.py $(INVENTORY_MUTANT)
inventory-mutations:
	@python3 /tmp/inventory-mutations.py
