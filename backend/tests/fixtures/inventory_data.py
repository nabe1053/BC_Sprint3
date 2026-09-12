"""Synthetic S06/S02 inventory builders shared by reconciliation test layers."""
from types import SimpleNamespace as N


def entry(id=1, status="mapped", **changes):
    return N(
        **{
            **dict(
                id=id,
                version_id=1,
                document_id=1,
                position=f"p.{id}",
                source_no=str(id),
                seq=id,
                excerpt=f"synthetic {id}",
                status=status,
                status_detail=None,
                basis="synthetic exclusion" if status == "excluded" else None,
            ),
            **changes,
        }
    )


def output_item(id=101, **changes):
    return N(
        **{
            **dict(
                id=id,
                version_id=1,
                row_code=f"R{id}",
                source_no=str(id - 100),
                seq=id - 100,
                group_code=None,
                candidate_label=None,
            ),
            **changes,
        }
    )


def link(entry_id, item_id):
    return N(entry_id=entry_id, item_id=item_id)


def s06():
    entries = [
        entry(i, "mapped" if i <= 5 else "split" if i <= 8 else "excluded")
        for i in range(1, 13)
    ]
    items = [output_item(i) for i in range(101, 112)]
    links = [link(i, 100 + i) for i in range(1, 6)]
    for entry_id, first_item in [(6, 106), (7, 108), (8, 110)]:
        links.extend([link(entry_id, first_item), link(entry_id, first_item + 1)])
    return entries, links, items


async def seed_inventory(session, finalized=True):
    from datetime import UTC, datetime
    from app.models import Document, InventoryEntry, InventoryLink, Item
    from app.domain.draft_types import ItemInput
    from tests.fixtures.record_data import seed_record_version
    from tests.fixtures.draft_data import item_data

    seed = await seed_record_version(session, finalized=finalized)
    document = Document(
        case_id=seed.case.id,
        file_name="synthetic-s06.txt",
        storage_path="unused",
        kind="text",
        read_status="success",
        received_at=datetime.now(UTC),
    )
    session.add(document)
    await session.flush()
    source_entries, source_links, source_items = s06()
    items = {}
    for index, template in enumerate(source_items):
        data = ItemInput.model_validate(
            {
                **item_data(),
                "row_code": template.row_code,
                "source_no": template.source_no,
                "seq": template.seq,
            }
        ).model_dump(exclude={"ends"})
        if index == 0:
            row = seed.item
            for field, value in data.items():
                setattr(row, field, value)
        else:
            row = Item(version_id=seed.version.id, **data)
            session.add(row)
        items[template.id] = row
    entries = {}
    for template in source_entries:
        row = InventoryEntry(
            version_id=seed.version.id,
            document_id=document.id,
            **{
                key: value
                for key, value in vars(template).items()
                if key not in {"id", "version_id", "document_id"}
            },
        )
        session.add(row)
        entries[template.id] = row
    await session.flush()
    session.add_all(
        [
            InventoryLink(
                entry_id=entries[row.entry_id].id, item_id=items[row.item_id].id
            )
            for row in source_links
        ]
    )
    await session.commit()
    return N(seed=seed, document=document, entries=entries, items=items)
