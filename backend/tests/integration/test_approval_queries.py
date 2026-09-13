"""Record collections, carryover isolation and bounded query count."""
from datetime import UTC, datetime
from sqlalchemy import event, select
from app.models import (
    Confirmation,
    ItemEdit,
    Question,
    QuestionJudgement,
    VersionStateEvent,
    SendoffDecision,
)
from app.domain.record_types import CarryOver
from app.repositories.record_repository import RecordRepository
from tests.fixtures.record_data import seed_record_version, record_actor


async def test_record_collections_include_cancellations_and_keep_version_scope(
    db_session
):
    seed = await seed_record_version(db_session, state="staff_checked")
    other = await seed_record_version(db_session)
    repo = RecordRepository(db_session)
    vid = seed.version.id
    at = datetime.now(UTC)
    question = Question(
        version_id=vid,
        question_code="Q1",
        item_id=seed.item.id,
        target_field="grade",
        reason="check",
    )
    db_session.add(question)
    await db_session.flush()
    edit = ItemEdit(
        version_id=vid,
        item_id=seed.item.id,
        field="grade",
        new_value="L80",
        reason="check",
        undone_at=at,
        undone_by="undo",
        **record_actor(),
    )
    cancelled = Confirmation(
        version_id=vid,
        kind="coverage",
        undone_at=at,
        undone_by="undo",
        **record_actor(),
    )
    active = Confirmation(
        version_id=vid, kind="row_match", item_id=seed.item.id, **record_actor()
    )
    judgement = QuestionJudgement(
        question_id=question.id,
        status="judged",
        resolution="unresolved",
        **record_actor(),
    )
    foreign = SendoffDecision(
        version_id=other.version.id, decision="undecided", **record_actor()
    )
    db_session.add_all([edit, cancelled, active, judgement, foreign])
    await db_session.commit()
    async with repo.record(vid):
        comment = await repo.save_bounce_comment(
            vid, {"item_id": seed.item.id, "comment": "check", **record_actor()}
        )
        bounce = await repo.save_bounce(
            vid, {"reason": "R1: check", **record_actor()}, [comment]
        )
        unlinked = await repo.save_bounce_comment(
            vid, {"item_id": seed.item.id, "comment": "next", **record_actor()}
        )
        sendoff = await repo.save_sendoff(
            vid, {"decision": "hold", "reason": "answer pending", **record_actor()}
        )
    records = await repo.list_records(vid)
    assert set(records) == {
        "edits",
        "confirmations",
        "judgements",
        "state_events",
        "bounces",
        "unlinked_comments",
        "sendoff_decisions",
    }
    assert {row.id for row in records["edits"]} == {edit.id}
    assert {row.id for row in records["confirmations"]} == {cancelled.id, active.id}
    assert {row.id for row in records["judgements"]} == {judgement.id}
    expected = {
        row.id
        for row in (
            await db_session.execute(
                select(VersionStateEvent).where(VersionStateEvent.version_id == vid)
            )
        ).scalars()
    }
    assert {row.id for row in records["state_events"]} == expected
    assert [
        (row["bounce"].id, {c.id for c in row["comments"]})
        for row in records["bounces"]
    ] == [(bounce.id, {comment.id})]
    assert {row.id for row in records["unlinked_comments"]} == {unlinked.id}
    assert {row.id for row in records["sendoff_decisions"]} == {sendoff.id}
    assert await repo.matched_item_ids(vid) == {seed.item.id}
    assert await repo.coverage_confirmed(vid) is False
    assert await repo.item_rows(vid) == {seed.item.id: seed.item.row_code}
    rows = await repo.list_versions_with_records(seed.case.id)
    assert len(rows) == 1 and rows[0]["version"].id == vid
    assert rows[0]["carry_over"] == CarryOver(0, 1, 1, False, 1)
    assert rows[0]["unresolved_count"] == 1
    assert rows[0]["latest_state_event"].id in expected
    assert rows[0]["latest_bounce"].id == bounce.id
    assert rows[0]["latest_sendoff_decision"].id == sendoff.id


async def test_query_count_is_constant_and_latest_records_use_time_then_id(db_session):
    from app.models import Version, Item
    from app.domain.draft_types import ItemInput
    from tests.fixtures.draft_data import item_data

    seed = await seed_record_version(db_session)
    repo = RecordRepository(db_session)
    # Warm case lookup so the identity map has identical state at both measurements.
    await repo.list_versions(seed.case.id)

    def statements():
        result = []

        def observe(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                result.append(statement)

        return result, observe

    first, observe = statements()
    event.listen(db_session.bind.sync_engine, "before_cursor_execute", observe)
    try:
        one = await repo.list_versions_with_records(seed.case.id)
    finally:
        event.remove(db_session.bind.sync_engine, "before_cursor_execute", observe)
    versions = [seed.version]
    at = datetime.now(UTC)
    for number in (2, 3, 4):
        version = Version(
            case_id=seed.case.id,
            rule_set_id=seed.rule.id,
            version_no=number,
            current_state="draft",
            is_complete=True,
            finalized_at=at,
        )
        db_session.add(version)
        await db_session.flush()
        versions.append(version)
        db_session.add(
            Item(
                version_id=version.id,
                **ItemInput.model_validate(item_data()).model_dump(exclude={"ends"}),
            )
        )
    pending = Version(
        case_id=seed.case.id,
        rule_set_id=seed.rule.id,
        version_no=5,
        current_state="draft",
        is_complete=False,
    )
    db_session.add(pending)
    earlier = SendoffDecision(
        version_id=seed.version.id,
        decision="hold",
        reason="first",
        **record_actor(at=at),
    )
    later = SendoffDecision(
        version_id=seed.version.id,
        decision="approved",
        reason="second",
        **record_actor(at=at),
    )
    db_session.add_all([earlier, later])
    await db_session.commit()
    many, observe = statements()
    event.listen(db_session.bind.sync_engine, "before_cursor_execute", observe)
    try:
        four = await repo.list_versions_with_records(seed.case.id)
    finally:
        event.remove(db_session.bind.sync_engine, "before_cursor_execute", observe)
    assert len(first) == len(many) and 1 < len(first) <= 12
    assert [row["version"].id for row in four] == [v.id for v in reversed(versions)]
    assert len(one) == 1
    assert four[-1]["latest_sendoff_decision"].id == later.id
    assert all(row["carry_over"] == CarryOver(0, 0, 1, False, 0) for row in four)
    assert all(row["latest_review_checked_at"] is None for row in four)
    assert all(
        row["unresolved_count"] == 0
        and row["latest_bounce"] is None
        and row["latest_state_event"] is None
        for row in four
    )


async def test_latest_review_time_survives_bounce_and_corrective_downgrade(db_session):
    from app.services.approval_service import ApprovalService
    from app.services.record_service import RecordService
    from tests.fixtures.record_data import edit_data

    seed = await seed_record_version(db_session, state="review_checked")
    repo = RecordRepository(db_session)
    previous = list(
        (
            await db_session.execute(
                select(VersionStateEvent).where(
                    VersionStateEvent.to_state == "review_checked"
                )
            )
        ).scalars()
    )
    reviewed_at = previous[0].recorded_at
    await RecordService(repo).edit(seed.version.id, edit_data(item_id=seed.item.id))
    service = ApprovalService(repo)
    await service.comment(
        seed.version.id,
        {"item_id": seed.item.id, "comment": "再確認", "recorded_by": "人"},
    )
    await service.bounce(seed.version.id, {"recorded_by": "人"})
    material = (await repo.list_versions_with_records(seed.case.id))[0]
    assert material["latest_state_event"].to_state == "staff_checked"
    assert material["latest_bounce"] is not None
    assert material["latest_review_checked_at"] == reviewed_at


async def test_carryover_counts_active_rows_and_questions_once_with_latest_resolution(
    db_session
):
    from app.services.record_service import RecordService
    from tests.fixtures.record_data import edit_data

    seed = await seed_record_version(db_session)
    repo = RecordRepository(db_session)
    service = RecordService(repo)
    vid = seed.version.id
    edits = await service.edit(
        vid,
        edit_data(
            item_id=seed.item.id,
            field="qty_value",
            new_value="200",
            new_state="numeric",
            qty_unit="本",
        ),
    )
    assert {row.field for row in edits} == {"qty_value", "qty_unit"}
    cancelled = await service.confirm(
        vid, {"kind": "row_match", "item_id": seed.item.id, "recorded_by": "人"}
    )
    await service.undo_confirmation(vid, cancelled.id, {"recorded_by": "取消者"})
    coverage = await service.confirm(vid, {"kind": "coverage", "recorded_by": "人"})
    question = Question(
        version_id=vid,
        question_code="Q1",
        item_id=seed.item.id,
        target_field="grade",
        reason="check",
    )
    db_session.add(question)
    await db_session.flush()
    at = datetime.now(UTC)
    first = QuestionJudgement(
        question_id=question.id,
        status="judged",
        resolution="unresolved",
        **record_actor(at=at),
    )
    last = QuestionJudgement(
        question_id=question.id,
        status="judged",
        resolution="resolved",
        **record_actor(at=at),
    )
    db_session.add_all([first, last])
    await db_session.commit()
    row = (await repo.list_versions_with_records(seed.case.id))[0]
    assert set(row) == {
        "version",
        "carry_over",
        "unresolved_count",
        "elapsed_sec",
        "latest_state_event",
        "latest_review_checked_at",
        "latest_bounce",
        "latest_sendoff_decision",
    }
    assert row["carry_over"] == CarryOver(2, 0, 1, True, 1)
    assert row["unresolved_count"] == 0
    assert await repo.matched_item_ids(vid) == set()
    assert await repo.coverage_confirmed(vid) is True
    records = await repo.list_records(vid)
    assert {row.id for row in records["edits"]} == {row.id for row in edits}
    assert {row.id for row in records["confirmations"]} == {cancelled.id, coverage.id}
    assert [row.id for row in records["judgements"]] == [first.id, last.id]
    assert (await service.summary(vid))["unresolved_count"] == row["unresolved_count"]


async def test_record_lists_order_by_recorded_time_then_id(db_session):
    from datetime import timedelta
    from app.models import Bounce, BounceComment

    seed = await seed_record_version(db_session)
    vid, item_id = seed.version.id, seed.item.id
    question = Question(
        version_id=vid,
        question_code="Q1",
        item_id=item_id,
        target_field="grade",
        reason="check",
    )
    db_session.add(question)
    await db_session.flush()
    at = datetime.now(UTC)
    groups = {
        key: []
        for key in (
            "edits",
            "confirmations",
            "judgements",
            "state_events",
            "bounces",
            "unlinked_comments",
            "sendoff_decisions",
        )
    }
    for offset in (2, 1, 1):
        actor = record_actor(at=at + timedelta(seconds=offset))
        records = {
            "edits": ItemEdit(
                version_id=vid,
                item_id=item_id,
                field="grade",
                new_value="L80",
                reason="check",
                **actor,
            ),
            "confirmations": Confirmation(
                version_id=vid,
                kind="coverage",
                undone_at=at + timedelta(seconds=3),
                undone_by="undo",
                **actor,
            ),
            "judgements": QuestionJudgement(
                question_id=question.id,
                status="judged",
                resolution="unresolved",
                **actor,
            ),
            "state_events": VersionStateEvent(
                version_id=vid,
                from_state="draft",
                to_state="staff_checked",
                unresolved_count=1,
                **actor,
            ),
            "bounces": Bounce(version_id=vid, reason="R1: check", **actor),
            "unlinked_comments": BounceComment(
                version_id=vid, item_id=item_id, comment="check", **actor
            ),
            "sendoff_decisions": SendoffDecision(
                version_id=vid, decision="undecided", **actor
            ),
        }
        db_session.add_all(list(records.values()))
        await db_session.flush()
        for key, record in records.items():
            groups[key].append(record)
    linked = []
    for offset in (2, 1, 1):
        comment = BounceComment(
            version_id=vid,
            item_id=item_id,
            bounce_id=groups["bounces"][0].id,
            comment="linked",
            **record_actor(at=at + timedelta(seconds=offset)),
        )
        db_session.add(comment)
        await db_session.flush()
        linked.append(comment)
    await db_session.commit()
    records = await RecordRepository(db_session).list_records(vid)
    for key, expected in groups.items():
        actual = (
            [row["bounce"] for row in records[key]]
            if key == "bounces"
            else records[key]
        )
        assert [row.id for row in actual] == [expected[index].id for index in (1, 2, 0)]
    assert [row.id for row in records["bounces"][-1]["comments"]] == [
        linked[index].id for index in (1, 2, 0)
    ]


async def test_version_list_reports_generation_elapsed_or_none(db_session):
    """N06: 版ごとの生成所要。run が無い版は None（0 秒と区別する）。"""
    from decimal import Decimal
    from app.models import AgentRun, Version

    seed = await seed_record_version(db_session)
    at = datetime.now(UTC)
    without_run = Version(
        case_id=seed.case.id,
        rule_set_id=seed.rule.id,
        version_no=2,
        current_state="draft",
        is_complete=True,
        finalized_at=at,
    )
    db_session.add(without_run)
    await db_session.flush()
    db_session.add(
        AgentRun(
            case_id=seed.case.id,
            rule_set_id=seed.rule.id,
            version_id=seed.version.id,
            model="mock-fixed-v2",
            limits={},
            started_at=at,
            ended_at=at,
            elapsed_sec=Decimal("631.5"),
            outcome="success",
            stage="done",
        )
    )
    await db_session.commit()
    rows = await RecordRepository(db_session).list_versions_with_records(seed.case.id)
    elapsed = {row["version"].id: row["elapsed_sec"] for row in rows}
    assert elapsed[seed.version.id] == Decimal("631.5")
    assert elapsed[without_run.id] is None
