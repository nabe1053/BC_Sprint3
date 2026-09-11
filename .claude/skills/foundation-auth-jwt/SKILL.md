---
name: foundation-auth-jwt
description: 認証基盤構築（httpOnly Cookie ベース JWT・トークン自動更新・ユーザー設定決定）
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Slice 0-4: Authentication Middleware (httpOnly Cookie JWT)

httpOnly Cookie ベースの JWT 認証を実装するスキル。
重要なセキュリティパラメータ（JWT 期限、シークレットキー等）をユーザーと一緒に決定します。

## Purpose

認証基盤を構築する（ユーザー主導決定）：

1. **JWT 設定をユーザーと決定**：期限、シークレットキー、リフレッシュ戦略
2. **httpOnly Cookie ベース認証を実装**（XSS 対策）
3. **トークン自動更新機能を実装**（401 Unauthorized 処理）
4. **パスワード管理**（bcrypt）
5. **orval custom mutator 対応**（credentials: include）
6. **認証保護されたエンドポイント**の実装例

## When to use

- Slice 0-3（Database Design）完了後に実行
- 認証機能を実装したい
- JWT / Cookie 戦略を決定したい

## Prerequisites

- Slice 0-3（Database & ORM）が完了していること
- User モデルが実装されていること

## Important: httpOnly Cookie ベース（固定）

このスキルでは **httpOnly Cookie ベースの JWT 認証** を実装します。

```
構成図：
Client → POST /api/v1/auth/login
         ↓ (email, password)
       Server
         ↓ (パスワード検証)
       JWT トークン生成
         ↓ (Set-Cookie: HttpOnly, SameSite)
Client ← Cookie 自動設定
         ↓
Client → GET /api/v1/users/me
         Cookie (自動付与, credentials: include)
         ↓
       Server (JWT 検証)
         ↓
       401 時: トークン自動更新
         ↓
       Response
```

**特徴**:
- ✅ XSS 対策（HttpOnly フラグ）
- ✅ CSRF 対策（SameSite フラグ）
- ✅ トークン自動送信（クライアント実装簡潔）
- ✅ orval custom mutator 対応（credentials: include）
- ✅ トークン自動更新機能

---

## Procedure

### Step 1: JWT セキュリティパラメータを決定（ユーザー主導）

以下の項目をご決定ください：

#### 1-1. JWT アクセストークンの有効期限

```
A. 15 分（推奨・セキュリティ重視）
   - リフレッシュ頻度が高い
   - セッションハイジャック時の影響最小

B. 30 分（標準）
   - バランス型
   - UX と セキュリティ両立

C. 1 時間（UX 重視）
   - リフレッシュ頻度が低い
   - ユーザー体験向上

D. カスタム: ___ 分
```

**推奨**: A（15 分）

#### 1-2. JWT リフレッシュトークンの有効期限

```
A. 7 日（推奨）
   - クライアント側で自動更新
   - セキュリティと UX バランス

B. 30 日（長期）
   - リフレッシュが少ない
   - セキュリティリスク増

C. 1 日（短期・セキュリティ重視）
   - 毎日のリログインが必要
   - セキュリティ最高

D. カスタム: ___ 日
```

**推奨**: A（7 日）

#### 1-3. JWT シークレットキー

```
自動生成（推奨）：
python -c "import secrets; print(secrets.token_urlsafe(32))"

または、カスタム値を指定：
_________________________________
（最小 32 文字推奨）

注意: 本番環境では環境変数で管理し、Git には commit しない
```

**推奨**: 自動生成（ランダムで強力）

#### 1-4. Cookie 設定を確認

```
Cookie Name: access_token
           （デフォルト、変更不推奨）

HttpOnly: True
        （XSS 対策・固定）

Secure: False（開発環境）/ True（本番環境）
       （HTTPS 環境のみ True）

SameSite: lax
        （CSRF 対策・推奨）
        （オプション: lax / strict / none）
```

**推奨設定**:
- 開発環境: Secure=False, SameSite=lax
- 本番環境: Secure=True, SameSite=strict

#### 1-5. パスワードハッシュアルゴリズム

```
A. bcrypt（推奨）
   - 計算コスト高
   - セキュリティ最高

B. argon2（超セキュア・遅い）
   - パスワードハッシュの最新
   - bcrypt より安全

C. scrypt（セキュア）
   - bcrypt より新しい
```

**推奨**: A（bcrypt）

---

### Step 2: パスワード管理を実装

```bash
# passlib / python-jose は pyproject に含まれる（未追加なら uv で追加）
uv add "passlib[bcrypt]" "python-jose[cryptography]"
```

```python
# app/core/security.py
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# パスワード・ハッシュ化設定（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """パスワードをハッシュ化"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワード検証"""
    return pwd_context.verify(plain_password, hashed_password)
```

---

### Step 3: JWT トークン生成・検証を実装（httpOnly Cookie 用）

```python
# app/core/security.py に追加
from jose import JWTError, jwt
from app.core.config import settings
import os

# JWT 設定（環境変数で指定）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"

# Step 1で決定した値
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # デフォルト（ユーザー決定値に変更）
REFRESH_TOKEN_EXPIRE_DAYS = 7     # デフォルト（ユーザー決定値に変更）

def create_access_token(data: dict) -> str:
    """アクセストークン生成（有効期限短い）"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """リフレッシュトークン生成（有効期限長い）"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """JWT トークン検証"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None
```

### Step 4: Cookie 設定を実装

```python
# app/core/security.py に追加
from fastapi.responses import JSONResponse

def set_auth_cookies(response: JSONResponse, user_id: int, is_secure: bool = False) -> JSONResponse:
    """認証 Cookie を設定（アクセス + リフレッシュ）"""

    access_token = create_access_token({"sub": str(user_id)})
    refresh_token = create_refresh_token({"sub": str(user_id)})

    # アクセストークン（短期）
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,      # JavaScript からアクセス不可
        secure=is_secure,   # HTTPS 環境のみ True
        samesite="lax",     # CSRF 対策
        path="/",
    )

    # リフレッシュトークン（長期）
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/api/v1/auth",  # リフレッシュエンドポイントのみ
    )

    return response

def clear_auth_cookies(response: JSONResponse) -> JSONResponse:
    """認証 Cookie をクリア（ログアウト）"""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1/auth")
    return response
```

### Step 5: 認証ミドルウェアを実装（Cookie 検証）

```python
# app/api/v1/dependencies/auth.py
from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_token
from app.repositories.user_repository import UserRepository
from app.core.dependencies import get_db
from typing import Optional

async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    session: AsyncSession = Depends(get_db)
):
    """現在のユーザー取得（Cookie JWT 検証）"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    payload = verify_token(access_token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_repo = UserRepository(session)
    user = await user_repo.get(int(user_id))

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user
```

### Step 6: ログインエンドポイントを実装

```python
# app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.schemas.user import UserCreate, UserResponse
from app.core.dependencies import get_db
from app.core.security import (
    hash_password, verify_password,
    set_auth_cookies, clear_auth_cookies
)
from app.models import User
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_db)):
    """ユーザー登録"""
    user_repo = UserRepository(session)

    # 既存ユーザー確認
    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ユーザー作成
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
    )
    created = await user_repo.create(new_user)
    return created

@router.post("/login")
async def login(email: str, password: str, session: AsyncSession = Depends(get_db)):
    """ログイン（httpOnly Cookie に JWT 設定）"""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_email(email)

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    response = JSONResponse({"message": "Login successful", "user": {"id": user.id, "email": user.email}})
    response = set_auth_cookies(response, user.id, is_secure=False)  # 本番環境では True
    return response

@router.post("/logout")
async def logout():
    """ログアウト（Cookie クリア）"""
    response = JSONResponse({"message": "Logout successful"})
    response = clear_auth_cookies(response)
    return response

@router.post("/refresh")
async def refresh(refresh_token: Optional[str] = Cookie(None), session: AsyncSession = Depends(get_db)):
    """トークンリフレッシュ（自動更新）"""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    payload = verify_token(refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = payload.get("sub")
    user_repo = UserRepository(session)
    user = await user_repo.get(int(user_id))

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    response = JSONResponse({"message": "Token refreshed"})
    response = set_auth_cookies(response, user.id, is_secure=False)
    return response
```

### Step 7: 保護されたエンドポイントの実装例

```python
# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Depends
from app.api.v1.dependencies.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報取得（認証保護）"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
    }
```

---

### Step 8: main.py にエンドポイントを登録

```python
# app/main.py に追加
from app.api.v1.endpoints import auth, users

app.include_router(auth.router)
app.include_router(users.router)
```

### Step 9: 環境変数を設定

Step 1 で決定したシークレットキーと期限を設定：

```bash
# .env に追加
JWT_SECRET_KEY=<Step 1-3 で決定したシークレットキー>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=<Step 1-1 で決定した期限（推奨: 15）>
JWT_REFRESH_TOKEN_EXPIRE_DAYS=<Step 1-2 で決定した期限（推奨: 7）>

# CORS 設定（フロント接続用）
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

**重要**:
- .env は git に commit しない
- 本番環境では環境変数で注入（CI/CD で設定）
- SECRET_KEY は十分にランダム（最小 32 文字）
- 本番環境では Secure=True, SameSite=strict に変更

### Step 10: Cookie & CORS 設定を確認

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,  # Cookie 送信許可（重要！）
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 11: OpenAPI スキーマの自動生成を確認

FastAPI は自動的に OpenAPI スキーマを生成します。
フロント側の orval で使用：

```bash
# OpenAPI スキーマ確認
curl http://localhost:8000/openapi.json

# Swagger UI（開発時）
# http://localhost:8000/docs
```

このスキーマを `orval.config.ts` で参照して、フロント API client を自動生成します。

### Step 12: テストエンドポイントで確認

```bash
# ユーザー登録
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"password123"}'

# ログイン（httpOnly Cookie に JWT 設定）
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt

# 現在ユーザー取得（Cookie は自動付与）
curl http://localhost:8000/api/v1/users/me \
  -b cookies.txt

# トークンリフレッシュ（401 時の自動更新をシミュレート）
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -b cookies.txt

# ログアウト（Cookie クリア）
curl -X POST http://localhost:8000/api/v1/auth/logout
```

**確認項目**:
- [ ] ユーザー登録成功
- [ ] ログイン時に Set-Cookie ヘッダーが返ってくる（access_token + refresh_token）
- [ ] Cookie を使用して /me エンドポイント呼び出し成功
- [ ] リフレッシュトークンで自動更新成功
- [ ] ログアウト後、Cookie が削除される

## チェックリスト

### Slice 0-4 完了時

- [ ] **JWT パラメータを決定した**（ユーザー主導）
  - [ ] アクセストークン有効期限（推奨: 15 分）
  - [ ] リフレッシュトークン有効期限（推奨: 7 日）
  - [ ] JWT シークレットキー
  - [ ] Cookie 設定（Secure、SameSite）
  - [ ] パスワードハッシュアルゴリズム
- [ ] 依存パッケージインストール完了（passlib, python-jose）
- [ ] app/core/security.py 実装完了
  - [ ] パスワードハッシュ化
  - [ ] アクセストークン生成
  - [ ] リフレッシュトークン生成
  - [ ] トークン検証
  - [ ] Cookie 設定・クリア
- [ ] 認証ミドルウェア実装完了（Cookie ベース）
- [ ] ログインエンドポイント実装完了（/api/v1/auth/login）
- [ ] ログアウトエンドポイント実装完了
- [ ] トークンリフレッシュエンドポイント実装完了（自動更新対応）
- [ ] 保護されたエンドポイント実装完了（/api/v1/users/me）
- [ ] main.py に CORS 設定追加（allow_credentials=True）
- [ ] 環境変数を設定した（.env に JWT_SECRET_KEY 等）
- [ ] OpenAPI スキーマ確認完了（http://localhost:8000/openapi.json）
- [ ] テストで疎通確認完了
  - [ ] ユーザー登録
  - [ ] ログイン（Cookie 設定）
  - [ ] 保護エンドポイント呼び出し
  - [ ] トークンリフレッシュ
  - [ ] ログアウト（Cookie クリア）

### 次のステップ

Slice 0-4 完了後は、**Slice 0-5: Frontend Setup (Next.js) を実行**

```
Slice 0-1: FastAPI セットアップ
  ↓
Slice 0-2: PostgreSQL Docker
  ↓
Slice 0-3: Database Design & Implementation
  ↓
Slice 0-4（ここ）
  ↓
Slice 0-5: Frontend Setup (Next.js)
  ↓
Slice 0-6: API Integration Test
```

## 参考資料

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Passlib Documentation](https://passlib.readthedocs.io/)
- [Cookie Security Best Practices](https://owasp.org/www-community/attacks/csrf)
