from datetime import datetime
from typing import Literal
from pydantic import Field, StrictBool
from app.api.schemas_base import CamelModel
from app.api.schemas_drafts import StrictRequest
from app.domain.run_types import StopReason


class AgentRunRequest(StrictRequest):
    rule_version: str | None = Field(default=None, min_length=1)
    acknowledged_carry_over: StrictBool = False


class AgentRunAccepted(CamelModel):
    run_id: int
    version_id: int
    started_at: datetime


class RunLimitsResponse(CamelModel):
    # NULL means legacy runs did not record this threshold; never invent a value.
    max_turns: int | None = None
    inner_timeout_s: int | None = None
    inactivity_timeout_s: int | None = None
    outer_timeout_s: int | None = None


class AgentRunResponse(CamelModel):
    run_id: int
    outcome: Literal["running", "success", "failed", "stopped"]
    stage: Literal["reading", "extracting", "self_checking", "done"] | None
    stage_detail: str | None
    turns: int
    elapsed_sec: float
    stop_reason: StopReason | None
    limits: RunLimitsResponse
    version_id: int | None
    is_complete: bool


class RunStepResponse(CamelModel):
    step_id: int
    seq: int
    tool_name: str
    args_digest: str
    args_summary: str | None
    locator: str | None
    document_id: int | None
    result_status: Literal["ok", "error", "unreadable"]
    duration_ms: int | None
    parent_step_id: int | None


class RunStepsResponse(CamelModel):
    steps: list[RunStepResponse]
