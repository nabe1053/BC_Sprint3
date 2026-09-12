"""tests/integration/test_api_* 共通フィクスチャ（T-102 RED）。

`client` は実 DB（`tests/conftest.py` の `db_session`）を使う `TestClient` を返す。
`get_db` だけを override するため、Presentation 層より内側（Service/Repository）は
実装が呼ばれる。実装が無い間は該当ルートが存在せず 404 になり、それ自体が
RED として機能する（実装後は実際の業務ロジックを通ることを検証できる）。

期待する公開インタフェース（実装側が用意するもの）:
    app.core.database.get_db  # 既存。FastAPI の Depends で override 対象にする
"""

from collections.abc import AsyncGenerator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from datetime import UTC, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core import database
from app.models import Case, RuleSet, Document, DocumentPage
from tests.fixtures.sqlite_support import configure_sqlite_metadata


@pytest.fixture
def client(db_session, monkeypatch) -> Iterator[TestClient]:
    """実 DB（db_session）を使う TestClient。"""

    async def _override_get_db() -> AsyncGenerator:
        yield db_session

    def reject_development_session():
        raise AssertionError("Integration TestClient must not open the development DB")

    monkeypatch.setattr(database, "AsyncSessionLocal", reject_development_session)

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


# SQLite repository fixtures shared by draft/run integration tests.
# Normal pytest collection uses the real Base; no sys.modules settings/DB stubs.
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
    configure_sqlite_metadata(database.Base.metadata)
    database.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as sync:
        yield AsyncTestSession(sync)
    engine.dispose()


class SyncConnectionAdapter:
    def __init__(self, connection):
        self.connection = connection

    async def run_sync(self, callback):
        return callback(self.connection)


async def _connection(self):
    return SyncConnectionAdapter(self.sync.connection())


AsyncTestSession.connection = _connection


@pytest.fixture
async def seeded(session):
    case = Case(case_code="SEED-CASE")
    rule = RuleSet(rule_version="active", rules={}, is_current=True)
    session.add_all([case, rule])
    await session.flush()
    newer = RuleSet(rule_version="newer-not-current", rules={})
    doc = Document(
        case_id=case.id,
        file_name="synthetic.txt",
        storage_path="/synthetic",
        kind="text",
        read_status="partial",
        received_at=datetime.now(UTC),
    )
    session.add_all([newer, doc])
    await session.flush()
    session.add(
        DocumentPage(document_id=doc.id, locator="body:1", seq=1, text="Synthetic")
    )
    await session.commit()
    return case, rule, doc
