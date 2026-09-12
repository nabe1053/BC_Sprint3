from datetime import UTC, datetime

import pytest

from app.domain.draft_errors import DraftError
from app.domain.draft_types import ItemInput
from app.models import (
    Confirmation,
    Document,
    Evidence,
    Item,
    ItemEdit,
    Question,
    QuestionJudgement,
)
from tests.fixtures.draft_data import item_data
from tests.fixtures.record_data import seed_record_version


async def test_summary_sets_current_values_history_latest_judgements_and_evidence(
    db_session
):
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session)
    # Build the synthetic display snapshot, including two alternatives.
    seed.item.group_code, seed.item.candidate_label = "G1", "A"
    second = Item(
        version_id=seed.version.id,
        **ItemInput.model_validate(
            {
                **item_data(),
                "row_code": "2",
                "source_no": "2",
                "seq": 2,
                "qty_state": "tba",
                "qty_value": None,
                "qty_unit": None,
                "group_code": "G1",
                "candidate_label": "B",
            }
        ).model_dump(exclude={"ends"}),
    )
    doc = Document(
        case_id=seed.case.id,
        file_name="synthetic.txt",
        storage_path="unused",
        kind="text",
        read_status="success",
        received_at=datetime.now(UTC),
    )
    db_session.add_all([second, doc])
    await db_session.flush()
    questions = [
        Question(
            version_id=seed.version.id,
            item_id=seed.item.id if i < 3 else None,
            question_code=f"Q{i}",
            target_field="grade",
            reason="confirm",
        )
        for i in range(1, 4)
    ]
    db_session.add_all(questions)
    await db_session.flush()
    at = datetime.now(UTC)
    active = ItemEdit(
        version_id=seed.version.id,
        item_id=seed.item.id,
        field="grade",
        new_value="L80",
        new_state="stated",
        reason="reason",
        recorded_by="person",
        recorded_at=at,
    )
    cancelled = ItemEdit(
        version_id=seed.version.id,
        item_id=seed.item.id,
        field="grade",
        new_value="N80",
        reason="reason",
        recorded_by="person",
        recorded_at=at,
        undone_at=at,
        undone_by="person",
    )
    evidence = Evidence(
        version_id=seed.version.id,
        item_id=seed.item.id,
        document_id=doc.id,
        field="grade",
        raw_value="K55",
        adopted_value="K55",
        locator="body:1",
        quote="K55",
    )
    db_session.add_all(
        [
            active,
            cancelled,
            evidence,
            Confirmation(
                version_id=seed.version.id,
                item_id=seed.item.id,
                kind="row_match",
                recorded_by="person",
                recorded_at=at,
            ),
            Confirmation(
                version_id=seed.version.id,
                item_id=second.id,
                kind="row_match",
                recorded_by="person",
                recorded_at=at,
                undone_at=at,
                undone_by="person",
            ),
            QuestionJudgement(
                question_id=questions[0].id,
                status="judged",
                resolution="resolved",
                recorded_by="person",
                recorded_at=at,
            ),
        ]
    )
    await db_session.flush()
    latest = QuestionJudgement(
        question_id=questions[0].id,
        status="judged",
        resolution="unresolved",
        recorded_by="person",
        recorded_at=at,
    )
    db_session.add_all(
        [
            latest,
            QuestionJudgement(
                question_id=questions[2].id,
                status="in_progress",
                resolution="resolved",
                recorded_by="person",
                recorded_at=at,
            ),
        ]
    )
    await db_session.commit()
    service = RecordService(RecordRepository(db_session))
    summary = await service.summary(seed.version.id)
    assert summary["item_ids"] == {seed.item.id, second.id}
    assert summary["matched_item_ids"] == {seed.item.id}
    assert summary["edited_item_ids"] == {seed.item.id}
    assert summary["question_item_ids"] == {seed.item.id}
    assert summary["tba_item_ids"] == {second.id}
    assert summary["unresolved_question_ids"] == {questions[0].id, questions[1].id}
    assert summary["choice_groups"] == {"G1": {seed.item.id, second.id}}
    assert (
        summary["item_count"],
        summary["matched_count"],
        summary["edit_count"],
        summary["unresolved_count"],
    ) == (2, 1, 1, 2)
    current = await service.list_items_with_edits(seed.version.id)
    assert (
        current[0].values["grade"] == "L80" and current[0].values["grade_raw"] == "K55"
    )
    assert {row.id for row in current[0].history} == {active.id, cancelled.id}
    latest_rows = await service.list_questions_with_latest(seed.version.id)
    assert latest_rows[0]["latest"].id == latest.id and latest_rows[1]["latest"] is None
    assert {
        row.id
        for row in await service.list_item_evidence(seed.version.id, seed.item.id)
    } == {evidence.id}


@pytest.mark.parametrize(
    "method",
    [
        "summary",
        "list_items_with_edits",
        "list_questions_with_latest",
        "list_item_evidence",
    ],
)
async def test_read_rejects_unfinalized_version(db_session, method):
    from app.repositories.record_repository import RecordRepository
    from app.services.record_service import RecordService

    seed = await seed_record_version(db_session, finalized=False)
    service = RecordService(RecordRepository(db_session))
    args = (
        (seed.version.id, seed.item.id)
        if method == "list_item_evidence"
        else (seed.version.id,)
    )
    with pytest.raises(DraftError) as error:
        await getattr(service, method)(*args)
    assert error.value.code == "E_NOT_FOUND"
