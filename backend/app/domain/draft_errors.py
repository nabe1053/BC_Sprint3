"""Errors shared by the draft repository and business service."""
from app.domain.errors import DomainError


class DraftError(DomainError):
    def __init__(self, code, message, details=None):
        self.code = code
        super().__init__(message, details)
