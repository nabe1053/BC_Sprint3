"""Inventory read orchestration; no ORM or HTTP dependencies."""
from dataclasses import replace
from app.domain.record_types import RowMatch
from app.services.inventory_reconciliation import reconcile


class InventoryService:
    def __init__(self, repository):
        self.repository = repository

    async def reconcile(self, version_id):
        entries, links, items, documents, coverage = await self.repository.load(
            version_id
        )
        result = reconcile(entries, links, items, version_id=version_id)
        names = {document.id: document.file_name for document in documents}
        return replace(
            result,
            entries=tuple(
                replace(entry, document_file_name=names.get(entry.document_id))
                for entry in result.entries
            ),
            summary=replace(
                result.summary,
                coverage=RowMatch(
                    coverage.id, coverage.recorded_by, coverage.recorded_at
                )
                if coverage is not None
                else None,
            ),
        )
