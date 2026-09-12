"""Translate T-202 domain/input failures without echoing request values."""
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from app.api.errors import ApiError, domain_error_handler
from app.api.schemas_error import ErrorResponse
from app.domain.errors import DomainError

ERROR_RESPONSES = {
    status: {"model": ErrorResponse} for status in (400, 404, 409, 413, 422, 503)
}


def invalid_request(exc, request):
    errors = exc.errors()
    structural = any(
        (e["loc"] and e["loc"][0] in ("path", "query"))
        or (e["type"] == "extra_forbidden" and e["loc"] and "_" in str(e["loc"][-1]))
        for e in errors
    )
    code = (
        "E_REQUEST_INVALID"
        if structural
        else next(
            (e["type"] for e in errors if e["type"].startswith("E_")),
            "E_REQUEST_INVALID",
        )
    )
    return ApiError(
        422 if structural else 400,
        code,
        "リクエストの形式または必須項目を確認してください",
        {
            "errors": [
                {"path": ".".join(str(p) for p in e["loc"]), "type": e["type"]}
                for e in errors
            ]
        },
    )


class DraftRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def wrapped(request):
            try:
                return await handler(request)
            except DomainError as exc:
                return await domain_error_handler(request, exc)
            except RequestValidationError as exc:
                raise invalid_request(exc, request) from exc

        return wrapped
