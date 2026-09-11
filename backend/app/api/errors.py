"""共通エラー応答。

05-api-ipo.md 0.2「エラーは { code, message, details } の共通形」。
`code` は 05-api-ipo.md 6章のエラーコード一覧が SSOT。

`DomainError`（Business Logic 層・`app.services.exceptions`）→ HTTP ステータスの
変換は、この1箇所（`DOMAIN_ERROR_STATUS_BY_CODE` + `domain_error_handler`）に
集約する（endpoints で個別に status を組み立てない。T-102 orchestrator 決定8）。
"""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.services.exceptions import DomainError


class ApiError(Exception):
    """業務エラー。05-api-ipo.md 6章の code をそのまま渡す。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


# DomainError.code → HTTP status（05-api-ipo.md 6章）。
# ここに無い code は開発時の取りこぼしなので 400（Bad Request）に丸める。
DOMAIN_ERROR_STATUS_BY_CODE: dict[str, int] = {
    "E_DUPLICATE_CASE_CODE": 409,
    "E_LIMIT_EXCEEDED": 413,
    "E_UNSUPPORTED_FORMAT": 415,
    "E_UNREADABLE": 409,
    "E_NOT_EMAIL": 409,
    "E_QUERY_REQUIRED": 400,
    "E_DETAIL_REQUIRED": 400,
    "E_NOT_FOUND": 404,
}


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Business Logic 層の `DomainError` を共通形のエラー応答に変換する。"""
    status_code = DOMAIN_ERROR_STATUS_BY_CODE.get(exc.code, 400)
    return JSONResponse(
        status_code=status_code,
        content={"code": exc.code, "message": str(exc), "details": exc.details},
    )
