from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest

from app.domain.draft_errors import DraftError
from tests.fixtures.record_data import current_item, edit, edit_data


@pytest.fixture
def repository():
    active = []

    @asynccontextmanager
    async def record(version_id):
        active.append(version_id)
        yield
        active.pop()

    async def save(version_id, rows):
        assert active == [version_id]
        return rows

    return N(
        record=record,
        item=AsyncMock(return_value=current_item()),
        edits=AsyncMock(return_value=[]),
        save_edits=AsyncMock(side_effect=save),
        get_edit=AsyncMock(return_value=edit()),
        undo=AsyncMock(),
        active_confirmation=AsyncMock(return_value=None),
        save_confirmation=AsyncMock(),
        get_confirmation=AsyncMock(),
        question=AsyncMock(),
        save_judgement=AsyncMock(),
    )


async def test_quantity_pair_records_current_old_values_once_in_same_transaction(
    repository
):
    from app.services.record_service import RecordService

    repository.edits.return_value = [
        edit(field="qty_value", new_value="180", new_state="numeric")
    ]
    before = datetime.now(UTC)
    rows = await RecordService(repository).edit(
        1,
        edit_data(
            field="qty_value", new_value="200", new_state="numeric", qty_unit="本"
        ),
    )
    after = datetime.now(UTC)
    assert [row["field"] for row in rows] == ["qty_value", "qty_unit"]
    assert rows[0]["old_value"] == "180" and rows[1]["old_value"] == "MT"
    assert rows[0]["new_value"] == "200" and rows[1]["new_value"] == "本"
    assert before <= rows[0]["recorded_at"] == rows[1]["recorded_at"] <= after
    repository.save_edits.assert_awaited_once()


async def test_old_value_uses_latest_effective_edit_and_source_is_unchanged(repository):
    from app.services.record_service import RecordService

    repository.edits.return_value = [
        edit(new_value="J55"),
        edit(id=2, new_value="N80", undone_at=datetime.now(UTC)),
    ]
    rows = await RecordService(repository).edit(1, edit_data())
    assert rows[0]["old_value"] == "J55" and rows[0]["old_state"] == "stated"
    assert repository.item.return_value.grade == "K55"


async def test_undo_requires_target_then_active_record_then_actor(repository):
    from app.services.record_service import RecordService

    service = RecordService(repository)
    repository.get_edit.side_effect = DraftError("E_NOT_FOUND", "missing")
    with pytest.raises(DraftError) as error:
        await service.undo_edit(1, 1, {"recorded_by": ""})
    assert error.value.code == "E_NOT_FOUND"
    repository.get_edit.side_effect = None
    repository.get_edit.return_value = edit(undone_at=datetime.now(UTC))
    with pytest.raises(DraftError) as error:
        await service.undo_edit(1, 1, {"recorded_by": ""})
    assert error.value.code == "E_ALREADY_UNDONE"
    repository.get_edit.return_value = edit()
    with pytest.raises(DraftError) as error:
        await service.undo_edit(1, 1, {"recorded_by": " "})
    assert error.value.code == "E_RECORDER_REQUIRED"
    await service.undo_edit(1, 1, {"recorded_by": "取消者"})
    args = repository.undo.call_args.args
    assert args[1].tzinfo is UTC and args[2] == "取消者"


async def test_duplicate_confirmation_is_prechecked(repository):
    from app.services.record_service import RecordService

    repository.active_confirmation.return_value = N(id=1)
    with pytest.raises(DraftError) as error:
        await RecordService(repository).confirm(
            1, {"kind": "row_match", "item_id": 1, "recorded_by": "person"}
        )
    assert error.value.code == "E_ALREADY_CONFIRMED"
    repository.save_confirmation.assert_not_awaited()
