"""Validate the T-201 forward migration in PostgreSQL, with no credential files or persistent changes.

Run from backend: .venv/bin/python scripts/check_t201_postgres.py
Only the existing local octg_postgres container and octg_test database are used.
Every object and synthetic row lives in a unique schema inside BEGIN ... ROLLBACK.
No application settings, existing migration files, source documents or table data are read.
"""
from io import StringIO
from pathlib import Path
import runpy
import subprocess
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations


def expect_failure(statement, condition):
    return f"""DO $check$ BEGIN
    BEGIN
        {statement};
        RAISE EXCEPTION 'Expected {condition}';
    EXCEPTION WHEN {condition} THEN NULL;
    END;
END $check$;"""


def item(row_id, version=1, **changes):
    values = dict(
        id=str(row_id),
        version_id=str(version),
        row_code=f"'{row_id}'",
        source_no=f"'{row_id}'",
        seq=str(row_id),
        kind="'casing'",
        kind_raw="'CSG'",
        grade_raw="'K55'",
        qty_raw="'9007199254740993 MT'",
        od_state="'not_stated'",
        wall_state="'not_stated'",
        weight_state="'not_stated'",
        grade_state="'not_stated'",
        connection_state="'not_stated'",
        length_state="'not_stated'",
        due_state="'not_stated'",
        place_state="'not_stated'",
        qty_state="'numeric'",
        qty_value="9007199254740993",
        qty_unit="'MT'",
    )
    values.update(changes)
    return (
        f"INSERT INTO items ({','.join(values)}) VALUES ({','.join(values.values())})"
    )


def main():
    buffer = StringIO()
    migration = runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "alembic/versions/t201_artifacts.py")
    )
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buffer}
    )
    with Operations.context(context):
        migration["upgrade"]()
    schema = "t201_check_" + uuid4().hex
    parts = [
        "BEGIN;",
        "DO $check$ BEGIN IF current_database() <> 'octg_test' THEN RAISE EXCEPTION 'Test database required'; END IF; END $check$;",
        f"CREATE SCHEMA {schema};",
        f"SET LOCAL search_path TO {schema};",
        "CREATE TABLE versions (id bigint PRIMARY KEY);",
        "CREATE TABLE documents (id bigint PRIMARY KEY);",
        "INSERT INTO versions VALUES (1),(2);",
        "INSERT INTO documents VALUES (1);",
        buffer.getvalue(),
        item(1) + ";",
        item(2) + ";",
        item(3, version=2) + ";",
        "DO $check$ BEGIN IF (SELECT qty_value FROM items WHERE id=1) <> 9007199254740993::numeric THEN RAISE EXCEPTION 'Lost numeric precision'; END IF; END $check$;",
    ]
    checks = [
        (item(10, qty_unit="NULL"), "check_violation"),
        (item(11, qty_state="'tba'", qty_value="0"), "check_violation"),
        (
            item(12, od_state="'stated'", od_value="1", od_unit="NULL"),
            "check_violation",
        ),
        (item(13, connection_state="'stated'"), "check_violation"),
        (item(14, candidate_label="'A'"), "check_violation"),
        (item(15, source_no="' '"), "check_violation"),
        (item(16, qty_state="NULL"), "not_null_violation"),
        (
            "INSERT INTO source_inventory_entries(version_id,document_id,position,seq,excerpt,status,basis) VALUES (1,1,'p.1',1,'total','excluded',NULL)",
            "check_violation",
        ),
        (
            "INSERT INTO source_inventory_entries(version_id,document_id,position,seq,excerpt,status,basis) VALUES (1,1,'p.1',1,'total','excluded',' ')",
            "check_violation",
        ),
        (
            "INSERT INTO questions(version_id,item_id,question_code,target_field,reason) VALUES (1,3,'Q1','qty','check')",
            "foreign_key_violation",
        ),
        (
            "INSERT INTO questions(version_id,question_code,reason) VALUES (1,'Q2','check')",
            "not_null_violation",
        ),
        (
            "INSERT INTO item_ends(item_id,side,od_value) VALUES (1,'end_a',1)",
            "check_violation",
        ),
    ]
    evidence = "INSERT INTO evidences(version_id,item_id,field,raw_value,adopted_value,document_id,locator,quote) VALUES "
    parts += [
        evidence + "(1,1,'qty','1 MT','1 MT',1,'p.1','synthetic');",
        evidence + "(1,2,'qty','1 MT','1 MT',1,'p.1','synthetic');",
        evidence + "(1,NULL,'qty','1 MT','1 MT',1,'p.1','synthetic');",
    ]
    checks += [
        (
            evidence + "(1,1,'qty','1 MT','1 MT',1,'p.1','synthetic')",
            "unique_violation",
        ),
        (
            evidence + "(1,NULL,'qty','1 MT','1 MT',1,'p.1','synthetic')",
            "unique_violation",
        ),
        (
            evidence + "(1,3,'qty','1 MT','1 MT',1,'p.1','synthetic')",
            "foreign_key_violation",
        ),
    ]
    parts += [expect_failure(statement, condition) for statement, condition in checks]
    parts += ["ROLLBACK;"]
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "octg_postgres",
            "psql",
            "-X",
            "-w",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "postgres",
            "-d",
            "octg_test",
        ],
        input="\n".join(parts),
        text=True,
        capture_output=True,
    )
    if result.returncode:
        print(result.stderr)
        raise SystemExit(result.returncode)
    print(
        f"PASS: PostgreSQL forward migration, exact numeric persistence, {len(checks)} constraint checks; rolled back."
    )


if __name__ == "__main__":
    main()
