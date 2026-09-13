from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace as N
from unittest.mock import AsyncMock

import pytest

from app.domain.draft_errors import DraftError
from tests.fixtures.record_data import current_item, edit, edit_data, approval_questions


@pytest.fixture
def repository():
    active = []
    version = N(id=1, current_state="draft")

    @asynccontextmanager
    async def record(version_id):
        active.append(version_id)
        try:
            yield version
        finally:
            active.pop()

    async def save(version_id, rows):
        assert active == [version_id]
        return rows

    return N(
        record=record,
        version=version,
        save_state_event=AsyncMock(),
        list_questions_with_latest=AsyncMock(return_value=approval_questions()),
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


@pytest.mark.parametrize("state", ["draft", "staff_checked", "review_checked"])
async def test_edit_only_downgrades_review_and_reuses_actor_time(repository, state):
    from app.services.record_service import RecordService

    repository.version.current_state = state
    rows = await RecordService(repository).edit(1, edit_data(recorded_by="訂正者"))
    if state == "review_checked":
        repository.save_state_event.assert_awaited_once_with(
            repository.version,
            from_state="review_checked",
            to_state="staff_checked",
            recorded_by="訂正者",
            recorded_at=rows[0]["recorded_at"],
            unresolved_count=2,
        )
    else:
        repository.save_state_event.assert_not_awaited()


async def test_undo_confirm_and_judge_never_emit_state_events(repository):
    from app.services.record_service import RecordService

    repository.version.current_state = "review_checked"
    service = RecordService(repository)
    await service.undo_edit(1, 1, {"recorded_by": "人"})
    await service.confirm(1, {"kind": "coverage", "recorded_by": "人"})
    await service.judge(
        1, 1, {"status": "judged", "resolution": "unresolved", "recorded_by": "人"}
    )
    repository.save_state_event.assert_not_awaited()
    assert repository.version.current_state == "review_checked"


async def test_summary_unresolved_count_matches_transition_counter(repository):
    from app.services.record_service import RecordService
    from app.services.version_state import unresolved_count

    questions = approval_questions()
    for row in questions:
        row["question"].item_id = None
    repository.summary = AsyncMock(
        return_value={
            "version": N(
                id=1,
                case_id=2,
                version_no=1,
                current_state="draft",
                is_complete=True,
                finalized_at=datetime.now(UTC),
            ),
            "case_header": None,
            "items": [],
            "confirmations": [],
            "questions": questions,
        }
    )
    result = await RecordService(repository).summary(1)
    assert result["unresolved_question_ids"] == {1, 2}
    assert result["unresolved_count"] == unresolved_count(questions) == 2
