"""UI-only run start/polling (#12–14)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.dependencies import get_run_service
from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.ui.schemas.agent_runs import (
    AgentRunRequest,
    AgentRunAccepted,
    AgentRunResponse,
    RunStepsResponse,
    RunStepResponse,
)
from app.services.run_service import RunService

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[RunService, Depends(get_run_service)]


@router.post(
    "/cases/{caseId}/agent-runs", status_code=202, response_model=AgentRunAccepted
)
async def start_run(caseId: Id, body: AgentRunRequest, service: Service):
    run = await service.start(
        caseId,
        rule_version=body.rule_version,
        acknowledged_carry_over=body.acknowledged_carry_over,
    )
    return AgentRunAccepted(
        run_id=run.id, version_id=run.version_id, started_at=run.started_at
    )


@router.get("/agent-runs/{runId}", response_model=AgentRunResponse)
async def get_run(runId: Id, service: Service):
    return AgentRunResponse(**await service.progress(runId))


@router.get("/agent-runs/{runId}/steps", response_model=RunStepsResponse)
async def get_steps(runId: Id, service: Service):
    rows = await service.steps(runId)
    return RunStepsResponse(
        steps=[
            RunStepResponse(
                step_id=r.id,
                seq=r.seq,
                tool_name=r.tool_name,
                args_digest=r.args_digest,
                args_summary=r.args_summary,
                locator=r.locator,
                document_id=r.document_id,
                result_status=r.result_status,
                duration_ms=r.duration_ms,
                parent_step_id=r.parent_step_id,
            )
            for r in rows
        ]
    )
