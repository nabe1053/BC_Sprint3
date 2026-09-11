"""共通エラー応答。

05-api-ipo.md 0.2「エラーは { code, message, details } の共通形」。
`code` は 05-api-ipo.md 6章のエラーコード一覧が SSOT。
"""

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


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
