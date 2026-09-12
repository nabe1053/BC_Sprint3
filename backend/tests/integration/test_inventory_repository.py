import pytest
from app.domain.draft_errors import DraftError
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from tests.fixtures.inventory_data import seed_inventory


async def test_real_s06_sets_names_and_version_isolation(db_session):
    first = await seed_inventory(db_session)
    other = await seed_inventory(db_session)
    result = await InventoryService(InventoryRepository(db_session)).reconcile(
        first.seed.version.id
    )
    summary = result.summary
    assert (
        summary.source_entry_count,
        summary.source_item_count,
        summary.output_row_count,
    ) == (12, 8, 11)
    assert summary.split_entry_ids == {first.entries[i].id for i in (6, 7, 8)}
    assert summary.excluded_entry_ids == {first.entries[i].id for i in (9, 10, 11, 12)}
    assert (
        summary.unmapped_entry_ids
        == summary.orphan_item_ids
        == summary.multi_mapped_item_ids
        == summary.inconsistent_entry_ids
        == set()
    )
    assert {item.item_id for item in result.items} == {
        row.id for row in first.items.values()
    }
    assert not {item.item_id for item in result.items} & {
        row.id for row in other.items.values()
    }
    assert [row.entry_id for row in result.entries] == [
        row.id for row in first.entries.values()
    ]
    assert {row.document_file_name for row in result.entries} == {"synthetic-s06.txt"}
    assert summary.coverage is None


async def test_unfinalized_inventory_version_is_not_found(db_session):
    seed = await seed_inventory(db_session, finalized=False)
    with pytest.raises(DraftError) as caught:
        await InventoryRepository(db_session).load(seed.seed.version.id)
    assert caught.value.code == "E_NOT_FOUND"


async def test_cross_version_link_is_reported_and_foreign_item_is_not_exposed(
    db_session
):
    from app.models import InventoryLink

    first = await seed_inventory(db_session)
    other = await seed_inventory(db_session)
    db_session.add(
        InventoryLink(entry_id=first.entries[1].id, item_id=other.seed.item.id)
    )
    await db_session.commit()
    result = await InventoryService(InventoryRepository(db_session)).reconcile(
        first.seed.version.id
    )
    assert result.summary.inconsistent_entry_ids == {first.entries[1].id}
    assert {item.item_id for item in result.items} == {
        row.id for row in first.items.values()
    }
    assert {item.item_id for item in result.entries[0].linked_items} == {
        first.seed.item.id
    }


async def test_coverage_record_and_undo_are_reflected_without_blocking_missing_entries(
    db_session
):
    from app.models import InventoryEntry
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_inventory(db_session)
    db_session.add(
        InventoryEntry(
            version_id=seed.seed.version.id,
            document_id=seed.document.id,
            seq=13,
            position="p.13",
            excerpt="synthetic missing",
            status="unmapped",
        )
    )
    await db_session.commit()
    service = InventoryService(InventoryRepository(db_session))
    records = RecordService(RecordRepository(db_session))
    coverage = await records.confirm(
        seed.seed.version.id, {"kind": "coverage", "recorded_by": "確認者"}
    )
    result = await service.reconcile(seed.seed.version.id)
    assert result.summary.coverage.confirmation_id == coverage.id
    assert result.summary.coverage.recorded_by == "確認者"
    assert result.summary.coverage.recorded_at == coverage.recorded_at
    assert len(result.summary.unmapped_entry_ids) == 1
    await records.undo_confirmation(
        seed.seed.version.id, coverage.id, {"recorded_by": "取消者"}
    )
    assert (await service.reconcile(seed.seed.version.id)).summary.coverage is None
