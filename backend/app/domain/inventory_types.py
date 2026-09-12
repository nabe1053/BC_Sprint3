"""Read-only inventory reconciliation contracts, independent of ORM and HTTP."""
from dataclasses import dataclass
from typing import Literal
from app.domain.record_types import RowMatch

InventoryStatus = Literal["mapped", "split", "excluded", "unmapped"]
Judgement = Literal["mapped", "split", "excluded", "missing", "inconsistent"]


@dataclass(frozen=True)
class LinkedItem:
    item_id: int
    row_code: str


@dataclass(frozen=True)
class SourceEntry:
    entry_id: int
    document_id: int
    position: str | None
    source_no: str | None


@dataclass(frozen=True)
class EntryView:
    entry_id: int
    document_id: int
    document_file_name: str | None
    position: str | None
    source_no: str | None
    seq: int
    excerpt: str | None
    status: InventoryStatus
    status_detail: str | None
    basis: str | None
    linked_items: tuple[LinkedItem, ...]
    link_count: int
    judgement: Judgement


@dataclass(frozen=True)
class ItemView:
    item_id: int
    row_code: str
    source_no: str
    seq: int
    group_code: str | None
    candidate_label: str | None
    source_entries: tuple[SourceEntry, ...]
    has_source: bool


@dataclass(frozen=True)
class InventorySummary:
    source_entry_count: int
    source_item_count: int
    output_row_count: int
    split_entry_ids: frozenset[int]
    excluded_entry_ids: frozenset[int]
    unmapped_entry_ids: frozenset[int]
    orphan_item_ids: frozenset[int]
    multi_mapped_item_ids: frozenset[int]
    inconsistent_entry_ids: frozenset[int]
    coverage: RowMatch | None = None


@dataclass(frozen=True)
class Reconciliation:
    summary: InventorySummary
    entries: tuple[EntryView, ...]
    items: tuple[ItemView, ...]
