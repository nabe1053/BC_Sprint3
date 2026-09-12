"""Strict tool arguments and local decision protocol, independent of SDK/DB."""
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.draft_types import (
    HeaderInput,
    ItemInput,
    EvidenceInput,
    QuestionInput,
    InventoryInput,
)


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CaseArguments(Arguments):
    case_id: int | None = Field(default=None, gt=0)


class DocumentArguments(Arguments):
    document_id: int = Field(gt=0)


class ContentArguments(DocumentArguments):
    from_seq: int | None = Field(default=None, ge=1)
    to_seq: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if (
            self.from_seq is not None
            and self.to_seq is not None
            and self.from_seq > self.to_seq
        ):
            raise ValueError("Invalid sequence range")
        return self


class SearchArguments(CaseArguments):
    query: str = Field(min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class RuleArguments(Arguments):
    rule_set_id: int | None = Field(default=None, gt=0)


class VersionArguments(Arguments):
    version_id: int | None = Field(default=None, gt=0)


class HeaderArguments(VersionArguments):
    header: HeaderInput


class ItemArguments(VersionArguments):
    rows: list[ItemInput] = Field(min_length=1)


class EvidenceArguments(VersionArguments):
    evidence: EvidenceInput


class QuestionArguments(VersionArguments):
    question: QuestionInput


class InventoryArguments(VersionArguments):
    entries: list[InventoryInput] = Field(min_length=1)


class IssueArguments(DocumentArguments):
    locator: str | None = None
    issue_type: Literal[
        "unreadable_page",
        "encrypted",
        "unsupported",
        "reference_missing",
        "not_scanned",
    ]
    detail: str = Field(min_length=1)


TOOL_ARGUMENTS = {
    "list_case_documents": CaseArguments,
    "read_document": ContentArguments,
    "read_email": DocumentArguments,
    "search_documents": SearchArguments,
    "get_rules": RuleArguments,
    "record_case_header": HeaderArguments,
    "propose_items": ItemArguments,
    "record_evidence": EvidenceArguments,
    "record_question": QuestionArguments,
    "record_source_inventory": InventoryArguments,
    "report_unreadable": IssueArguments,
    "validate_draft": VersionArguments,
    "finalize_draft": VersionArguments,
}


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolReply:
    data: dict
    is_error: bool = False


class LocalPolicyStop(Exception):
    """A local policy cannot proceed; only fixed reason codes cross this boundary."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)
