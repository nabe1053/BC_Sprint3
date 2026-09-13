"""Event/cache atomicity and real version-lock serialization."""
import asyncio
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.domain.draft_errors import DraftError
from app.models import Version, VersionStateEvent, BounceComment
from app.repositories.record_repository import RecordRepository
from tests.fixtures.record_data import seed_record_version, record_actor


async def test_event_and_cached_state_commit_or_rollback_together(db_session):
    seed = await seed_record_version(db_session)
    version_id = seed.version.id
    repo = RecordRepository(db_session)
    with pytest.raises(RuntimeError):
        async with repo.record(version_id) as version:
            assert version.id == version_id
            await repo.save_state_event(
                version,
                from_state="draft",
                to_state="staff_checked",
                unresolved_count=2,
                **record_actor(),
            )
            raise RuntimeError("rollback")
    assert (
        await db_session.get(Version, version_id, populate_existing=True)
    ).current_state == "draft"
    assert list((await db_session.execute(select(VersionStateEvent))).scalars()) == []
    async with repo.record(version_id) as version:
        event = await repo.save_state_event(
            version,
            from_state="draft",
            to_state="staff_checked",
            unresolved_count=2,
            **record_actor(),
        )
    assert (
        await db_session.get(Version, version_id, populate_existing=True)
    ).current_state == "staff_checked"
    assert {
        row.id
        for row in (await db_session.execute(select(VersionStateEvent))).scalars()
    } == {event.id}


async def test_two_sessions_block_then_reject_repeated_transition(db_session):
    from app.services.approval_service import ApprovalService

    seed = await seed_record_version(db_session)
    version_id, item_id = seed.version.id, seed.item.id
    repo = RecordRepository(db_session)
    async with repo.record(version_id):
        await repo.save_confirmation(
            version_id, {"kind": "row_match", "item_id": item_id, **record_actor()}
        )
        await repo.save_confirmation(
            version_id, {"kind": "coverage", "item_id": None, **record_actor()}
        )
    sessions = async_sessionmaker(db_session.bind, expire_on_commit=False)
    started = asyncio.Event()
    worker_pid = []

    async def second():
        async with sessions() as session:
            worker_pid.append(
                (await session.execute(text("SELECT pg_backend_pid()"))).scalar_one()
            )
            # Prime the identity map before the lock; lock re-read must refresh it.
            stale = await session.get(Version, version_id)
            assert stale.current_state == "draft"
            started.set()
            return await ApprovalService(RecordRepository(session)).transition(
                version_id, {"recorded_by": "second", "to_state": "staff_checked"}
            )

    async with sessions() as first_session:
        first = RecordRepository(first_session)
        async with first.record(version_id) as version:
            first_pid = (
                await first_session.execute(text("SELECT pg_backend_pid()"))
            ).scalar_one()
            task = asyncio.create_task(second())
            try:
                await asyncio.wait_for(started.wait(), 2)
                blockers = []
                for _ in range(100):
                    blockers = (
                        await db_session.execute(
                            text("SELECT pg_blocking_pids(:pid)"),
                            {"pid": worker_pid[0]},
                        )
                    ).scalar_one()
                    if first_pid in blockers:
                        break
                    await asyncio.sleep(0.01)
                assert first_pid in blockers and not task.done()
                saved = await first.save_state_event(
                    version,
                    from_state="draft",
                    to_state="staff_checked",
                    unresolved_count=0,
                    **record_actor("first"),
                )
            except BaseException:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                raise
        with pytest.raises(DraftError) as error:
            await asyncio.wait_for(task, 2)
    assert error.value.code == "E_STATE_ORDER"
    assert {
        row.id
        for row in (await db_session.execute(select(VersionStateEvent))).scalars()
    } == {saved.id}
    assert (
        await db_session.get(Version, version_id, populate_existing=True)
    ).current_state == "staff_checked"


async def test_bounce_links_comments_once_without_changing_state_or_events(db_session):
    seed = await seed_record_version(db_session, state="staff_checked")
    repo = RecordRepository(db_session)
    version_id = seed.version.id
    before = {
        row.id
        for row in (await db_session.execute(select(VersionStateEvent))).scalars()
    }
    async with repo.record(version_id):
        old = await repo.save_bounce_comment(
            version_id, {"item_id": seed.item.id, "comment": "first", **record_actor()}
        )
        first = await repo.save_bounce(
            version_id, {"reason": "R1: first", **record_actor()}, [old]
        )
    async with repo.record(version_id):
        new = await repo.save_bounce_comment(
            version_id, {"item_id": seed.item.id, "comment": "second", **record_actor()}
        )
        assert {row.id for row in await repo.unlinked_bounce_comments(version_id)} == {
            new.id
        }
        second = await repo.save_bounce(
            version_id, {"reason": "R1: second", **record_actor()}, [old, new]
        )
    assert (
        await db_session.get(BounceComment, old.id, populate_existing=True)
    ).bounce_id == first.id
    assert (
        await db_session.get(BounceComment, new.id, populate_existing=True)
    ).bounce_id == second.id
    assert (
        await db_session.get(Version, version_id, populate_existing=True)
    ).current_state == "staff_checked"
    assert {
        row.id
        for row in (await db_session.execute(select(VersionStateEvent))).scalars()
    } == before


async def test_bounce_failure_rolls_back_insert_and_comment_link(db_session):
    from app.models import Bounce

    seed = await seed_record_version(db_session, state="staff_checked")
    repo = RecordRepository(db_session)
    vid, item_id = seed.version.id, seed.item.id
    async with repo.record(vid):
        comment = await repo.save_bounce_comment(
            vid, {"item_id": item_id, "comment": "check", **record_actor()}
        )
    comment_id = comment.id
    with pytest.raises(RuntimeError):
        async with repo.record(vid):
            await repo.save_bounce(
                vid, {"reason": "R1: check", **record_actor()}, [comment]
            )
            raise RuntimeError("rollback")
    assert list((await db_session.execute(select(Bounce))).scalars()) == []
    assert (
        await db_session.get(BounceComment, comment_id, populate_existing=True)
    ).bounce_id is None
    assert (
        await db_session.get(Version, vid, populate_existing=True)
    ).current_state == "staff_checked"


async def test_approval_rejects_unfinalized_version_and_foreign_item(db_session):
    from app.services.approval_service import ApprovalService

    seed = await seed_record_version(db_session)
    pending = await seed_record_version(db_session, finalized=False)
    vid, pending_vid, pending_item_id = (
        seed.version.id,
        pending.version.id,
        pending.item.id,
    )
    service = ApprovalService(RecordRepository(db_session))
    for method, payload in [
        (
            "comment",
            {"item_id": pending_item_id, "comment": "check", "recorded_by": "人"},
        ),
        ("transition", {"to_state": "staff_checked", "recorded_by": "人"}),
        ("bounce", {"recorded_by": "人"}),
        ("decide_sendoff", {"decision": "undecided", "recorded_by": "人"}),
    ]:
        with pytest.raises(DraftError) as error:
            await getattr(service, method)(pending_vid, payload)
        assert error.value.code == "E_NOT_FOUND"
    with pytest.raises(DraftError) as error:
        await service.comment(
            vid,
            {
                "item_id": pending_item_id,
                "comment": "wrong version",
                "recorded_by": "人",
            },
        )
    assert error.value.code == "E_NOT_FOUND"
    assert list((await db_session.execute(select(BounceComment))).scalars()) == []
