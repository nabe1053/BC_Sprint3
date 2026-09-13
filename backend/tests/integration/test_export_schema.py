"""Export metadata constraints are enforced by PostgreSQL."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.fixtures.record_data import seed_record_version


from tests.fixtures.export_data import export_values


async def insert(session, values):
    return (
        await session.execute(
            text(
                f"INSERT INTO exports ({','.join(values)}) VALUES ({','.join(':'+key for key in values)}) RETURNING id,created_at,updated_at"
            ),
            values,
        )
    ).one()


@pytest.mark.parametrize(
    "changes",
    [
        dict(state_at_export="pending"),
        dict(sendoff_at_export="yes"),
        dict(unresolved_at_export=-1),
        dict(file_name=" "),
        dict(storage_path=" "),
        dict(content_hash=" "),
    ],
)
async def test_export_checks_in_postgres(db_session, changes):
    seed = await seed_record_version(db_session)
    values = {**export_values(seed.version.id), **changes}
    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            await insert(db_session, values)
    assert error.value.orig.sqlstate == "23514"


async def test_only_one_initial_export_but_multiple_subsequent_exports(db_session):
    seed = await seed_record_version(db_session)
    values = export_values(seed.version.id)
    first = await insert(db_session, {**values, "is_initial": True})
    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            await insert(db_session, {**values, "is_initial": True})
    assert error.value.orig.sqlstate == "23505"
    second = await insert(db_session, values)
    third = await insert(db_session, values)
    assert len({first.id, second.id, third.id}) == 3
    assert first.created_at and first.updated_at
