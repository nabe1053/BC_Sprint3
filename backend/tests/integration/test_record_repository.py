from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.domain.draft_errors import DraftError
from app.models import ItemEdit, Confirmation, Question, QuestionJudgement
from tests.fixtures.record_data import edit_data, seed_record_version


async def test_records_are_append_only_and_undo_keeps_actor(db_session):
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session)
    service = RecordService(RecordRepository(db_session))
    first = (await service.edit(seed.version.id, edit_data(item_id=seed.item.id)))[0]
    second = (
        await service.edit(
            seed.version.id, edit_data(item_id=seed.item.id, new_value="N80")
        )
    )[0]
    assert second.old_value == "L80"
    await service.undo_edit(seed.version.id, second.id, {"recorded_by": "取消者"})
    assert second.undone_by == "取消者" and second.undone_at is not None
    rows = list((await db_session.execute(select(ItemEdit))).scalars())
    assert {row.id for row in rows} == {first.id, second.id}
    assert seed.item.grade == "K55" and seed.version.current_state == "draft"


async def test_unfinalized_and_cross_version_targets_are_rejected(db_session):
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session)
    other = await seed_record_version(db_session, finalized=False)
    service = RecordService(RecordRepository(db_session))
    for version, target, method, code in [
        (other.version.id, other.item.id, "edit", "E_NOT_FOUND"),
        (seed.version.id, other.item.id, "edit", "E_NOT_FOUND"),
        (seed.version.id, other.item.id, "confirm", "E_TARGET_INVALID"),
    ]:
        data = (
            edit_data(item_id=target)
            if method == "edit"
            else {"kind": "row_match", "item_id": target, "recorded_by": "person"}
        )
        with pytest.raises(DraftError) as error:
            await getattr(service, method)(version, data)
        assert error.value.code == code


async def test_confirmation_cancel_repeat_and_judged_unresolved(db_session):
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session)
    q = Question(
        version_id=seed.version.id,
        item_id=seed.item.id,
        question_code="Q1",
        target_field="grade",
        reason="confirm",
    )
    db_session.add(q)
    await db_session.commit()
    service = RecordService(RecordRepository(db_session))
    first = await service.confirm(
        seed.version.id,
        {"kind": "row_match", "item_id": seed.item.id, "recorded_by": "person"},
    )
    await service.undo_confirmation(
        seed.version.id, first.id, {"recorded_by": "undo person"}
    )
    second = await service.confirm(
        seed.version.id,
        {"kind": "row_match", "item_id": seed.item.id, "recorded_by": "person"},
    )
    assert first.id != second.id
    judgement = await service.judge(
        seed.version.id,
        q.id,
        {"status": "judged", "resolution": "unresolved", "recorded_by": "person"},
    )
    assert judgement.status == "judged" and judgement.resolution == "unresolved"
    assert len(list((await db_session.execute(select(Confirmation))).scalars())) == 2
    assert (
        len(list((await db_session.execute(select(QuestionJudgement))).scalars())) == 1
    )


async def test_unique_translation_is_limited_to_active_confirmation_constraint(
    db_session
):
    from app.repositories.record_repository import RecordRepository

    seed = await seed_record_version(db_session)
    version_id, item_id = seed.version.id, seed.item.id
    repo = RecordRepository(db_session)
    data = {
        "kind": "coverage",
        "item_id": None,
        "recorded_by": "person",
        "recorded_at": datetime.now(UTC),
    }
    async with repo.record(version_id):
        first_id = (await repo.save_confirmation(version_id, data)).id
    with pytest.raises(DraftError) as error:
        async with repo.record(version_id):
            await repo.save_confirmation(version_id, data)
    assert error.value.code == "E_ALREADY_CONFIRMED"
    with pytest.raises(DraftError) as error:
        async with repo.record(version_id):
            await repo.save_confirmation(
                version_id,
                {**data, "id": first_id, "kind": "row_match", "item_id": item_id},
            )
    assert error.value.code == "E_VALIDATION_FAILED"


async def test_version_lock_serializes_current_old_value_across_sessions(db_session):
    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session)
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    started = asyncio.Event()
    worker_pid = []

    async def second_write():
        async with sessions() as session:
            worker_pid.append(
                (await session.execute(text("SELECT pg_backend_pid()"))).scalar_one()
            )
            started.set()
            return await RecordService(RecordRepository(session)).edit(
                seed.version.id, edit_data(item_id=seed.item.id, new_value="N80")
            )

    async with sessions() as first_session:
        repo = RecordRepository(first_session)
        async with repo.record(seed.version.id):
            await repo.save_edits(
                seed.version.id,
                [
                    {
                        **edit_data(item_id=seed.item.id),
                        "old_value": "K55",
                        "old_state": "stated",
                        "recorded_at": datetime.now(UTC),
                    }
                ],
            )
            task = asyncio.create_task(second_write())
            try:
                await asyncio.wait_for(started.wait(), timeout=2)
                blockers = []
                for _ in range(100):
                    blockers = (
                        await db_session.execute(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": worker_pid[0]},
                        )
                    ).scalar_one()
                    if blockers:
                        break
                    await asyncio.sleep(0.01)
                assert blockers and not task.done()
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
        rows = await asyncio.wait_for(task, timeout=2)
    assert rows[0].old_value == "L80" and rows[0].new_value == "N80"
