"""Validate the live scan index and synthetic T-201 constraints in PostgreSQL.

make check-run-step-index checks both existing databases read-only (--index-only).
Without that flag, also validate synthetic constraints in octg_test, rolled back.
No credential files, application settings, source documents or live rows are read.
"""
import argparse
import os
from io import StringIO
from pathlib import Path
import runpy
import subprocess
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import make_url


def connection_targets():
    # Makefile owns local Docker targets; parse the existing TEST_DB URL without
    # logging its credentials or importing application settings.
    return (
        os.environ["INDEX_CONTAINER"],
        os.environ["INDEX_USER"],
        os.environ["INDEX_DEV_DATABASE"],
        make_url(os.environ["INDEX_TEST_URL"]).database,
    )


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


def check_live_scan_index():
    """Inspect the migrated public schema, not Base.metadata.create_all()."""
    sql = """BEGIN READ ONLY;
DO $check$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_index i
        JOIN pg_class idx ON idx.oid = i.indexrelid
        JOIN pg_class tbl ON tbl.oid = i.indrelid
        JOIN pg_namespace ns ON ns.oid = tbl.relnamespace
        JOIN pg_am am ON am.oid = idx.relam
        WHERE ns.nspname = 'public' AND tbl.relname = 'agent_run_steps'
          AND idx.relname = 'ix_agent_run_steps_document_locator'
          AND i.indisvalid AND i.indisready AND NOT i.indisunique
          AND i.indpred IS NULL AND i.indexprs IS NULL
          AND i.indnkeyatts = 2 AND i.indnatts = 2 AND am.amname = 'btree'
          AND pg_get_indexdef(i.indexrelid, 1, true) = 'document_id'
          AND pg_get_indexdef(i.indexrelid, 2, true) = 'locator'
    ) THEN
        RAISE EXCEPTION 'Missing or invalid ix_agent_run_steps_document_locator';
    END IF;
END $check$;
SELECT current_database() AS database, indexdef FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'agent_run_steps'
  AND indexname = 'ix_agent_run_steps_document_locator';
ROLLBACK;"""
    container, user, development, testing = connection_targets()
    failed = False
    for database in (development, testing):
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                container,
                "psql",
                "-X",
                "-w",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                user,
                "-d",
                database,
            ],
            input=sql,
            text=True,
            capture_output=True,
        )
        print(f"{database}: {'FAIL' if result.returncode else 'PASS'}")
        print(result.stderr if result.returncode else result.stdout)
        failed |= bool(result.returncode)
    if failed:
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()
    check_live_scan_index()
    if args.index_only:
        return
    container, user, _, testing = connection_targets()
    quoted_testing = testing.replace("'", "''")
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
        f"DO $check$ BEGIN IF current_database() <> '{quoted_testing}' THEN RAISE EXCEPTION 'Test database required'; END IF; END $check$;",
        f"CREATE SCHEMA {schema};",
        f"SET LOCAL search_path TO {schema};",
        "CREATE TABLE versions (id bigint PRIMARY KEY);",
        "CREATE TABLE documents (id bigint PRIMARY KEY);",
        "CREATE TABLE agent_run_steps (id bigint PRIMARY KEY, document_id bigint, locator text);",
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
            container,
            "psql",
            "-X",
            "-w",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            user,
            "-d",
            testing,
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
