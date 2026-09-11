---
name: foundation-postgres-docker
description: PostgreSQL Docker セットアップ・docker-compose.yml 構成
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Slice 0-2: PostgreSQL Docker Setup

PostgreSQL を Docker で セットアップし、FastAPI との接続を確立するスキル。

## Purpose

PostgreSQL の Docker 環境を構築する：

1. docker-compose.yml を作成（PostgreSQL + pgAdmin）
2. SQLAlchemy の AsyncSession 設定
3. Database URL 設定
4. 接続テスト

## When to use

- Slice 0-1 完了後に実行
- PostgreSQL ローカル開発環境を構築したい
- Database とアプリケーションを Docker で統合したい

## Prerequisites

- Docker & Docker Compose がインストールされていること
- Slice 0-1（FastAPI 基盤）が完了していること

## Outputs

ファイル構成：
```
training-sprint2/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── database.py         # SQLAlchemy 設定 (NEW)
│   │   └── main.py
│   ├── pyproject.toml
│   └── Dockerfile                  # Docker 設定
├── docker-compose.yml              # Compose 設定 (NEW)
└── .env.example                    # 環境変数テンプレート
```

## Procedure

### Step 1: Docker & Docker Compose インストール確認

```bash
# Docker インストール確認
docker --version

# Docker Compose インストール確認
docker-compose --version
```

### Step 2: Docker パラメータを決定（ユーザー主導）

docker-compose.yml を作成する前に、以下の項目をご決定ください：

#### 2-1. PostgreSQL イメージを選択

**選択肢**：

```
A. postgres:16-alpine （推奨）
   - 軽量（140MB）
   - 本番環境向け
   - イメージサイズ：小

B. postgres:16
   - 完全版
   - 開発環境向け
   - イメージサイズ：中（約200MB）

C. postgres:15-alpine
   - 前バージョン（安定性重視）
   - 軽量
   - イメージサイズ：小
```

**推奨**: A（postgres:16-alpine）

#### 2-2. メモリ・リソース制限を決定

```
A. 制限なし（開発環境推奨）
   - memory: なし
   - cpus: なし

B. 制限あり（マシンリソース節約）
   - memory: 512M
   - cpus: 0.5

C. カスタム
   - memory: ___M
   - cpus: ___
```

**推奨**: A（開発環境なので制限なし）

#### 2-3. PostgreSQL ユーザー・パスワード・DB 名を決定

```
PostgreSQL User: postgres
                （デフォルトはpostgres）

PostgreSQL Password: ________
                （推奨: 強力なパスワード、開発環境でも指定）

Database Name: training_db
             （デフォルト: training_db、カスタム可）
```

#### 2-4. pgAdmin アクセス情報を決定

```
pgAdmin Email: admin@example.com
             （変更推奨）

pgAdmin Password: ________
                （推奨: 強力なパスワード）
```

#### 2-5. ポート番号を決定

```
PostgreSQL Port: 5432
               （他のサービスと被っていないか確認）

pgAdmin Port: 5050
            （他のサービスと被っていないか確認）
```

**現在のシステムでポート確認**:

```bash
# macOS/Linux
lsof -i :5432
lsof -i :5050

# Windows
netstat -ano | findstr :5432
netstat -ano | findstr :5050
```

---

### Step 3: docker-compose.yml を作成

前のステップで決定したパラメータを使用して、以下を作成：

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine  # 選択したイメージ（A/B/C）
    container_name: training_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: <決定したパスワード>
      POSTGRES_DB: <決定したDB名>
    ports:
      - "<決定したport>:5432"  # 例: "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - training_network
    # リソース制限（選択肢Bの場合のみ）
    # deploy:
    #   resources:
    #     limits:
    #       memory: 512M
    #       cpus: '0.5'

  pgadmin:
    image: dpage/pgadmin4:8.0
    container_name: training_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: <決定したメール>
      PGADMIN_DEFAULT_PASSWORD: <決定したパスワード>
    ports:
      - "<決定したport>:80"  # 例: "5050:80"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - training_network

volumes:
  postgres_data:

networks:
  training_network:
    driver: bridge
```

**重要な項目の確認**:
- [ ] PostgreSQL イメージを選択した（A/B/C）
- [ ] パスワードを決定した（強力か？）
- [ ] DB 名を決定した
- [ ] ポート番号が利用可能か確認した
- [ ] リソース制限が必要な場合は選択した

### Step 3: 環境変数を設定

.env ファイルを作成（または .env.example から）：

```
# .env
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=training_db
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/training_db
```

### Step 4: SQLAlchemy AsyncSession を設定

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# AsyncEngine 作成
engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql://... を async_postgresql に変換
    echo=True,  # SQL ログ出力（開発時のみ）
    future=True,
)

# AsyncSessionLocal 作成
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """Database session の取得"""
    async with AsyncSessionLocal() as session:
        yield session
```

### Step 5: DB 依存を確認

以下が `pyproject.toml` に含まれていることを確認（無ければ `uv add`）：

- `sqlalchemy`（>=2.0）
- `psycopg[binary]`（>=3.1）
- `alembic`（>=1.13）

### Step 6: Docker コンテナを起動

```bash
# コンテナ起動
cd training-sprint2
docker-compose up -d

# ログ確認（起動確認）
docker-compose logs postgres
```

**確認項目**:
- [ ] postgres コンテナが起動している
- [ ] pgadmin コンテナが起動している
- [ ] ネットワーク接続が正常

### Step 7: pgAdmin でデータベース接続確認

ブラウザで http://localhost:5050 を開く：

**ログイン情報**:
- メール: admin@example.com
- パスワード: admin

**新しいサーバーを登録**:
1. "Servers" → "Register" → "Server"
2. General タブ:
   - Name: training_db
3. Connection タブ:
   - Hostname: postgres（docker-compose 内部ホスト）
   - Port: 5432
   - Username: postgres
   - Password: postgres
   - Database: training_db
4. Save

**確認項目**:
- [ ] pgAdmin で training_db が表示される
- [ ] テーブル一覧が表示される（現在は空）

### Step 8: FastAPI から Database 接続テスト

`app/main.py` に テストエンドポイントを追加：

```python
# app/main.py に追加
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

@app.get("/api/v1/db-test", tags=["Health"])
async def db_test():
    """Database 接続テスト"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            return {"status": "Database connected", "result": result.scalar()}
    except Exception as e:
        return {"status": "Database connection failed", "error": str(e)}
```

開発サーバー起動・テスト：

```bash
cd backend
uvicorn app.main:app --reload

# 別ウィンドウで curl でテスト
curl http://localhost:8000/api/v1/db-test
```

**確認項目**:
- [ ] `curl http://localhost:8000/api/v1/db-test` で成功レスポンス
- [ ] `{"status": "Database connected", ...}` が返ってくる

### Step 9: backend/Dockerfile を作成（オプション）

後で本番ビルド時に使用：

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# uv で依存解決（pyproject.toml / uv.lock を使用）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 10: docker-compose.yml に FastAPI サービスを追加（オプション）

後で両方を統合したいときに使用：

```yaml
# docker-compose.yml に追加
  backend:
    build: ./backend
    container_name: training_backend
    environment:
      DATABASE_URL: postgresql://postgres:postgres@postgres:5432/training_db
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./backend:/app
    networks:
      - training_network
```

## チェックリスト

### Slice 0-2 完了時

- [ ] docker-compose.yml を作成した
- [ ] PostgreSQL コンテナが起動している
- [ ] pgAdmin でデータベースに接続できている
- [ ] app/core/database.py で AsyncSession を設定した
- [ ] pyproject.toml に sqlalchemy, psycopg が含まれることを確認した
- [ ] FastAPI から Database 接続テスト成功
- [ ] http://localhost:8000/api/v1/db-test でレスポンス確認
- [ ] backend/Dockerfile を作成した（オプション）

### 次のステップ

Slice 0-2 完了後は、**Slice 0-3: Database Design & Implementation を実行**

```
Slice 0-1: FastAPI セットアップ
  ↓
Slice 0-2（ここ）
  ↓
Slice 0-3: Database Design & Implementation
  ↓
Slice 0-4: Authentication Middleware (JWT/Cookie)
```

## トラブルシューティング

### postgres コンテナが起動しない場合

```bash
# ログ確認
docker-compose logs postgres

# コンテナを停止・削除
docker-compose down
docker volume rm training_postgres_data  # データ削除

# 再度起動
docker-compose up -d
```

### pgAdmin で接続できない場合

- Hostname は `postgres`（localhost ではなく、docker-compose 内部ホスト）
- Port は `5432`（デフォルト）
- パスワードは docker-compose.yml の `POSTGRES_PASSWORD` と同じ

### FastAPI から接続できない場合

- DATABASE_URL が `postgresql://...` ではじまっていることを確認
- 非同期接続の場合は `postgresql+asyncpg://...` に変更

## 参考資料

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)
