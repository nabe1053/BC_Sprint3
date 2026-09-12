"""FastAPI アプリケーション入点。

Sprint 3 は認証を実装しない（CLAUDE.md 決定事項1）。代わりに、AGENT-01 が人の記録 API
（05-api-ipo.md F群）を呼べない境界を **`/agent/*` と `/ui/*` のパス分離** で守る
（05-api-ipo.md 7.1 推奨案）。エージェント実行時の HTTP クライアントは `/agent/*` 配下
にしか到達させない。

パスは `/api/v1/agent/*` と `/api/v1/ui/*`（版プレフィックスは `API_V1` の1箇所で管理する）。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent.router import router as agent_router
from app.api.dependencies import run_lifespan
from app.api.errors import ApiError, api_error_handler, domain_error_handler
from app.api.ui.router import router as ui_router
from app.core.config import settings
from app.services.exceptions import DomainError

app = FastAPI(
    lifespan=run_lifespan,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(DomainError, domain_error_handler)

# 版プレフィックスは1箇所に集約する（health も /api/v1 配下）。
API_V1 = "/api/v1"
app.include_router(agent_router, prefix=API_V1)
app.include_router(ui_router, prefix=API_V1)


@app.get(f"{API_V1}/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """ヘルスチェック。"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/", tags=["Health"])
async def root() -> dict[str, str]:
    return {"message": "OCTG Item List Agent API"}
