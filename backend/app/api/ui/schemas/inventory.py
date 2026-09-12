"""Read-only inventory response whitelists and deterministic ID arrays."""
from pydantic import Field, field_validator

from app.api.schemas_base import CamelModel
from app.api.ui.schemas.versions import RowMatchResponse
from app.domain.inventory_types import InventoryStatus, Judgement


class LinkedItemResponse(CamelModel):
    item_id: int
    row_code: str


class SourceEntryResponse(CamelModel):
    entry_id: int
    document_id: int
    position: str
    source_no: str | None


class InventoryEntryResponse(CamelModel):
    entry_id: int
    document_id: int
    document_file_name: str | None
    position: str
    source_no: str | None
    seq: int = Field(ge=1)
    excerpt: str
    status: InventoryStatus
    status_detail: str | None
    basis: str | None
    linked_items: list[LinkedItemResponse]
    link_count: int = Field(ge=0)
    judgement: Judgement


class InventoryItemResponse(CamelModel):
    item_id: int
    row_code: str
    source_no: str
    seq: int = Field(ge=1)
    group_code: str | None
    candidate_label: str | None
    source_entries: list[SourceEntryResponse]
    has_source: bool


class InventorySummaryResponse(CamelModel):
    source_entry_count: int = Field(ge=0)
    source_item_count: int = Field(ge=0)
    output_row_count: int = Field(ge=0)
    split_entry_ids: list[int]
    excluded_entry_ids: list[int]
    unmapped_entry_ids: list[int]
    orphan_item_ids: list[int]
    multi_mapped_item_ids: list[int]
    inconsistent_entry_ids: list[int]
    coverage: RowMatchResponse | None

    @field_validator(
        "split_entry_ids",
        "excluded_entry_ids",
        "unmapped_entry_ids",
        "orphan_item_ids",
        "multi_mapped_item_ids",
        "inconsistent_entry_ids",
        mode="before",
    )
    @classmethod
    def sorted_ids(cls, value):
        return sorted(set(value))


class InventoryResponse(CamelModel):
    summary: InventorySummaryResponse
    entries: list[InventoryEntryResponse]
    items: list[InventoryItemResponse]
