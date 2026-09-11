"""pytest 共通設定。

T-101: Repository 層の統合テスト用に AsyncSession フィクスチャを追加する。
- テスト専用データベース（既定 `octg_test`）を使い、本番用 `octg_db` を壊さない。
- スキーマは事前に `alembic upgrade head` を **テスト DB に対して** 実行して作る
  （このファイルは作らない。用意手順は README/報告に書く）。
- テストごとにテーブルをまとめて TRUNCATE してデータを掃除する（外部キーがあるため
  トランザクションロールバックより TRUNCATE ... CASCADE の方が単純で確実）。
"""

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/octg_test",
)

# references/ の実データ（読取部品テストで使う）。backend/ の1つ上。
REFERENCES_DIR = Path(__file__).resolve().parents[2] / "references"

test_engine = create_async_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """テスト用 DB セッション。テストの前後でA層テーブルを空にする。

    スキーマ自体（テーブル）はテスト実行前に用意しておくこと
    （`DATABASE_URL=... uv run alembic upgrade head` をテスト DB に対して実行）。
    """
    async with test_engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        if table_names:
            await conn.exec_driver_sql(
                f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"
            )

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    # テスト内で commit したデータ（DocumentRepository/CaseRepository は commit する）は
    # rollback だけでは消えない。次のテストに漏らさないよう、ここでも掃除する
    # （reviewer 指摘 軽微-6）。
    async with test_engine.begin() as conn:
        table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        if table_names:
            await conn.exec_driver_sql(
                f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"
            )


@pytest.fixture
def references_dir() -> Path:
    return REFERENCES_DIR
