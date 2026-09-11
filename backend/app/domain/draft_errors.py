"""Errors shared by the draft repository and business service."""


class DraftError(Exception):
    def __init__(self, code, message, details=None):
        self.code = code
        self.details = details or {}
        super().__init__(message)
