"""Human-record constraints must be enforced by PostgreSQL itself."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.fixtures.record_data import seed_record_version


@pytest.mark.parametrize(
    "changes,sqlstate",
    [
        ({"recorded_by": " "}, "23514"),
        ({"reason": " "}, "23514"),
        ({"new_value": None, "new_state": None}, "23514"),
        ({"field": "grade_raw"}, "23514"),
        ({"new_state": "unknown"}, "23514"),
        ({"undone_at": datetime.now(UTC), "undone_by": " "}, "23514"),
        ({"undone_at": datetime.now(UTC), "undone_by": None}, "23514"),
        ({"version_id": "other"}, "23503"),
    ],
)
async def test_item_edit_constraints_in_postgres(db_session, changes, sqlstate):
    seed = await seed_record_version(db_session)
    other = await seed_record_version(db_session)
    values = dict(
        version_id=seed.version.id,
        item_id=seed.item.id,
        field="grade",
        new_value="L80",
        new_state="stated",
        reason="reason",
        recorded_by="person",
        recorded_at=datetime.now(UTC),
        undone_at=None,
        undone_by=None,
    )
    values.update(changes)
    if values["version_id"] == "other":
        values["version_id"] = other.version.id
    with pytest.raises(IntegrityError) as error:
        await db_session.execute(
            text(
                "INSERT INTO item_edits ("
                + ",".join(values)
                + ") VALUES ("
                + ",".join(":" + field for field in values)
                + ")"
            ),
            values,
        )
    assert error.value.orig.sqlstate == sqlstate


@pytest.mark.parametrize("kind", ["row_match", "coverage"])
async def test_confirmation_unique_excludes_undone_rows(db_session, kind):
    seed = await seed_record_version(db_session)
    values = {
        "version_id": seed.version.id,
        "kind": kind,
        "item_id": seed.item.id if kind == "row_match" else None,
        "recorded_by": "person",
        "recorded_at": datetime.now(UTC),
    }
    insert = text(
        "INSERT INTO confirmations(version_id,kind,item_id,recorded_by,recorded_at) VALUES (:version_id,:kind,:item_id,:recorded_by,:recorded_at) RETURNING id"
    )
    first_id = (await db_session.execute(insert, values)).scalar_one()
    await db_session.commit()
    with pytest.raises(IntegrityError) as error:
        await db_session.execute(insert, values)
    assert error.value.orig.sqlstate == "23505"
    await db_session.rollback()
    await db_session.execute(
        text(
            "UPDATE confirmations SET undone_at=:at, undone_by='undo person' WHERE id=:id"
        ),
        {"at": datetime.now(UTC), "id": first_id},
    )
    second_id = (await db_session.execute(insert, values)).scalar_one()
    assert second_id != first_id


@pytest.mark.parametrize(
    "table,values",
    [
        ("confirmations", {"kind": "coverage", "item_id": "item"}),
        ("confirmations", {"kind": "row_match", "item_id": None}),
        ("confirmations", {"kind": "coverage", "item_id": None, "recorded_by": " "}),
        (
            "confirmations",
            {
                "kind": "coverage",
                "item_id": None,
                "undone_at": datetime.now(UTC),
                "undone_by": None,
            },
        ),
        ("question_judgements", {"status": "unknown", "resolution": "unresolved"}),
        ("question_judgements", {"status": "judged", "resolution": "unknown"}),
        (
            "question_judgements",
            {"status": "judged", "resolution": "resolved", "recorded_by": " "},
        ),
    ],
)
async def test_confirmation_and_judgement_checks(db_session, table, values):
    from app.models import Question

    seed = await seed_record_version(db_session)
    values = {"recorded_by": "person", "recorded_at": datetime.now(UTC), **values}
    if table == "confirmations":
        values["version_id"] = seed.version.id
        if values["item_id"] == "item":
            values["item_id"] = seed.item.id
    else:
        question = Question(
            version_id=seed.version.id,
            question_code="Q",
            target_field="qty",
            reason="confirm",
        )
        db_session.add(question)
        await db_session.flush()
        values["question_id"] = question.id
    with pytest.raises(IntegrityError) as error:
        await db_session.execute(
            text(
                f"INSERT INTO {table} ("
                + ",".join(values)
                + ") VALUES ("
                + ",".join(":" + field for field in values)
                + ")"
            ),
            values,
        )
    assert error.value.orig.sqlstate == "23514"


async def test_migration_and_orm_have_the_same_named_checks_and_indexes(db_session):
    from sqlalchemy import CheckConstraint, inspect
    from app.models import ItemEdit, Confirmation, QuestionJudgement

    connection = await db_session.connection()
    for model in (ItemEdit, Confirmation, QuestionJudgement):
        table = model.__table__
        checks = await connection.run_sync(
            lambda conn: inspect(conn).get_check_constraints(table.name)
        )
        indexes = await connection.run_sync(
            lambda conn: inspect(conn).get_indexes(table.name)
        )
        assert {c["name"] for c in checks} == {
            c.name for c in table.constraints if isinstance(c, CheckConstraint)
        }
        assert {index["name"] for index in indexes} == {
            index.name for index in table.indexes
        }
