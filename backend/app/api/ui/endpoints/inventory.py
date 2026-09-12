"""UI-only inventory reconciliation read (#27)."""
from typing import Annotated
from fastapi import APIRouter, Depends, Path

from app.api.common.route_errors import DraftRoute, ERROR_RESPONSES
from app.api.dependencies import get_inventory_service
from app.api.ui.schemas.inventory import InventoryResponse
from app.services.inventory_service import InventoryService

router = APIRouter(route_class=DraftRoute, responses=ERROR_RESPONSES)
Id = Annotated[int, Path(gt=0)]
Service = Annotated[InventoryService, Depends(get_inventory_service)]


@router.get("/versions/{versionId}/inventory", response_model=InventoryResponse)
async def get_inventory(versionId: Id, service: Service):
    result = await service.reconcile(versionId)
    return InventoryResponse.model_validate(result, from_attributes=True)
