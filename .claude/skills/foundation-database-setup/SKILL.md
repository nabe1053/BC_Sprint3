---
name: foundation-database-setup
description: 初期的なデータベーススキーマ設計・ORM モデル実装・マイグレーション設定
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Slice 0-3: Database Design & Implementation

設計ドキュメント（04-db.md）に基づいて、
PostgreSQL スキーマを実装し、SQLAlchemy ORM モデルを作成するスキル。

## Purpose

データベースの基盤を構築する：

1. `docs/requirements/04-db.md` を読み込む
2. SQLAlchemy ORM モデルを実装
3. Alembic マイグレーション設定
4. 初期マイグレーション実行
5. リポジトリパターンの基盤実装

## When to use

- Slice 0-2（PostgreSQL セットアップ）完了後に実行
- データベーススキーマを実装したい
- ORM モデルを定義したい

## Prerequisites

- Slice 0-2（PostgreSQL Docker）が完了していること
- `docs/requirements/04-db.md` が存在すること

## Inputs

必ず確認するドキュメント：
- `docs/requirements/04-db.md` - ER図・テーブル定義

## Outputs

ファイル構成：
```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 # Base モデル（新規）
│   │   ├── user.py                 # User テーブル
│   │   └── ...                     # その他テーブル
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseRepository（新規）
│   │   ├── user_repository.py      # User 操作
│   │   └── ...                     # その他リポジトリ
│   └── core/
│       ├── database.py
│       └── dependencies.py
├── alembic/                        # マイグレーション（新規）
│   ├── versions/
│   │   └── 001_initial.py
│   ├── env.py
│   ├── script.py.mako
│   └── alembic.ini
└── pyproject.toml
```

## Procedure

### Step 1: 04-db.md を確認

`docs/requirements/04-db.md` を読み込み、以下を確認：

- [ ] テーブル一覧を確認した
- [ ] 各テーブルのカラム・型を確認した
- [ ] 主キー・外部キーを確認した
- [ ] インデックス・制約を確認した

### Step 2: Alembic を初期化

```bash
cd backend

# Alembic 初期化
alembic init alembic

# alembic/env.py を編集（SQLAlchemy async 対応）
```

**alembic/env.py 修正**:

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.database import Base
from app.core.config import settings

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_loader.get_section_names()[0])
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Step 3: SQLAlchemy モデルを実装

04-db.md に基づいて、モデルを作成：

#### 3-1. Base モデル（共通フィールド）

```python
# app/models/base.py
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from app.core.database import Base

class BaseModel(Base):
    """全テーブル共通フィールド"""
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

#### 3-2. テーブルモデルを作成

例（User テーブル）：

```python
# app/models/user.py
from sqlalchemy import Column, String, Boolean, Index
from app.models.base import BaseModel

class User(BaseModel):
    """User テーブル"""
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
    )
```

#### 3-3. models/__init__.py を更新

```python
# app/models/__init__.py
from app.models.base import BaseModel
from app.models.user import User

__all__ = ["BaseModel", "User"]
```

### Step 4: Pydantic スキーマを実装

API の入出力型を定義：

```python
# app/api/v1/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Step 5: BaseRepository を実装

```python
# app/repositories/base.py
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.base import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """汎用リポジトリベースクラス"""

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get(self, id: int) -> Optional[T]:
        """ID でレコード取得"""
        return await self.session.get(self.model, id)

    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """リスト取得"""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, obj: T) -> T:
        """レコード作成"""
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: int, update_data: dict) -> Optional[T]:
        """レコード更新"""
        obj = await self.get(id)
        if obj:
            for key, value in update_data.items():
                setattr(obj, key, value)
            await self.session.commit()
            await self.session.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """レコード削除"""
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False
```

### Step 6: User リポジトリを実装

```python
# app/repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.repositories.base import BaseRepository
from typing import Optional

class UserRepository(BaseRepository[User]):
    """User テーブル操作"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> Optional[User]:
        """メールアドレスでユーザー取得"""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """ユーザー名でユーザー取得"""
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
```

### Step 7: 初期マイグレーションを作成

```bash
cd backend

# マイグレーション生成（自動検出）
alembic revision --autogenerate -m "Initial migration"

# マイグレーション実行
alembic upgrade head
```

**確認項目**:
- [ ] alembic/versions/ に 001_initial.py が生成された
- [ ] pgAdmin でテーブルが作成されたことを確認

### Step 8: データベース接続テストを更新

```python
# app/main.py のテストエンドポイントを更新
from app.repositories.user_repository import UserRepository
from app.core.dependencies import get_db

@app.get("/api/v1/db-schema-test", tags=["Health"])
async def db_schema_test(session: AsyncSession = Depends(get_db)):
    """Schema テスト：Users テーブルが存在するか確認"""
    try:
        user_repo = UserRepository(session)
        users = await user_repo.list(limit=1)
        return {
            "status": "Schema OK",
            "users_table_exists": True,
            "count": len(users)
        }
    except Exception as e:
        return {
            "status": "Schema error",
            "error": str(e)
        }
```

### Step 9: マイグレーション管理

**マイグレーションを実行**:

```bash
# マイグレーション状態確認
alembic current

# マイグレーション実行
alembic upgrade head

# ロールバック（開発時）
alembic downgrade -1
```

## チェックリスト

### Slice 0-3 完了時

- [ ] 04-db.md を確認した
- [ ] Alembic を初期化した
- [ ] SQLAlchemy モデルを実装した
  - [ ] BaseModel（共通フィールド）
  - [ ] テーブルモデル（User など）
- [ ] Pydantic スキーマを実装した
- [ ] BaseRepository を実装した
- [ ] ユーザー固有リポジトリを実装した
- [ ] マイグレーション生成・実行完了
- [ ] pgAdmin でテーブル確認完了
- [ ] DB スキーマテスト成功

### 次のステップ

Slice 0-3 完了後は、**Slice 0-4: Authentication Middleware を実行**

```
Slice 0-1: FastAPI セットアップ
  ↓
Slice 0-2: PostgreSQL Docker
  ↓
Slice 0-3（ここ）
  ↓
Slice 0-4: Authentication Middleware (JWT/Cookie)
  ↓
Slice 0-5: Frontend Setup
```

## 参考資料

- [SQLAlchemy ORM Documentation](https://docs.sqlalchemy.org/en/20/orm/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
