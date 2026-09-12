"""Check only the T-202 forward migration in a rollback-only PostgreSQL schema."""
from io import StringIO
from pathlib import Path
import runpy
import subprocess
from uuid import uuid4
from alembic.migration import MigrationContext
from alembic.operations import Operations


def rejected(statement, condition):
    return f"DO $c$ BEGIN BEGIN {statement}; RAISE EXCEPTION 'Constraint did not reject input'; EXCEPTION WHEN {condition} THEN NULL; END; END $c$;"


def main():
    buffer = StringIO()
    migration = runpy.run_path(
        str(
            Path(__file__).resolve().parents[1]
            / "alembic/versions/t202_run_metadata.py"
        )
    )
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buffer}
    )
    with Operations.context(context):
        migration["upgrade"]()
    schema = "t202_check_" + uuid4().hex
    parts = [
        "BEGIN;",
        "DO $c$ BEGIN IF current_database()<>'octg_test' THEN RAISE EXCEPTION 'Test database required'; END IF; END $c$;",
        f"CREATE SCHEMA {schema};",
        f"SET LOCAL search_path TO {schema};",
        "CREATE TABLE rule_sets (id bigint PRIMARY KEY);",
        "CREATE TABLE agent_run_steps (id bigint PRIMARY KEY);",
        "CREATE TABLE agent_runs (id bigint PRIMARY KEY,case_id bigint NOT NULL,outcome text NOT NULL,stop_reason text);",
        "INSERT INTO rule_sets VALUES (1),(2);",
        "INSERT INTO agent_runs VALUES (1,1,'failed','failed');",
        buffer.getvalue(),
        "DO $c$ BEGIN IF EXISTS(SELECT 1 FROM rule_sets WHERE is_current) THEN RAISE EXCEPTION 'Current rule inferred'; END IF; IF (SELECT impl_version FROM agent_runs WHERE id=1)<>'legacy-unrecorded' THEN RAISE EXCEPTION 'Missing legacy marker'; END IF; END $c$;",
        "UPDATE rule_sets SET is_current=true WHERE id=1;",
        rejected("UPDATE rule_sets SET is_current=true WHERE id=2", "unique_violation"),
        "INSERT INTO agent_runs VALUES (2,1,'running',NULL,'t202-test','{}');",
        rejected(
            "INSERT INTO agent_runs VALUES (3,1,'running',NULL,'t202-test','{}')",
            "unique_violation",
        ),
        "INSERT INTO agent_runs VALUES (4,2,'running',NULL,'t202-test','{}');",
        rejected(
            "INSERT INTO agent_runs VALUES (5,3,'stopped','timeout','t202-test','{}')",
            "check_violation",
        ),
        rejected(
            "INSERT INTO agent_runs (id,case_id,outcome) VALUES (6,3,'running')",
            "not_null_violation",
        ),
        "UPDATE agent_runs SET outcome='stopped',stop_reason='outer_timeout' WHERE id=2;",
        "INSERT INTO agent_runs VALUES (7,1,'running',NULL,'t202-test','{}');",
        "ROLLBACK;",
    ]
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
        # This SQL contains synthetic data only, but don't print arbitrary server diagnostics.
        print("T-202 PostgreSQL check failed; no transaction committed.")
        raise SystemExit(result.returncode)
    print(
        "PASS: T-202 migration, legacy markers, 4 rejection checks, restart after terminal state; rolled back."
    )


if __name__ == "__main__":
    main()
