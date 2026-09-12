"""Deterministic reconciliation from saved status and structural links."""
from app.domain.inventory_types import (
    EntryView,
    InventorySummary,
    ItemView,
    LinkedItem,
    Reconciliation,
    SourceEntry,
)


def reconcile(entries, links, items, *, version_id):
    entries = sorted(
        (row for row in entries if row.version_id == version_id),
        key=lambda row: (row.seq, row.id),
    )
    items = sorted(
        (row for row in items if row.version_id == version_id),
        key=lambda row: (row.seq, row.id),
    )
    entry_by_id = {row.id: row for row in entries}
    item_by_id = {row.id: row for row in items}
    by_entry = {}
    by_item = {}
    inconsistent = set()
    for link in links:
        by_entry.setdefault(link.entry_id, set()).add(link.item_id)
        if link.entry_id not in entry_by_id:
            inconsistent.add(link.entry_id)
        target = item_by_id.get(link.item_id)
        if target is None or getattr(link, "item_version_id", version_id) != version_id:
            inconsistent.add(link.entry_id)
            continue
        by_item.setdefault(link.item_id, set()).add(link.entry_id)

    entry_views = []
    for entry in entries:
        linked = by_entry.get(entry.id, set())
        count = len(linked)
        if (
            (entry.status == "mapped" and count != 1)
            or (entry.status == "split" and count < 2)
            or (entry.status in ("excluded", "unmapped") and count > 0)
        ):
            inconsistent.add(entry.id)
        if entry.id in inconsistent:
            judgement = "inconsistent"
        elif count >= 2:
            judgement = "split"
        elif entry.status == "excluded":
            judgement = "excluded"
        elif entry.status == "unmapped":
            judgement = "missing"
        else:
            judgement = "mapped"
        entry_views.append(
            EntryView(
                entry_id=entry.id,
                document_id=entry.document_id,
                document_file_name=None,
                position=entry.position,
                source_no=entry.source_no,
                seq=entry.seq,
                excerpt=entry.excerpt,
                status=entry.status,
                status_detail=entry.status_detail,
                basis=entry.basis,
                linked_items=tuple(
                    LinkedItem(item.id, item.row_code)
                    for item in items
                    if item.id in linked
                ),
                link_count=count,
                judgement=judgement,
            )
        )
    item_views = tuple(
        ItemView(
            item_id=item.id,
            row_code=item.row_code,
            source_no=item.source_no,
            seq=item.seq,
            group_code=item.group_code,
            candidate_label=item.candidate_label,
            source_entries=tuple(
                SourceEntry(
                    entry.id, entry.document_id, entry.position, entry.source_no
                )
                for entry in entries
                if entry.id in by_item.get(item.id, set())
            ),
            has_source=bool(by_item.get(item.id)),
        )
        for item in items
    )
    summary = InventorySummary(
        source_entry_count=len(entries),
        source_item_count=sum(entry.status != "excluded" for entry in entries),
        output_row_count=len(items),
        split_entry_ids=frozenset(
            entry.id for entry in entries if len(by_entry.get(entry.id, set())) >= 2
        ),
        excluded_entry_ids=frozenset(
            entry.id for entry in entries if entry.status == "excluded"
        ),
        unmapped_entry_ids=frozenset(
            entry.id
            for entry in entries
            if entry.status == "unmapped" and not by_entry.get(entry.id)
        ),
        orphan_item_ids=frozenset(
            item.id for item in items if not by_item.get(item.id)
        ),
        multi_mapped_item_ids=frozenset(
            item.id for item in items if len(by_item.get(item.id, set())) >= 2
        ),
        inconsistent_entry_ids=frozenset(inconsistent),
    )
    return Reconciliation(summary, tuple(entry_views), item_views)
