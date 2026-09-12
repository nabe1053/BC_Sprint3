"""Read model for deterministic validation; independent of SQLAlchemy and HTTP."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DraftSnapshot:
    items: list[Any] = field(default_factory=list)
    ends: list[Any] = field(default_factory=list)
    header: Any = None
    evidences: list[Any] = field(default_factory=list)
    questions: list[Any] = field(default_factory=list)
    inventory: list[Any] = field(default_factory=list)
    readable_ranges: set[tuple[int, str]] = field(default_factory=set)
    scanned_ranges: set[tuple[int, str]] = field(default_factory=set)
    excused_ranges: set[tuple[int, str]] = field(default_factory=set)
    has_issues: bool = False
    run_id: int | None = None
