"""SQLAlchemy 2.0 AsyncSession 設定。

DB は PostgreSQL 16（ローカル Docker・docker-compose）。04-db.md 0.1 の決定に従う。
psycopg3 ドライバは async / sync の両方をサポートするため、Alembic（同期）と
アプリ（非同期）で同じ DSN スキーム（postgresql+psycopg://）を使う。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """全 ORM モデルの基底クラス。"""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依存注入用の DB セッション取得。"""
    async with AsyncSessionLocal() as session:
        yield session
