"""共通エラー応答 DTO（05-api-ipo.md 0.2「エラーは {code, message, details} の共通形」）。

reviewer 指摘 中-6: OpenAPI にエラー応答が出ていなかった（422 以外ゼロ）。
実際の変換は `app.api.errors`（`ApiError`/`DomainError` → JSONResponse）が担う。
このモデルは各エンドポイントの `responses` に宣言し、orval/OpenAPI ドキュメントに
反映するためだけに使う。
"""

from typing import Any

from app.api.schemas_base import CamelModel


class ErrorResponse(CamelModel):
    code: str
    message: str
    details: dict[str, Any] = {}
