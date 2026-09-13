"""PostgreSQL owns approval constraints, independently of input validation."""
from datetime import UTC, datetime
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.fixtures.record_data import seed_record_version


@pytest.mark.parametrize(
    "table,changes,code",
    [
        ("version_state_events", {"to_state": "draft"}, "23514"),
        ("version_state_events", {"from_state": "staff_checked"}, "23514"),
        ("version_state_events", {"from_state": "unknown"}, "23514"),
        ("version_state_events", {"recorded_by": " "}, "23514"),
        ("bounces", {"reason": " "}, "23514"),
        ("bounces", {"recorded_by": " "}, "23514"),
        ("bounce_comments", {"comment": " "}, "23514"),
        ("bounce_comments", {"recorded_by": " "}, "23514"),
        ("bounce_comments", {"item_id": "other"}, "23503"),
        ("sendoff_decisions", {"decision": "hold", "reason": None}, "23514"),
        ("sendoff_decisions", {"decision": "approved", "reason": " "}, "23514"),
        ("sendoff_decisions", {"decision": "unknown"}, "23514"),
        ("sendoff_decisions", {"recorded_by": " "}, "23514"),
    ],
)
async def test_approval_constraints_are_enforced_in_postgres(
    db_session, table, changes, code
):
    seed = await seed_record_version(db_session)
    other = await seed_record_version(db_session)
    values = {
        "version_id": seed.version.id,
        "recorded_by": "person",
        "recorded_at": datetime.now(UTC),
    }
    values.update(
        {
            "version_state_events": {
                "from_state": "draft",
                "to_state": "staff_checked",
                "unresolved_count": 0,
            },
            "bounces": {"reason": "R1: note"},
            "bounce_comments": {"item_id": seed.item.id, "comment": "note"},
            "sendoff_decisions": {"decision": "approved", "reason": "condition"},
        }[table]
    )
    values.update(changes)
    if values.get("item_id") == "other":
        values["item_id"] = other.item.id
    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            await db_session.execute(
                text(
                    f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join(':'+key for key in values)})"
                ),
                values,
            )
    assert error.value.orig.sqlstate == code


async def test_undecided_allows_no_reason_and_records_are_append_only(db_session):
    seed = await seed_record_version(db_session)
    statement = text(
        "INSERT INTO sendoff_decisions(version_id,decision,recorded_by,recorded_at) VALUES (:version,'undecided','person',:at) RETURNING id,created_at"
    )
    first = (
        await db_session.execute(
            statement, {"version": seed.version.id, "at": datetime.now(UTC)}
        )
    ).one()
    second = (
        await db_session.execute(
            statement, {"version": seed.version.id, "at": datetime.now(UTC)}
        )
    ).one()
    assert (
        first.id != second.id
        and first.created_at is not None
        and second.created_at is not None
    )


async def test_unfinalized_version_cannot_acquire_checked_cache(db_session):
    seed = await seed_record_version(db_session, finalized=False)
    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            await db_session.execute(
                text("UPDATE versions SET current_state='staff_checked' WHERE id=:id"),
                {"id": seed.version.id},
            )
    assert error.value.orig.sqlstate == "23514"
