"""Export the real route schema without reading runtime settings or opening a DB.

The ordinary exporter remains available for normal development. These public dummy
settings exist only for schema construction; no server is started by this script.
"""
import json
import sys
import types
from pathlib import Path
from sqlalchemy.orm import declarative_base

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def export():
    database = types.ModuleType("app.core.database")
    database.Base = declarative_base()

    async def no_database():
        raise RuntimeError("Schema export cannot access a database")
        yield

    database.get_db = no_database
    config = types.ModuleType("app.core.config")
    config.settings = types.SimpleNamespace(
        APP_NAME="OCTG Item List Agent API",
        APP_VERSION="0.1.0",
        DEBUG=False,
        ALLOWED_ORIGINS=[],
        STORAGE_ROOT="/unused/schema-export",
        MAX_DOCUMENTS_PER_CASE=50,
        MAX_FILE_SIZE_MB=20,
        MAX_PDF_PAGES=200,
        MAX_XLSX_SHEETS=50,
    )
    sys.modules["app.core.database"] = database
    sys.modules["app.core.config"] = config
    from app.main import app

    path = BACKEND / "openapi.json"
    path.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Exported {len(app.openapi()['paths'])} route paths to {path}")


if __name__ == "__main__":
    export()
