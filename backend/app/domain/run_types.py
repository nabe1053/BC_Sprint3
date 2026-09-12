"""Run contracts shared by services and local workers; no SDK or settings imports."""
from dataclasses import dataclass
from typing import Literal

StopReason = Literal[
    "completed",
    "failed",
    "max_turns",
    "inner_timeout",
    "inactivity_timeout",
    "outer_timeout",
    "repeated_call",
    "no_readable_document",
    "validation_loop",
]


@dataclass(frozen=True)
class RunLimits:
    max_turns: int
    inner_timeout_s: int
    inactivity_timeout_s: int
    outer_timeout_s: int

    def __post_init__(self):
        if (
            self.max_turns < 1
            or not 0
            < self.inactivity_timeout_s
            < self.inner_timeout_s
            < self.outer_timeout_s
        ):
            raise ValueError("Invalid run limits")

    def snapshot(self):
        return {
            "maxTurns": self.max_turns,
            "innerTimeoutS": self.inner_timeout_s,
            "inactivityTimeoutS": self.inactivity_timeout_s,
            "outerTimeoutS": self.outer_timeout_s,
        }


@dataclass(frozen=True)
class InputLimits:
    max_documents: int = 50
    max_file_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 200
    max_xlsx_sheets: int = 50


@dataclass(frozen=True)
class HeartbeatDiagnostics:
    since_last_heartbeat_s: float
    heartbeats: int


@dataclass(frozen=True)
class RunResult:
    stop_reason: StopReason
    turns: int | None = None
    detail: str | None = None
    heartbeat_diagnostics: HeartbeatDiagnostics | None = None

    def __post_init__(self):
        if self.stop_reason not in (
            "completed",
            "failed",
            "max_turns",
            "inner_timeout",
            "inactivity_timeout",
            "outer_timeout",
            "repeated_call",
            "no_readable_document",
            "validation_loop",
        ):
            raise ValueError("Invalid stop reason")
        if self.turns is not None and self.turns < 0:
            raise ValueError("Invalid turns")


@dataclass(frozen=True)
class RunContext:
    run_id: int
    case_id: int
    version_id: int
    rule_set_id: int
    limits: RunLimits
