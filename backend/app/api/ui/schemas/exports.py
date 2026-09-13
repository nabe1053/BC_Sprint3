"""Explicit export metadata and version-wide evidence response contracts."""
from datetime import datetime
from typing import Literal
from pydantic import Field
from app.api.schemas_base import CamelModel
from app.api.ui.schemas.versions import EvidenceResponse
from app.domain.record_types import VersionState, SendoffState


class ExportRecord(CamelModel):
    export_id: int
    file_name: str
    storage_path: str
    content_hash: str
    exported_at: datetime
    state_at_export: VersionState
    sendoff_at_export: SendoffState
    unresolved_at_export: int = Field(ge=0)
    is_initial: bool
    integrity: Literal["intact", "modified", "missing"]


class ExportsResponse(CamelModel):
    exports: list[ExportRecord]


class VersionEvidenceRecord(EvidenceResponse):
    item_id: int | None
    file_name: str


class VersionEvidenceResponse(CamelModel):
    evidences: list[VersionEvidenceRecord]
