"""The same readonly validation contract is mounted under UI and AGENT (#20)."""
from dataclasses import asdict
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.api.dependencies_t202 import get_draft_service
from app.api.routes_t202 import DraftRoute, ERROR_RESPONSES
from app.api.schemas_drafts import ValidationResponse
from app.services.draft_service import DraftService

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)


@router.get("/versions/{versionId}/validation", response_model=ValidationResponse)
async def validate_draft(
    versionId: Annotated[int, Path(gt=0)],
    service: Annotated[DraftService, Depends(get_draft_service)],
):
    result = await service.validate(versionId)
    return ValidationResponse(
        violations=[asdict(v) for v in result.violations], counts=result.counts
    )
