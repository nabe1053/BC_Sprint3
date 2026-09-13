"""Synthetic human-record builders shared across test layers."""
from datetime import UTC, datetime
from types import SimpleNamespace as N

from tests.fixtures.draft_data import item_data


def edit_data(**changes):
    return {
        "item_id": 1,
        "field": "grade",
        "new_value": "L80",
        "reason": "照合結果",
        "recorded_by": "担当者",
        **changes,
    }


def current_item(**changes):
    return N(**{**item_data(), "id": 1, "version_id": 1, **changes})


def edit(**changes):
    return N(
        **{
            "id": 1,
            "field": "grade",
            "new_value": "L80",
            "new_state": "stated",
            "old_value": "K55",
            "old_state": "stated",
            "undone_at": None,
            "recorded_at": datetime(2026, 1, 1, tzinfo=UTC),
            **changes,
        }
    )


async def seed_record_version(session, finalized=True, state="draft"):
    from uuid import uuid4
    from app.domain.draft_types import ItemInput
    from app.models import Case, RuleSet, Version, Item, VersionStateEvent

    key = str(uuid4())
    case = Case(case_code=key)
    rule = RuleSet(rule_version=key, rules={})
    session.add_all([case, rule])
    await session.flush()
    version = Version(
        case_id=case.id,
        rule_set_id=rule.id,
        version_no=1,
        current_state=state,
        is_complete=True,
        finalized_at=datetime.now(UTC) if finalized else None,
    )
    session.add(version)
    await session.flush()
    item = Item(
        version_id=version.id,
        **ItemInput.model_validate(item_data()).model_dump(exclude={"ends"}),
    )
    session.add(item)
    at = datetime.now(UTC)
    if state != "draft":
        session.add(
            VersionStateEvent(
                version_id=version.id,
                from_state="draft",
                to_state="staff_checked",
                recorded_by="fixture",
                recorded_at=at,
                unresolved_count=0,
            )
        )
    if state == "review_checked":
        session.add(
            VersionStateEvent(
                version_id=version.id,
                from_state="staff_checked",
                to_state="review_checked",
                recorded_by="fixture",
                recorded_at=at,
                unresolved_count=0,
            )
        )
    await session.commit()
    return N(case=case, rule=rule, version=version, item=item)


def carryover_record(table, version_id, item_id, question_id, undone):
    from app.models import ItemEdit, Confirmation, QuestionJudgement

    actor = dict(recorded_by="person", recorded_at=datetime.now(UTC))
    if table == "item_edits":
        return ItemEdit(
            version_id=version_id,
            item_id=item_id,
            field="grade",
            new_value="L80",
            reason="reason",
            undone_at=datetime.now(UTC) if undone else None,
            undone_by="undo person" if undone else None,
            **actor,
        )
    if table == "confirmations":
        return Confirmation(version_id=version_id, kind="coverage", **actor)
    return QuestionJudgement(
        question_id=question_id, status="judged", resolution="unresolved", **actor
    )


def record_actor(by="person", at=None):
    return {"recorded_by": by, "recorded_at": at or datetime.now(UTC)}


def approval_questions():
    return [
        {"question": N(id=1), "latest": None},
        {"question": N(id=2), "latest": N(status="judged", resolution="unresolved")},
        {"question": N(id=3), "latest": N(status="judged", resolution="resolved")},
    ]
