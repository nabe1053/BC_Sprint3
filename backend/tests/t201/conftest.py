"""Isolated T-201 tests: no settings, credential files, live DB or destructive cleanup."""
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, declarative_base

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
database = sys.modules.get("app.core.database")
if database is None:
    database = types.ModuleType("app.core.database")
    database.Base = declarative_base()
    sys.modules["app.core.database"] = database


@compiles(BigInteger, "sqlite")
def bigint_sqlite(element, compiler, **kw):
    return "INTEGER"


@compiles(JSONB, "sqlite")
def jsonb_sqlite(element, compiler, **kw):
    return "JSON"


class AsyncTestSession:
    """Run repository SQL against a fresh in-memory database."""

    def __init__(self, session):
        self.sync = session

    def add(self, entity):
        self.sync.add(entity)

    def add_all(self, entities):
        self.sync.add_all(entities)

    async def execute(self, statement):
        return self.sync.execute(statement)

    async def get(self, model, key):
        return self.sync.get(model, key)

    async def flush(self):
        self.sync.flush()

    async def commit(self):
        self.sync.commit()

    async def rollback(self):
        self.sync.rollback()

    async def refresh(self, entity):
        self.sync.refresh(entity)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    for table in database.Base.metadata.tables.values():
        for index in table.indexes:
            condition = index.dialect_options["postgresql"].get("where")
            if condition is not None:
                index.dialect_options["sqlite"]["where"] = condition
    database.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as sync:
        yield AsyncTestSession(sync)
    engine.dispose()
