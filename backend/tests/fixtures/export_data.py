"""Synthetic workbook snapshots and database seeds."""
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace as N
from app.domain.export_types import ExportSnapshot, ItemRow
from app.domain.record_types import RowMatch
from tests.fixtures.record_data import current_item
from tests.fixtures.approval_data import approval_material

AT = datetime(2026, 9, 13, 5, 3, 5, tzinfo=UTC)


def snapshot(**changes):
    material = approval_material()
    values = vars(
        current_item(
            id=9,
            seq=1,
            row_code="R1",
            grade="L80",
            grade_raw="API K55",
            od_value=Decimal("13.375"),
            od_unit="in",
            od_raw='13-3/8"',
        )
    )
    other = {
        **values,
        "id": 10,
        "seq": 2,
        "row_code": "R2",
        "grade": "J55",
        "grade_raw": "API J55",
        "note": None,
    }
    end = N(
        side="end_a",
        od_value=Decimal("13.375"),
        od_unit="in",
        od_raw='13-3/8"',
        connection="LTC",
        thread_end="BOX",
    )
    rows = [
        ItemRow(values, [end], RowMatch(3, "確認者", AT), 1),
        ItemRow(other, [], None, 0),
    ]
    doc1 = N(
        id=1,
        file_name="synthetic.pdf",
        kind="pdf",
        read_status="success",
        received_at=AT,
        page_count=1,
    )
    doc2 = N(
        id=2,
        file_name="later.xlsx",
        kind="xlsx",
        read_status="success",
        received_at=AT + timedelta(seconds=1),
        page_count=None,
    )
    evidence = N(
        id=1,
        item_id=None,
        field="customer_name",
        raw_value="客先A",
        adopted_value="客先A",
        file_name=doc1.file_name,
        locator="p.1",
        quote="原文",
        applied_condition=None,
        conversion_note="換算：未実施（不足条件）",
        change_reason=None,
        prior_value=None,
    )
    question = N(
        id=71,
        item_id=9,
        question_code="Q1",
        target_field="grade",
        category="unknown",
        reason="要確認",
        candidates=None,
    )
    header = N(
        inquiry_no="INQ",
        inquiry_no_state="stated",
        customer_name="客先A",
        customer_name_state="stated",
        due_raw=None,
        due_state="not_stated",
        due_granularity=None,
        due_basis=None,
        place_raw=None,
        place_state="not_stated",
        incoterms=None,
        incoterms_state="not_stated",
        quote_deadline_raw=None,
        quote_deadline_at=None,
        quote_deadline_tz_state="missing",
    )
    return replace(
        ExportSnapshot(
            case=N(id=3, case_code="S-01"),
            version=N(
                id=7,
                version_no=2,
                current_state="draft",
                finalized_at=AT,
                is_complete=True,
            ),
            header=header,
            documents=[doc2, doc1],
            items=rows,
            evidences=[evidence],
            questions=[{"question": question, "latest": None}],
            records=material.records,
            elapsed_sec=None,
            rule_version="R-01",
            conversion_enabled=False,
            unresolved_count=1,
            matched_count=1,
            coverage_confirmed=True,
        ),
        **changes,
    )


async def seed_export_version(session, *, finalized=True, count=2):
    from app.models import (
        CaseHeader,
        Document,
        Item,
        ItemEnd,
        Evidence,
        Question,
        ItemEdit,
        Confirmation,
    )
    from app.domain.draft_types import ItemInput
    from tests.fixtures.record_data import seed_record_version, record_actor
    from tests.fixtures.draft_data import item_data, header_data

    seed = await seed_record_version(session, finalized=finalized)
    vid = seed.version.id
    header = CaseHeader(version_id=vid, **header_data())
    document = Document(
        case_id=seed.case.id,
        file_name="synthetic.pdf",
        storage_path="synthetic.pdf",
        kind="pdf",
        read_status="success",
        received_at=AT,
        page_count=1,
    )
    items = [seed.item]
    for seq in range(2, count + 1):
        items.append(
            Item(
                version_id=vid,
                **ItemInput.model_validate(
                    {**item_data(), "seq": seq, "row_code": str(seq)}
                ).model_dump(exclude={"ends"}),
            )
        )
    session.add_all([header, document, *items[1:]])
    await session.flush()
    end = ItemEnd(
        item_id=seed.item.id,
        side="end_a",
        od_value=Decimal("13.375"),
        od_unit="in",
        od_raw='13-3/8"',
        connection="LTC",
        thread_end="BOX",
    )
    evidence = Evidence(
        version_id=vid,
        item_id=None,
        field="customer_name",
        raw_value="客先",
        adopted_value="客先",
        document_id=document.id,
        locator="p.1",
        quote="原文",
    )
    question = Question(
        version_id=vid,
        item_id=seed.item.id,
        question_code="Q1",
        target_field="grade",
        reason="確認",
        category="unknown",
    )
    edit = ItemEdit(
        version_id=vid,
        item_id=seed.item.id,
        field="grade",
        old_value="K55",
        old_state="stated",
        new_value="L80",
        new_state="stated",
        reason="照合",
        **record_actor(at=AT),
    )
    confirmation = Confirmation(
        version_id=vid, item_id=seed.item.id, kind="row_match", **record_actor(at=AT)
    )
    session.add_all([end, evidence, question, edit, confirmation])
    await session.commit()
    return N(
        **vars(seed),
        header=header,
        document=document,
        items=items,
        end=end,
        evidence=evidence,
        question=question,
        edit=edit,
        confirmation=confirmation,
    )


def export_values(version_id, **changes):
    return dict(
        version_id=version_id,
        file_name="synthetic.xlsx",
        storage_path="synthetic.xlsx",
        content_hash="abc",
        exported_at=AT,
        state_at_export="draft",
        sendoff_at_export="undecided",
        unresolved_at_export=0,
        is_initial=False,
        **changes,
    )
