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


@pytest.fixture
def client(db_session) -> Iterator[TestClient]:
    """実 DB（db_session）を使う TestClient。"""

    async def _override_get_db() -> AsyncGenerator:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
