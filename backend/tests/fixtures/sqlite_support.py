"""SQLite-only support for the in-memory repository fixtures.

Import registers the BigInteger/JSONB SQLite compilers process-wide, as before.
PostgreSQL compilers are unaffected. configure_sqlite_metadata mutates the shared
Base metadata's SQLite index options (not its PostgreSQL options); the old fixture
also retained these options after disposal. This extraction intentionally preserves
that behavior and is not a PostgreSQL migration or locking test.
"""
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(BigInteger, "sqlite")
def bigint_sqlite(element, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def jsonb_sqlite(element, compiler, **kw):
    return "JSON"


def configure_sqlite_metadata(metadata):
    for table in metadata.tables.values():
        for index in table.indexes:
            condition = index.dialect_options["postgresql"].get("where")
            if condition is not None:
                index.dialect_options["sqlite"]["where"] = condition
