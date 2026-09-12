"""Read-only inventory loading scoped to one finalized version."""
from sqlalchemy import select
from app.models import Document, InventoryEntry, InventoryLink, Item
from app.repositories.record_repository import RecordRepository


class InventoryRepository:
    def __init__(self, session):
        self.session = session

    version = RecordRepository.version

    async def load(self, version_id):
        await self.version(version_id)
        entries = list(
            (
                await self.session.execute(
                    select(InventoryEntry)
                    .where(InventoryEntry.version_id == version_id)
                    .order_by(InventoryEntry.seq, InventoryEntry.id)
                )
            ).scalars()
        )
        links = list(
            (
                await self.session.execute(
                    select(
                        InventoryLink.entry_id,
                        InventoryLink.item_id,
                        Item.version_id.label("item_version_id"),
                    )
                    .select_from(InventoryLink)
                    .join(InventoryEntry, InventoryEntry.id == InventoryLink.entry_id)
                    .outerjoin(Item, Item.id == InventoryLink.item_id)
                    .where(InventoryEntry.version_id == version_id)
                    .order_by(InventoryLink.id)
                )
            ).all()
        )
        items = list(
            (
                await self.session.execute(
                    select(Item)
                    .where(Item.version_id == version_id)
                    .order_by(Item.seq, Item.id)
                )
            ).scalars()
        )
        documents = list(
            (
                await self.session.execute(
                    select(Document).where(
                        Document.id.in_({entry.document_id for entry in entries})
                    )
                )
            ).scalars()
        )
        coverage = await RecordRepository(self.session).active_confirmation(
            version_id, "coverage", None
        )
        return entries, links, items, documents, coverage
