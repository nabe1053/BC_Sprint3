"""Shared domain error contract; independent of service and transport layers."""
from typing import Any


class DomainError(Exception):
    code: str = "E_DOMAIN_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.details = details or {}
        super().__init__(message)
