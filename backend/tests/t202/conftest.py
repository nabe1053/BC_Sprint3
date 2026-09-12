"""T-202 isolated tests. Never load environment files or the root test configuration."""
import importlib.util
from datetime import UTC, datetime
import pytest
import sys
import types
from pathlib import Path

support_path = Path(__file__).resolve().parents[1] / "t201/conftest.py"
spec = importlib.util.spec_from_file_location("t201_isolated_support", support_path)
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
session = support.session


async def unused_db():
    raise RuntimeError("Tests must inject a session")
    yield


database = sys.modules["app.core.database"]
if not hasattr(database, "get_db"):
    database.get_db = unused_db
if "app.core.config" not in sys.modules:
    config = types.ModuleType("app.core.config")
    config.settings = types.SimpleNamespace(
        APP_NAME="Isolated T202 API",
        APP_VERSION="0.1.0",
        DEBUG=False,
        ALLOWED_ORIGINS=[],
        MAX_DOCUMENTS_PER_CASE=50,
        MAX_FILE_SIZE_MB=20,
        MAX_PDF_PAGES=200,
        MAX_XLSX_SHEETS=50,
        STORAGE_ROOT="/tmp/t202-test-storage",
    )
    sys.modules["app.core.config"] = config


class TestConnection:
    def __init__(self, connection):
        self.connection = connection

    async def run_sync(self, callback):
        return callback(self.connection)


async def test_connection(self):
    return TestConnection(self.sync.connection())


support.AsyncTestSession.connection = test_connection

from app.models import Case, RuleSet, Document, DocumentPage  # noqa: E402


@pytest.fixture
async def seeded(session):
    case = Case(case_code="T202")
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
