from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.domain.draft_errors import DraftError
from app.domain.draft_types import (
    EvidenceInput,
    HeaderInput,
    InventoryInput,
    ItemInput,
    QuestionInput,
)
from app.models.cases import Case
from app.models.documents import Document, DocumentPage, DocumentIssue, EmailPart
from app.models.rule_sets import RuleSet
from app.models.agent_runs import AgentRun, AgentRunStep
from app.models.drafts import CaseHeader, Item, ItemEnd, Evidence, InventoryLink
from app.repositories.draft_repository import DraftRepository
from tests.unit.test_draft_inputs import item_data, header_data


async def setup_case(session, code="TEST-201"):
    case = Case(case_code=code)
    rules = RuleSet(rule_version=code, rules={}, conversion_enabled=False)
    session.add_all([case, rules])
    await session.commit()
    doc = Document(
        case_id=case.id,
        file_name="synthetic.txt",
        storage_path="synthetic.txt",
        kind="text",
        read_status="success",
        content_hash=code,
        received_at=datetime.now(UTC),
    )
    session.add(doc)
    await session.commit()
    return case, rules, doc


async def setup_version(session):
    case, rules, doc = await setup_case(session)
    repo = DraftRepository(session)
    version = await repo.create_version(case.id, rules.id)
    return repo, version, doc


@pytest.mark.parametrize(
    "tool,locator", [("read_document", "body:1"), ("read_email", "email:postscript:2")]
)
async def test_successful_read_marks_only_requested_range(session, tool, locator):
    repo, version, doc = await setup_version(session)
    session.add(DocumentPage(document_id=doc.id, locator="body:1", seq=1, text="text"))
    session.add_all(
        [
            EmailPart(document_id=doc.id, part_role="latest_body", seq=1, body="body"),
            EmailPart(
                document_id=doc.id, part_role="postscript", seq=2, body="postscript"
            ),
        ]
    )
    run = AgentRun(
        case_id=version.case_id,
        rule_set_id=version.rule_set_id,
        version_id=version.id,
        model="synthetic",
        started_at=datetime.now(UTC),
        outcome="running",
    )
    session.add(run)
    await session.flush()
    session.add(
        AgentRunStep(
            agent_run_id=run.id,
            seq=1,
            tool_name=tool,
            args_digest="synthetic",
            document_id=doc.id,
            locator=locator,
            result_status="ok",
        )
    )
    await session.commit()
    snapshot = await repo.snapshot(version.id)
    assert snapshot.scanned_ranges == {(doc.id, locator)}
    assert len(snapshot.readable_ranges - snapshot.scanned_ranges) == 2


@pytest.mark.parametrize("intake", [True, False])
async def test_scoped_issue_excuses_only_matching_range(session, intake):
    repo, version, doc = await setup_version(session)
    session.add_all(
        [
            DocumentPage(document_id=doc.id, locator=f"body:{i}", seq=i, text="text")
            for i in (1, 2)
        ]
    )
    run = AgentRun(
        case_id=version.case_id,
        rule_set_id=version.rule_set_id,
        version_id=version.id,
        model="synthetic",
        started_at=datetime.now(UTC),
        outcome="running",
    )
    session.add(run)
    await session.flush()
    session.add(
        DocumentIssue(
            document_id=doc.id,
            agent_run_id=None if intake else run.id,
            locator="body:1",
            issue_type="not_scanned",
            detail="synthetic",
        )
    )
    await session.commit()
    snapshot = await repo.snapshot(version.id)
    assert snapshot.excused_ranges == {(doc.id, "body:1")}
    assert snapshot.readable_ranges - snapshot.excused_ranges == {(doc.id, "body:2")}
    assert snapshot.has_issues


async def test_stopped_run_rejects_draft_write(session):
    repo, version, doc = await setup_version(session)
    session.add(
        AgentRun(
            case_id=version.case_id,
            rule_set_id=version.rule_set_id,
            version_id=version.id,
            model="synthetic",
            started_at=datetime.now(UTC),
            outcome="stopped",
        )
    )
    await session.commit()
    with pytest.raises(DraftError) as exc:
        await repo.save_header(version.id, HeaderInput(**header_data()))
    assert exc.value.code == "E_RUN_NOT_ACTIVE"
    assert (await repo.snapshot(version.id)).header is None


async def test_edit_refreshes_finalization_from_database(session):
    """Cache refresh only; SQLite cannot establish PostgreSQL lock serialization."""
    from sqlalchemy import text

    repo, version, doc = await setup_version(session)
    await session.refresh(version)
    await session.execute(
        text("UPDATE versions SET finalized_at=:at WHERE id=:id").bindparams(
            at=datetime.now(UTC), id=version.id
        )
    )
    await session.commit()
    assert version.finalized_at is None  # deliberately stale identity map
    with pytest.raises(DraftError) as exc:
        await repo.save_header(version.id, HeaderInput(**header_data()))
    assert exc.value.code == "E_VERSION_FINALIZED"


def test_scan_index_exists_in_model():
    """Model contract only; make check-run-step-index verifies live migrations."""
    assert any(
        tuple(c.name for c in idx.columns) == ("document_id", "locator")
        for idx in AgentRunStep.__table__.indexes
    )


async def test_version_numbers_and_lineage_preserve_old_version(session):
    repo, first, doc = await setup_version(session)
    row = (await repo.add_items(first.id, [ItemInput(**item_data())]))[0]
    second = await repo.create_version(first.case_id, first.rule_set_id, first.id)
    assert (first.version_no, second.version_no, second.prev_version_id) == (
        1,
        2,
        first.id,
    )
    assert (await repo.snapshot(first.id)).items[0].id == row.id
    assert (await repo.snapshot(second.id)).items == []


async def test_all_artifacts_and_cross_over_ends_roundtrip(session):
    repo, version, doc = await setup_version(session)
    await repo.save_header(version.id, HeaderInput(**header_data()))
    row_data = item_data() | {
        "ends": [
            {
                "side": "end_a",
                "od_value": "13.375",
                "od_unit": "in",
                "thread_end": "BOX",
            },
            {"side": "end_b", "od_value": "7", "od_unit": "in", "thread_end": "PIN"},
        ]
    }
    row = (await repo.add_items(version.id, [ItemInput(**row_data)]))[0]
    await repo.add_evidences(
        version.id,
        [
            EvidenceInput(
                item_id=row.id,
                field="qty",
                document_id=doc.id,
                locator="body:1",
                quote="150 MT",
                raw_value="150 MT",
                adopted_value="150 MT",
            )
        ],
    )
    await repo.add_questions(
        version.id,
        [
            QuestionInput(
                question_code="Q1",
                item_id=row.id,
                target_field="connection",
                reason="Unspecified",
            )
        ],
    )
    await repo.add_inventory(
        version.id,
        [
            InventoryInput(
                document_id=doc.id,
                position="body:1",
                source_no="1",
                seq=1,
                excerpt="CSG 150 MT",
                status="mapped",
                item_ids=[row.id],
            )
        ],
    )
    s = await repo.snapshot(version.id)
    assert (len(s.items), len(s.evidences), len(s.questions), len(s.inventory)) == (
        1,
        1,
        1,
        1,
    )
    assert s.header.inquiry_no_state == "not_stated"
    ends = (
        (await session.execute(select(ItemEnd).where(ItemEnd.item_id == row.id)))
        .scalars()
        .all()
    )
    assert {e.thread_end for e in ends} == {"BOX", "PIN"}
    links = (await session.execute(select(InventoryLink))).scalars().all()
    assert len(links) == 1 and links[0].item_id == row.id


@pytest.mark.parametrize(
    "method",
    ["save_header", "add_items", "add_evidences", "add_questions", "add_inventory"],
)
async def test_every_write_rejects_finalized_version(session, method):
    repo, version, doc = await setup_version(session)
    version.finalized_at = datetime.now(UTC)
    await session.commit()
    argument = HeaderInput(**header_data()) if method == "save_header" else []
    with pytest.raises(DraftError) as exc:
        await getattr(repo, method)(version.id, argument)
    assert exc.value.code == "E_VERSION_FINALIZED"


async def test_cross_version_item_and_cross_case_document_rejected(session):
    repo, first, doc = await setup_version(session)
    row = (await repo.add_items(first.id, [ItemInput(**item_data())]))[0]
    second = await repo.create_version(first.case_id, first.rule_set_id, first.id)
    with pytest.raises(DraftError):
        await repo.add_questions(
            second.id,
            [
                QuestionInput(
                    question_code="Q1",
                    item_id=row.id,
                    target_field="qty",
                    reason="Check",
                )
            ],
        )
    other_case, other_rules, other_doc = await setup_case(session, "OTHER")
    with pytest.raises(DraftError):
        await repo.add_inventory(
            first.id,
            [
                InventoryInput(
                    document_id=other_doc.id,
                    position="body:1",
                    seq=1,
                    excerpt="Not this case",
                    status="unmapped",
                )
            ],
        )
    with pytest.raises(DraftError):
        await repo.create_version(other_case.id, other_rules.id, first.id)


async def test_batch_is_atomic_on_duplicate_row(session):
    repo, version, doc = await setup_version(session)
    with pytest.raises(DraftError):
        await repo.add_items(
            version.id, [ItemInput(**item_data()), ItemInput(**item_data())]
        )
    assert (await repo.snapshot(version.id)).items == []


async def test_email_coverage_and_issue_scope(session):
    repo, version, doc = await setup_version(session)
    doc.kind = "eml"
    session.add_all(
        [
            EmailPart(document_id=doc.id, part_role="latest_body", seq=1, body="Body"),
            EmailPart(
                document_id=doc.id, part_role="postscript", seq=2, body="Revision"
            ),
            EmailPart(
                document_id=doc.id,
                part_role="attachment",
                seq=3,
                attachment_name="a.pdf",
            ),
        ]
    )
    run = AgentRun(
        case_id=version.case_id,
        rule_set_id=version.rule_set_id,
        version_id=version.id,
        model="dummy-t201",
        started_at=datetime.now(UTC),
        outcome="running",
    )
    session.add(run)
    await session.commit()
    expected = {
        (doc.id, "email:latest_body:1"),
        (doc.id, "email:postscript:2"),
        (doc.id, "email:attachment:3"),
    }
    s = await repo.snapshot(version.id)
    assert s.readable_ranges == expected and s.scanned_ranges == set()
    session.add(
        AgentRunStep(
            agent_run_id=run.id,
            seq=1,
            tool_name="read_email",
            args_digest="synthetic",
            document_id=doc.id,
            locator="email:*",
            result_status="ok",
        )
    )
    await session.commit()
    assert (await repo.snapshot(version.id)).scanned_ranges == expected


async def test_only_successful_read_tools_count_and_other_run_issues_do_not_excuse(
    session
):
    repo, version, doc = await setup_version(session)
    session.add(DocumentPage(document_id=doc.id, locator="body:1", seq=1, text="text"))
    runs = [
        AgentRun(
            case_id=version.case_id,
            rule_set_id=version.rule_set_id,
            version_id=version.id if i == 0 else None,
            model="dummy-t201",
            started_at=datetime.now(UTC),
            outcome="running" if i == 0 else "failed",
        )
        for i in range(2)
    ]
    session.add_all(runs)
    await session.commit()
    for seq, tool, status in [
        (1, "search_documents", "ok"),
        (2, "read_document", "error"),
    ]:
        session.add(
            AgentRunStep(
                agent_run_id=runs[0].id,
                seq=seq,
                tool_name=tool,
                args_digest="synthetic",
                document_id=doc.id,
                locator="body:1",
                result_status=status,
            )
        )
    session.add(
        DocumentIssue(
            document_id=doc.id,
            agent_run_id=runs[1].id,
            locator="body:1",
            issue_type="not_scanned",
            detail="another run",
        )
    )
    session.add(
        DocumentIssue(
            document_id=doc.id,
            locator=None,
            issue_type="reference_missing",
            detail="missing metadata",
        )
    )
    await session.commit()
    s = await repo.snapshot(version.id)
    assert s.scanned_ranges == s.excused_ranges == set()


async def test_no_conversion_or_total_columns_exist(session):
    forbidden = {"converted_value", "converted_qty", "total_qty"}
    for cls in [Item, ItemEnd, CaseHeader, Evidence]:
        assert not forbidden.intersection(cls.__table__.columns.keys())


@pytest.mark.parametrize("case_level", [True, False])
async def test_duplicate_evidence_uses_documented_error_code(session, case_level):
    repo, version, doc = await setup_version(session)
    row = (await repo.add_items(version.id, [ItemInput(**item_data())]))[0]
    evidence = EvidenceInput(
        item_id=None if case_level else row.id,
        field="qty",
        document_id=doc.id,
        locator="body:1",
        quote="150 MT",
        raw_value="150 MT",
        adopted_value="150 MT",
    )
    await repo.add_evidences(version.id, [evidence])
    with pytest.raises(DraftError) as exc:
        await repo.add_evidences(version.id, [evidence])
    assert exc.value.code == "E_EVIDENCE_DUPLICATE"
    assert len((await repo.snapshot(version.id)).evidences) == 1


async def test_snapshot_includes_both_ends(session):
    repo, version, doc = await setup_version(session)
    data = item_data() | {
        "ends": [
            {"side": "end_a", "connection": "BTC"},
            {"side": "end_b", "thread_end": "PIN"},
        ]
    }
    row = (await repo.add_items(version.id, [ItemInput(**data)]))[0]
    s = await repo.snapshot(version.id)
    assert {(e.item_id, e.side) for e in s.ends} == {
        (row.id, "end_a"),
        (row.id, "end_b"),
    }


async def test_finalize_persists_version_and_run_and_rejects_second_attempt(session):
    from app.services.draft_service import DraftService

    repo, version, doc = await setup_version(session)
    await repo.save_header(version.id, HeaderInput(**header_data()))
    row = (await repo.add_items(version.id, [ItemInput(**item_data())]))[0]
    await repo.add_evidences(
        version.id,
        [
            EvidenceInput(
                item_id=row.id,
                field=f,
                document_id=doc.id,
                locator="body:1",
                quote="original",
                raw_value="original",
                adopted_value="original",
            )
            for f in ("kind", "qty", "od", "grade", "connection")
        ],
    )
    await repo.add_inventory(
        version.id,
        [
            InventoryInput(
                document_id=doc.id,
                position="body:1",
                seq=1,
                excerpt="synthetic",
                status="mapped",
                item_ids=[row.id],
            )
        ],
    )
    run = AgentRun(
        case_id=version.case_id,
        rule_set_id=version.rule_set_id,
        version_id=version.id,
        model="dummy-t201",
        started_at=datetime.now(UTC),
        outcome="running",
    )
    session.add(run)
    session.add(
        DocumentIssue(
            document_id=doc.id,
            locator=None,
            issue_type="reference_missing",
            detail="Missing metadata",
        )
    )
    await session.commit()
    finalized = await DraftService(repo).finalize(version.id)
    assert finalized.finalized_at is not None
    assert finalized.current_state == "draft" and not finalized.is_complete
    await session.refresh(run)
    assert run.validation_result == []
    with pytest.raises(DraftError) as exc:
        await DraftService(repo).finalize(version.id)
    assert exc.value.code == "E_VERSION_FINALIZED"
