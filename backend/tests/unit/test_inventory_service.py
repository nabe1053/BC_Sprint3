from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock
import pytest
from app.domain.draft_errors import DraftError
from app.domain.record_types import RowMatch
from app.services.inventory_service import InventoryService
from tests.fixtures.inventory_data import s06


async def test_service_delegates_version_and_attaches_document_name_with_null_coverage():
    repository = N(
        load=AsyncMock(
            return_value=(*s06(), [N(id=1, file_name="synthetic.txt")], None)
        )
    )
    result = await InventoryService(repository).reconcile(1)
    repository.load.assert_awaited_once_with(1)
    assert result.summary.coverage is None
    assert {row.document_file_name for row in result.entries} == {"synthetic.txt"}
    assert result.summary.source_item_count == 8


async def test_service_preserves_unfinalized_version_not_found():
    error = DraftError("E_NOT_FOUND", "unfinalized")
    repository = N(load=AsyncMock(side_effect=error))
    with pytest.raises(DraftError) as caught:
        await InventoryService(repository).reconcile(99)
    assert caught.value is error
    repository.load.assert_awaited_once_with(99)


async def test_service_attaches_only_coverage_response_fields():
    at = datetime(2026, 9, 13, tzinfo=UTC)
    repository = N(
        load=AsyncMock(
            return_value=(
                [],
                [],
                [],
                [],
                N(id=7, recorded_by="確認者", recorded_at=at, private="hidden"),
            )
        )
    )
    result = await InventoryService(repository).reconcile(9)
    assert result.summary.coverage == RowMatch(7, "確認者", at)
