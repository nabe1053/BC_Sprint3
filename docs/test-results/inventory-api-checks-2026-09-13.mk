inventory-api-unit:
	@cd $(BACKEND) && uv run pytest tests/unit/test_inventory_api.py tests/unit/test_api_path_separation_live.py -q
inventory-api-integration:
	@cd $(BACKEND) && uv run pytest tests/integration/test_api_inventory.py -q

inventory-api-mutation:
	@python3 /tmp/inventory-api-mutation.py
